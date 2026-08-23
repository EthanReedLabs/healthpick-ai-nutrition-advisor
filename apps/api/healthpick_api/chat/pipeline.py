"""One fail-closed chat path from intent to validated evidence-backed final event."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from uuid import UUID

from healthpick_api.config import Settings
from healthpick_api.evidence import CitationBuilder, EvidenceValidator
from healthpick_api.models import (
    ChatFinalEvent,
    ChatRequest,
    Citation,
    ModelInfo,
    RetrievalSelection,
    RetrievalTraceView,
    SafetyResult,
)
from healthpick_api.providers import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResult,
    ProviderRequestError,
    build_llm_provider,
)
from healthpick_api.recommendation import RecommendationEvaluation
from healthpick_api.recommendation.service import RecommendationService
from healthpick_api.retrieval import KeywordRetriever, KnowledgeIndex, RetrievalTrace
from healthpick_api.routing import QueryRouter, RouteDecision
from healthpick_api.safety import (
    OutputSafetyValidator,
    SafetyService,
    ensure_required_notice,
)

from .conversation import (
    ConversationStore,
    ConversationTurn,
    EphemeralConversationStore,
    build_conversation_store,
)

LOGGER = logging.getLogger("healthpick.api.chat")
FALLBACK_CLAUSE_SPLIT = re.compile(r"(?<=[。！？!?；;])|\n+")
FALLBACK_MAX_STATEMENTS = 3
FALLBACK_BLOCKED_FOOD_TERMS: dict[str, tuple[str, ...]] = {
    "egg": ("鸡蛋", "蛋类", "全蛋", "蛋清"),
    "dairy": ("牛奶", "乳制品", "酸奶", "奶酪"),
    "peanut": ("花生",),
    "tree_nut": ("坚果", "核桃", "杏仁", "腰果"),
    "wheat": ("小麦", "全麦"),
    "soy": ("大豆", "豆浆", "豆腐", "豆制品"),
    "fish": ("鱼", "三文鱼", "鳕鱼"),
    "shellfish": ("虾", "蟹", "贝类", "甲壳类"),
    "sesame": ("芝麻",),
    "gluten": ("小麦", "大麦", "黑麦", "麸质", "全麦"),
    "high_purine": ("动物内脏", "浓肉汤", "沙丁鱼", "啤酒"),
    "high_sodium": ("腌制", "加工肉", "浓汤宝", "方便面调料"),
    "meat": ("肉", "鸡胸", "牛肉", "猪肉", "鱼", "虾"),
    "animal_product": ("肉", "鸡蛋", "牛奶", "酸奶", "鱼", "虾"),
}


@dataclass(frozen=True, slots=True)
class ChatExecution:
    final: ChatFinalEvent
    trace: RetrievalTrace | None
    session_mode: str


@dataclass(frozen=True, slots=True)
class GeneratedAnswerValidation:
    valid: bool
    error_codes: tuple[str, ...]
    referenced_chunk_ids: tuple[str, ...]


class ChatPipelineError(RuntimeError):
    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ChatPipeline:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        index: KnowledgeIndex,
        conversations: ConversationStore | None = None,
        safety: SafetyService | None = None,
        recommendations: RecommendationService | None = None,
        generation_timeout_seconds: float = 30,
    ) -> None:
        self.provider = provider
        self.router = QueryRouter()
        self.retriever = KeywordRetriever(index)
        self.citations = CitationBuilder()
        self.validator = EvidenceValidator(index)
        self.conversations = conversations or EphemeralConversationStore()
        self.safety = safety or SafetyService()
        self.recommendations = recommendations or RecommendationService.load_default()
        self.output_safety = OutputSafetyValidator()
        self.generation_timeout_seconds = generation_timeout_seconds

    async def run(self, payload: ChatRequest, *, request_id: str) -> ChatExecution:
        safety = self.safety.assess(payload.message, payload.profile_patch)
        if safety.risk_level != "S0":
            _log_safety_decision(request_id=request_id, safety=safety)
        if safety.response_mode in {"refuse", "emergency_stop"}:
            if safety.response_mode == "emergency_stop":
                await self.conversations.clear(
                    payload.conversation_id, session_id=payload.session_id
                )
            final = ChatFinalEvent(
                request_id=request_id,
                answer=ensure_required_notice(_deterministic_safety_answer(safety), safety),
                route="nutrition",
                citations=[],
                safety=safety,
                model=ModelInfo(
                    provider="healthpick_guard",
                    name="deterministic_safety_guard",
                    mode=self.provider.mode,
                ),
            )
            final = await self._remember(payload, final, context_eligible=False)
            return ChatExecution(
                final=final,
                trace=None,
                session_mode=self.conversations.mode,
            )

        decision = self.router.route(payload.message)
        if decision.route == "out_of_scope":
            final = ChatFinalEvent(
                request_id=request_id,
                answer="这个问题不在营养知识或 HealthPick 平台说明范围内，请换一个相关问题。",
                route="out_of_scope",
                citations=[],
                safety=SafetyResult(
                    risk_level="S0",
                    matched_rules=["scope_guard"],
                    required_notice="general",
                ),
                model=ModelInfo(
                    provider="healthpick_guard",
                    name="deterministic_scope_guard",
                    mode=self.provider.mode,
                ),
            )
            final = await self._remember(payload, final)
            return ChatExecution(
                final=final,
                trace=None,
                session_mode=self.conversations.mode,
            )

        recommendation_preview = self.recommendations.preview_for_message(
            payload.message,
            payload.profile_patch,
            safety=safety,
        )

        retrieval = self.retriever.search(payload.message, decision, limit=6)
        if not retrieval.hits:
            raise ChatPipelineError(
                code="insufficient_evidence",
                message="指定资料中没有找到足够证据，无法生成回答。",
                status_code=422,
            )
        bundle = self.citations.build(retrieval)
        history = await self.conversations.history(
            payload.conversation_id, session_id=payload.session_id
        )
        system_message = LLMMessage(role="system", content=_system_prompt(safety))
        user_message = LLMMessage(
            role="user",
            content=_user_prompt(payload, history, bundle.context_blocks),
        )
        result = await self._generate(
            LLMRequest(
                messages=(system_message, user_message),
                temperature=0,
                max_tokens=500,
                request_id=request_id,
            )
        )
        answer = _ensure_recommendation_notice(
            ensure_required_notice(result.content, safety),
            recommendation_preview,
        )
        validation = self._validate_generated_answer(
            answer=answer,
            citations=bundle.citations,
            decision=decision,
            safety=safety,
        )
        if not validation.valid:
            _log_validation_failure(
                request_id=request_id,
                attempt=1,
                answer=answer,
                error_codes=validation.error_codes,
                referenced_chunk_ids=validation.referenced_chunk_ids,
            )
            result = await self._generate(
                LLMRequest(
                    messages=(
                        system_message,
                        user_message,
                        LLMMessage(role="assistant", content=answer),
                        LLMMessage(
                            role="user",
                            content=_repair_prompt(
                                validation.error_codes,
                                tuple(citation.chunk_id for citation in bundle.citations),
                            ),
                        ),
                    ),
                    temperature=0,
                    request_id=request_id,
                )
            )
            answer = _ensure_recommendation_notice(
                ensure_required_notice(result.content, safety),
                recommendation_preview,
            )
            validation = self._validate_generated_answer(
                answer=answer,
                citations=bundle.citations,
                decision=decision,
                safety=safety,
            )
        if not validation.valid:
            _log_validation_failure(
                request_id=request_id,
                attempt=2,
                answer=answer,
                error_codes=validation.error_codes,
                referenced_chunk_ids=validation.referenced_chunk_ids,
            )
            fallback_answer = self._build_evidence_fallback(
                citations=bundle.citations,
                decision=decision,
                safety=safety,
                query=payload.message,
            )
            fallback_answer = _ensure_recommendation_notice(
                fallback_answer,
                recommendation_preview,
            )
            fallback_validation = self._validate_generated_answer(
                answer=fallback_answer,
                citations=bundle.citations,
                decision=decision,
                safety=safety,
            )
            if not fallback_validation.valid:
                _log_validation_failure(
                    request_id=request_id,
                    attempt=3,
                    answer=fallback_answer,
                    error_codes=fallback_validation.error_codes,
                    referenced_chunk_ids=fallback_validation.referenced_chunk_ids,
                )
                raise ChatPipelineError(
                    code="evidence_validation_failed",
                    message="模型输出和安全证据回退均未通过校验，已阻止返回。",
                    status_code=502,
                )
            _log_evidence_fallback(
                request_id=request_id,
                error_codes=validation.error_codes,
                referenced_chunk_ids=fallback_validation.referenced_chunk_ids,
            )
            answer = fallback_answer
            result = None

        final = ChatFinalEvent(
            request_id=request_id,
            answer=answer,
            route=_public_route(decision),
            citations=list(bundle.citations),
            safety=safety,
            model=ModelInfo(
                provider=result.provider if result is not None else "healthpick_guard",
                name=result.model if result is not None else "deterministic_evidence_fallback",
                mode=result.mode if result is not None else self.provider.mode,
            ),
            recommendation_preview=recommendation_preview,
            retrieval_trace=RetrievalTraceView(
                mode=retrieval.trace.mode,
                route=_public_route(decision),  # type: ignore[arg-type]
                route_components=list(retrieval.trace.route_components),
                allowed_sources=list(retrieval.trace.allowed_sources),  # type: ignore[arg-type]
                query_terms=list(retrieval.trace.query_terms),
                examined_chunks=retrieval.trace.examined_chunks,
                excluded_unknown_glyph_chunks=(retrieval.trace.excluded_unknown_glyph_chunks),
                eligible_chunks=retrieval.trace.eligible_chunks,
                rejected_by_source_boundary=retrieval.trace.rejected_by_source_boundary,
                returned_chunks=retrieval.trace.returned_chunks,
                selections=[
                    RetrievalSelection(
                        chunk_id=hit.chunk.chunk_id,
                        source=hit.chunk.source_code,  # type: ignore[arg-type]
                        score=round(hit.score, 6),
                        matched_terms=list(hit.matched_terms),
                    )
                    for hit in retrieval.hits
                ],
            ),
        )
        final = await self._remember(payload, final)
        return ChatExecution(
            final=final,
            trace=retrieval.trace,
            session_mode=self.conversations.mode,
        )

    async def aclose(self) -> None:
        await self.provider.aclose()

    async def _generate(self, request: LLMRequest) -> LLMResult:
        try:
            return await asyncio.wait_for(
                self.provider.generate(request), timeout=self.generation_timeout_seconds
            )
        except TimeoutError as exc:
            raise ProviderRequestError(
                "LLM provider timed out",
                retryable=True,
                code="provider_timeout",
            ) from exc

    async def _remember(
        self,
        payload: ChatRequest,
        final: ChatFinalEvent,
        *,
        context_eligible: bool = True,
    ) -> ChatFinalEvent:
        turn = await self.conversations.append(
            payload.conversation_id,
            ConversationTurn(
                user_message=payload.message,
                assistant_message=final.answer,
                request_id=final.request_id,
                route=final.route,
                context_eligible=context_eligible,
                response_payload=final.model_dump(mode="json"),
            ),
            session_id=payload.session_id,
        )
        return final.model_copy(
            update={"turn_id": UUID(turn.turn_id) if turn.turn_id is not None else None}
        )

    def _validate_generated_answer(
        self,
        *,
        answer: str,
        citations: tuple[Citation, ...],
        decision: RouteDecision,
        safety: SafetyResult,
        enforce_primary_references: bool = True,
    ) -> GeneratedAnswerValidation:
        evidence = self.validator.validate(
            answer=answer,
            citations=citations,
            decision=decision,
        )
        output = self.output_safety.validate(answer=answer, safety=safety)
        primary_ids = _primary_reference_ids(citations, decision)
        primary_error = ()
        if (
            enforce_primary_references
            and not safety.blocked_food_tags
            and not set(primary_ids) <= set(evidence.referenced_chunk_ids)
        ):
            primary_error = ("missing_primary_evidence_reference",)
        error_codes = tuple(
            dict.fromkeys((*evidence.error_codes, *output.error_codes, *primary_error))
        )
        return GeneratedAnswerValidation(
            valid=not error_codes,
            error_codes=error_codes,
            referenced_chunk_ids=evidence.referenced_chunk_ids,
        )

    def _build_evidence_fallback(
        self,
        *,
        citations: tuple[Citation, ...],
        decision: RouteDecision,
        safety: SafetyResult,
        query: str,
    ) -> str:
        intro = "以下内容直接摘自本次检索资料："
        statements: list[str] = []
        first_by_source: dict[str, Citation] = {}
        for citation in citations:
            first_by_source.setdefault(citation.source, citation)
        first_per_source = list(first_by_source.values())
        ordered = [
            *first_per_source,
            *(citation for citation in citations if citation not in first_per_source),
        ]

        for citation in ordered:
            if len(statements) >= FALLBACK_MAX_STATEMENTS:
                break
            statement = _safe_excerpt_statement(
                citation,
                query=query,
                blocked_food_tags=tuple(safety.blocked_food_tags),
            )
            if statement is None:
                continue
            trial = ensure_required_notice("\n".join((intro, *statements, statement)), safety)
            validation = self._validate_generated_answer(
                answer=trial,
                citations=citations,
                decision=decision,
                safety=safety,
                enforce_primary_references=False,
            )
            if validation.valid:
                statements.append(statement)

        if not statements:
            chunk_id = citations[0].chunk_id
            statements.append(f"已检索到相关资料，详细内容见引用【{chunk_id}】。")
        return ensure_required_notice("\n".join((intro, *statements)), safety)


def build_chat_pipeline(
    settings: Settings, *, conversations: ConversationStore | None = None
) -> ChatPipeline:
    if settings.retrieval_mode != "keyword":
        raise ChatPipelineError(
            code="retrieval_mode_not_ready",
            message="当前构建仅验证了 keyword 检索模式。",
            status_code=503,
        )
    return ChatPipeline(
        provider=build_llm_provider(settings),
        index=KnowledgeIndex.load_default(),
        conversations=conversations
        or build_conversation_store(
            mode=settings.resolved_conversation_store_mode,
            database_url=(
                settings.database_url.get_secret_value() if settings.database_url else None
            ),
            connect_timeout_seconds=settings.database_connect_timeout_seconds,
            statement_timeout_ms=settings.database_statement_timeout_ms,
        ),
        generation_timeout_seconds=settings.llm_timeout_seconds,
    )


def _system_prompt(safety: SafetyResult | None = None) -> str:
    base = (
        "你是 HealthPick 营养知识助手。只能使用 EVIDENCE 块中的事实。"
        "每个事实结论必须包含对应证据块的 ID，且引用只能严格写成【A-p01-c04】这种格式。"
        "禁止写成【Chunk-ID: A-p01-c04】、[A-p01-c04]或其他变体。"
        "禁止在同一个书名号中合并多个 ID；多个证据必须分别写成【A-p01-c04】【A-p03-c03】。"
        "回答至少包含一个合法引用，引用 ID 必须逐字匹配提供的 EVIDENCE ID。"
        "只输出一到三条短句，每条短句只陈述一个事实；引用必须紧跟该事实并放在句末标点前。"
        "优先使用与问题措辞最直接相关、排序最靠前的证据；问题询问数值时必须直接回答证据中的数值。"
        "不要输出开场白、总结、推理过程或未引用的标题。"
        "不得编造来源、页码、诊断或治疗结论。"
        "证据不足时明确拒答。"
    )
    if safety is None or safety.risk_level == "S0":
        return base
    blocked = ", ".join(safety.blocked_food_tags) or "(none)"
    return (
        f"{base}"
        f"本次确定性安全分级为 {safety.risk_level}，响应模式为 {safety.response_mode}。"
        f"硬过滤标签为 {blocked}。"
        "只能提供资料支持的一般原则，不得给出个体化热量、营养素精确目标、诊断、治疗或药物调整。"
        "答案主体附近必须提示用户咨询医生或注册营养师。"
    )


def _user_prompt(
    payload: ChatRequest,
    history: tuple[ConversationTurn, ...],
    context_blocks: tuple[str, ...],
) -> str:
    recent = history[-4:]
    history_text = "\n".join(
        f"user: {turn.user_message}\nassistant: {turn.assistant_message}" for turn in recent
    )
    profile = payload.profile_patch.model_dump_json() if payload.profile_patch else "{}"
    evidence = "\n\n".join(context_blocks)
    return "\n\n".join(
        (
            f"CONVERSATION_HISTORY:\n{history_text or '(none)'}",
            f"PROFILE_PATCH:\n{profile}",
            f"QUESTION:\n{payload.message}",
            evidence,
        )
    )


def _repair_prompt(
    error_codes: tuple[str, ...],
    allowed_chunk_ids: tuple[str, ...],
) -> str:
    errors = ", ".join(error_codes)
    allowed = ", ".join(allowed_chunk_ids)
    return (
        "上一回答未通过证据校验，请只重写答案，不要解释校验过程。"
        f"校验错误：{errors}。"
        f"允许使用的引用 ID 仅有：{allowed}。"
        "每个事实要点末尾至少放一个对应引用，严格使用【A-p01-c04】这种格式。"
        "只输出一到三条短句，每句只写一个事实；引用放在句末标点前。"
        "不得输出开场白、总结、道歉、推理过程、无引用标题或引用后的补充结论。"
        "不得使用列表外 ID，不得省略引用，不得新增证据中没有的事实。"
        "多个引用必须分别使用完整书名号，禁止用分号、逗号或斜杠合并 ID。"
        "若错误涉及安全提示，请保留一般信息边界并提示咨询医生或注册营养师；"
        "不得输出药物调整、诊断、疗效承诺或个体化精确数值。"
    )


def _log_validation_failure(
    *,
    request_id: str,
    attempt: int,
    answer: str,
    error_codes: tuple[str, ...],
    referenced_chunk_ids: tuple[str, ...],
) -> None:
    answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
    LOGGER.warning(
        "Evidence validation failed request_id=%s attempt=%s errors=%s "
        "referenced_chunk_ids=%s answer_sha256=%s answer_chars=%s",
        request_id,
        attempt,
        ",".join(error_codes),
        ",".join(referenced_chunk_ids),
        answer_digest,
        len(answer),
    )


def _log_safety_decision(*, request_id: str, safety: SafetyResult) -> None:
    LOGGER.info(
        "Safety decision request_id=%s risk=%s response_mode=%s rules=%s",
        request_id,
        safety.risk_level,
        safety.response_mode,
        ",".join(safety.matched_rules),
    )


def _log_evidence_fallback(
    *,
    request_id: str,
    error_codes: tuple[str, ...],
    referenced_chunk_ids: tuple[str, ...],
) -> None:
    LOGGER.warning(
        "Deterministic evidence fallback used request_id=%s errors=%s referenced_chunk_ids=%s",
        request_id,
        ",".join(error_codes),
        ",".join(referenced_chunk_ids),
    )


def _safe_excerpt_statement(
    citation: Citation, *, query: str, blocked_food_tags: tuple[str, ...] = ()
) -> str | None:
    excerpt = re.sub(r"【[ABC]-p\d{2}-c\d{2}】", "", citation.excerpt)
    candidates: list[tuple[int, int, str]] = []
    for raw_clause in FALLBACK_CLAUSE_SPLIT.split(excerpt):
        clause = " ".join(raw_clause.split()).strip(" -*#：:")
        if len(clause) < 8:
            continue
        if _contains_blocked_food(clause, blocked_food_tags):
            continue
        clause = clause[:180].rstrip("。！？!?；;")
        candidates.append((_fallback_relevance(query, clause), len(clause), clause))
    if not candidates:
        return None
    _, _, selected = max(candidates, key=lambda item: (item[0], item[1]))
    return f"资料原文：{selected}【{citation.chunk_id}】。"


def _contains_blocked_food(clause: str, blocked_food_tags: tuple[str, ...]) -> bool:
    return any(
        term in clause
        for tag in blocked_food_tags
        for term in FALLBACK_BLOCKED_FOOD_TERMS.get(tag, ())
    )


def _fallback_relevance(query: str, clause: str) -> int:
    query_terms = _fallback_terms(query)
    normalized_clause = "".join(clause.lower().split())
    score = sum(len(term) ** 2 for term in query_terms if term in normalized_clause)
    query_numbers = set(re.findall(r"\d+(?:\.\d+)?", query))
    clause_numbers = set(re.findall(r"\d+(?:\.\d+)?", clause))
    if query_numbers & clause_numbers:
        score += 20
    return score


def _fallback_terms(text: str) -> tuple[str, ...]:
    normalized = "".join(text.lower().split())
    segments = re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", normalized)
    terms: list[str] = []
    for segment in segments:
        if segment.isascii() or len(segment) <= 2:
            terms.append(segment)
            continue
        terms.extend(segment[index : index + 2] for index in range(len(segment) - 1))
        terms.extend(segment[index : index + 3] for index in range(len(segment) - 2))
    return tuple(dict.fromkeys(terms))


def _public_route(decision: RouteDecision) -> str:
    if decision.route in {"nutrition", "recommendation", "contraindication"}:
        return "nutrition"
    return decision.route


def _primary_reference_ids(
    citations: tuple[Citation, ...], decision: RouteDecision
) -> tuple[str, ...]:
    if not citations:
        return ()
    if decision.route != "mixed":
        return (citations[0].chunk_id,)
    core = next((item.chunk_id for item in citations if item.source in {"A", "B"}), None)
    platform = next((item.chunk_id for item in citations if item.source == "C"), None)
    return tuple(item for item in (core, platform) if item is not None)


def _deterministic_safety_answer(safety: SafetyResult) -> str:
    if safety.response_mode == "emergency_stop":
        return (
            "你描述的情况可能需要紧急医疗处理。请立即联系当地急救电话或尽快前往急诊；"
            "不要等待本系统继续生成饮食建议。"
        )
    return (
        "我不能提供停药、换药、剂量调整、极端减重或高风险个体化营养处方。"
        "请联系医生或药师评估；我可以继续提供不涉及治疗调整的一般饮食信息。"
    )


def _ensure_recommendation_notice(
    answer: str,
    preview: RecommendationEvaluation | None,
) -> str:
    notice = preview.professional_notice if preview else None
    normalized = answer.rstrip()
    if not notice or notice in normalized:
        return normalized
    return f"{normalized}\n\n{notice}。"
