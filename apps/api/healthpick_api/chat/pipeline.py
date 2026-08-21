"""One fail-closed chat path from intent to validated evidence-backed final event."""

from __future__ import annotations

from dataclasses import dataclass

from healthpick_api.config import Settings
from healthpick_api.evidence import CitationBuilder, EvidenceValidator
from healthpick_api.models import (
    ChatFinalEvent,
    ChatRequest,
    ModelInfo,
    SafetyResult,
)
from healthpick_api.providers import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    build_llm_provider,
)
from healthpick_api.retrieval import KeywordRetriever, KnowledgeIndex, RetrievalTrace
from healthpick_api.routing import QueryRouter, RouteDecision

from .conversation import ConversationTurn, EphemeralConversationStore


@dataclass(frozen=True, slots=True)
class ChatExecution:
    final: ChatFinalEvent
    trace: RetrievalTrace | None
    session_mode: str


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
        conversations: EphemeralConversationStore | None = None,
    ) -> None:
        self.provider = provider
        self.router = QueryRouter()
        self.retriever = KeywordRetriever(index)
        self.citations = CitationBuilder()
        self.validator = EvidenceValidator(index)
        self.conversations = conversations or EphemeralConversationStore()

    async def run(self, payload: ChatRequest, *, request_id: str) -> ChatExecution:
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
            await self._remember(payload, final)
            return ChatExecution(
                final=final,
                trace=None,
                session_mode=self.conversations.mode,
            )

        retrieval = self.retriever.search(payload.message, decision, limit=6)
        if not retrieval.hits:
            raise ChatPipelineError(
                code="insufficient_evidence",
                message="指定资料中没有找到足够证据，无法生成回答。",
                status_code=422,
            )
        bundle = self.citations.build(retrieval)
        history = await self.conversations.history(payload.conversation_id)
        result = await self.provider.generate(
            LLMRequest(
                messages=(
                    LLMMessage(role="system", content=_system_prompt()),
                    LLMMessage(
                        role="user",
                        content=_user_prompt(payload, history, bundle.context_blocks),
                    ),
                ),
                request_id=request_id,
            )
        )
        validation = self.validator.validate(
            answer=result.content,
            citations=bundle.citations,
            decision=decision,
        )
        if not validation.valid:
            raise ChatPipelineError(
                code="evidence_validation_failed",
                message="模型输出未通过证据完整性校验，已阻止返回。",
                status_code=502,
            )

        final = ChatFinalEvent(
            request_id=request_id,
            answer=result.content,
            route=_public_route(decision),
            citations=list(bundle.citations),
            safety=_phase_three_safety(decision),
            model=ModelInfo(
                provider=result.provider,
                name=result.model,
                mode=result.mode,
            ),
        )
        await self._remember(payload, final)
        return ChatExecution(
            final=final,
            trace=retrieval.trace,
            session_mode=self.conversations.mode,
        )

    async def aclose(self) -> None:
        await self.provider.aclose()

    async def _remember(self, payload: ChatRequest, final: ChatFinalEvent) -> None:
        await self.conversations.append(
            payload.conversation_id,
            ConversationTurn(
                user_message=payload.message,
                assistant_message=final.answer,
                request_id=final.request_id,
                route=final.route,
            ),
        )


def build_chat_pipeline(settings: Settings) -> ChatPipeline:
    if settings.retrieval_mode != "keyword":
        raise ChatPipelineError(
            code="retrieval_mode_not_ready",
            message="当前构建仅验证了 keyword 检索模式。",
            status_code=503,
        )
    return ChatPipeline(
        provider=build_llm_provider(settings),
        index=KnowledgeIndex.load_default(),
    )


def _system_prompt() -> str:
    return (
        "你是 HealthPick 营养知识助手。只能使用 EVIDENCE 块中的事实。"
        "每个事实结论必须包含对应的【Chunk-ID】；不得编造来源、页码、诊断或治疗结论。"
        "证据不足时明确拒答。"
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
            f"EPHEMERAL_HISTORY:\n{history_text or '(none)'}",
            f"PROFILE_PATCH:\n{profile}",
            f"QUESTION:\n{payload.message}",
            evidence,
        )
    )


def _public_route(decision: RouteDecision) -> str:
    if decision.route in {"nutrition", "recommendation", "contraindication"}:
        return "nutrition"
    return decision.route


def _phase_three_safety(decision: RouteDecision) -> SafetyResult:
    if "contraindication" in decision.components:
        return SafetyResult(
            risk_level="S2",
            matched_rules=["phase03_contraindication_baseline", "p04_rules_pending"],
            required_notice="professional",
        )
    return SafetyResult(
        risk_level="S0",
        matched_rules=["phase03_baseline", "p04_rules_pending"],
        required_notice="general",
    )
