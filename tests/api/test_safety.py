from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from healthpick_api.chat import (
    ChatPipeline,
    ConversationTurn,
    EphemeralConversationStore,
)
from healthpick_api.config import Settings
from healthpick_api.main import create_app
from healthpick_api.models import ChatRequest
from healthpick_api.profile import ProfilePatch
from healthpick_api.providers import LLMRequest, LLMResult
from healthpick_api.retrieval import KnowledgeIndex
from healthpick_api.safety import (
    FoodCandidate,
    OutputSafetyValidator,
    SafetyService,
    ensure_required_notice,
)


def parse_final(body: str) -> dict:
    for block in body.strip().replace("\r\n", "\n").split("\n\n"):
        if block.startswith("event: final"):
            data = next(line[6:] for line in block.splitlines() if line.startswith("data: "))
            return json.loads(data)
    raise AssertionError("missing final event")


@pytest.mark.parametrize(
    "message",
    [
        "我现在胸痛而且胸口像被压住。",
        "我呼吸困难，说不出完整的话。",
        "家人低血糖抽搐并失去意识。",
        "吃虾后严重过敏，喉咙肿了。",
    ],
)
def test_emergency_signals_are_s3_and_stop_generation(message: str) -> None:
    result = SafetyService().assess(message)
    assert result.risk_level == "S3"
    assert result.response_mode == "emergency_stop"
    assert result.required_notice == "emergency"
    assert result.allow_personalized_targets is False


def test_medication_adjustment_is_refused_before_generation() -> None:
    result = SafetyService().assess("我想停药并调整剂量，饮食怎么配？")
    assert result.risk_level == "S2"
    assert result.response_mode == "refuse"
    assert "medication_adjustment_forbidden" in result.matched_rules


def test_s2_profile_allows_only_general_guidance() -> None:
    result = SafetyService().assess(
        "膳食纤维有什么作用？",
        ProfilePatch(conditions=["kidney_disease"]),
    )
    assert result.risk_level == "S2"
    assert result.response_mode == "general_only"
    assert result.allow_personalized_targets is False
    assert "profile_kidney_disease" in result.matched_rules


def test_high_risk_precise_prescription_is_refused() -> None:
    result = SafetyService().assess(
        "请给我精确热量和每天吃多少克蛋白质",
        ProfilePatch(conditions=["kidney_disease"]),
    )
    assert result.risk_level == "S2"
    assert result.response_mode == "refuse"


def test_allergy_and_condition_create_s1_hard_filter_tags() -> None:
    result = SafetyService().assess(
        "帮我搭配早餐",
        ProfilePatch(
            allergies=["shellfish", "milk"],
            conditions=["hypertension"],
        ),
    )
    assert result.risk_level == "S1"
    assert set(result.blocked_food_tags) == {"shellfish", "dairy", "high_sodium"}
    assert result.allow_personalized_targets is False


def test_message_only_allergy_creates_a_hard_filter_tag() -> None:
    result = SafetyService().assess("我海鲜过敏，早餐怎么吃？")
    assert result.risk_level == "S1"
    assert "shellfish" in result.blocked_food_tags


def test_candidate_filter_rejects_before_any_model_prompt() -> None:
    service = SafetyService()
    safety = service.assess(
        "帮我搭配早餐",
        ProfilePatch(allergies=["shellfish"], dietary_preferences=["low_sodium"]),
    )
    result = service.filter_candidates(
        (
            FoodCandidate("oatmeal", frozenset({"whole_grain"})),
            FoodCandidate("shrimp-bowl", frozenset({"shellfish"})),
            FoodCandidate("salty-soup", frozenset({"high_sodium"})),
        ),
        safety,
    )
    assert [candidate.candidate_id for candidate in result.allowed] == ["oatmeal"]
    assert result.rejected_ids == ("shrimp-bowl", "salty-soup")


def test_standard_query_remains_s0() -> None:
    result = SafetyService().assess("膳食纤维有什么营养作用？")
    assert result.risk_level == "S0"
    assert result.response_mode == "normal"
    assert result.allow_personalized_targets is True


def test_required_notice_is_appended_deterministically() -> None:
    service = SafetyService()
    general = service.assess("膳食纤维有什么作用？")
    professional = service.assess(
        "膳食纤维有什么作用？",
        ProfilePatch(conditions=["kidney_disease"]),
    )
    general_answer = ensure_required_notice("一般回答【A-p01-c04】", general)
    professional_answer = ensure_required_notice("一般回答【A-p01-c04】", professional)
    assert "仅供参考" in general_answer
    assert "咨询医生或注册营养师" in professional_answer
    assert (
        OutputSafetyValidator()
        .validate(
            answer=general_answer,
            safety=general,
        )
        .valid
    )
    assert (
        OutputSafetyValidator()
        .validate(
            answer=professional_answer,
            safety=professional,
        )
        .valid
    )


@pytest.mark.parametrize(
    ("answer", "error_code"),
    [
        ("建议你调整剂量。", "forbidden_medication_directive"),
        ("你已经确诊为糖尿病。", "forbidden_diagnosis"),
        ("这个方案保证有效并能根治疾病。", "forbidden_absolute_treatment_claim"),
    ],
)
def test_output_validator_rejects_high_risk_generated_claims(
    answer: str,
    error_code: str,
) -> None:
    safety = SafetyService().assess("膳食纤维有什么作用？")
    validation = OutputSafetyValidator().validate(
        answer=ensure_required_notice(answer, safety),
        safety=safety,
    )
    assert error_code in validation.error_codes


class ForbiddenProvider:
    mode = "mock"
    provider_name = "must-not-run"
    model_name = "must-not-run"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: LLMRequest) -> LLMResult:
        del request
        self.calls += 1
        raise AssertionError("provider must not run for deterministic safety stops")

    async def aclose(self) -> None:
        return None


class CapturingProvider:
    mode = "mock"
    provider_name = "capture"
    model_name = "capture-v1"

    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        return LLMResult(
            content="膳食纤维可来自燕麦等食物。【A-p01-c04】",
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=0,
        )

    async def aclose(self) -> None:
        return None


class PreciseThenSafeProvider(CapturingProvider):
    async def generate(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        if len(self.requests) == 1:
            content = "建议每天摄入999克蛋白质。【A-p01-c04】"
        else:
            assert "forbidden_precise_target" in request.messages[-1].content
            content = "膳食纤维有助于促进肠道蠕动。【A-p01-c04】"
        return LLMResult(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=0,
        )


@pytest.mark.parametrize(
    ("message", "expected_level", "expected_mode"),
    [
        ("我胸痛而且呼吸困难。", "S3", "emergency_stop"),
        ("请告诉我怎么停药并调整剂量。", "S2", "refuse"),
    ],
)
def test_api_stops_high_risk_requests_before_provider(
    message: str,
    expected_level: str,
    expected_mode: str,
) -> None:
    provider = ForbiddenProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    app = create_app(
        Settings(app_env="test", llm_mode="mock", embedding_mode="disabled"),
        chat_pipeline=pipeline,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/chat/stream",
            json={"conversation_id": "safety-stop", "message": message},
        )
    assert response.status_code == 200
    final = parse_final(response.text)
    assert final["safety"]["risk_level"] == expected_level
    assert final["safety"]["response_mode"] == expected_mode
    assert final["citations"] == []
    assert final["model"]["provider"] == "healthpick_guard"
    assert provider.calls == 0


def test_api_marks_profile_constrained_general_answer_as_s2() -> None:
    app = create_app(Settings(app_env="test", llm_mode="mock", embedding_mode="disabled"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/chat/stream",
            json={
                "conversation_id": "safety-profile",
                "message": "膳食纤维有什么营养作用？",
                "profile_patch": {"conditions": ["kidney_disease"]},
            },
        )
    assert response.status_code == 200
    final = parse_final(response.text)
    assert final["safety"]["risk_level"] == "S2"
    assert final["safety"]["response_mode"] == "general_only"
    assert final["safety"]["allow_personalized_targets"] is False
    assert final["citations"]
    assert "咨询医生或注册营养师" in final["answer"]


def test_pipeline_repairs_a_precise_s2_target_once_and_adds_notice() -> None:
    provider = PreciseThenSafeProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    app = create_app(
        Settings(app_env="test", llm_mode="mock", embedding_mode="disabled"),
        chat_pipeline=pipeline,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/chat/stream",
            json={
                "conversation_id": "s2-output-repair",
                "message": "膳食纤维有什么营养作用？",
                "profile_patch": {"conditions": ["kidney_disease"]},
            },
        )
    assert response.status_code == 200
    final = parse_final(response.text)
    assert len(provider.requests) == 2
    assert "999克" not in final["answer"]
    assert "咨询医生或注册营养师" in final["answer"]


@pytest.mark.anyio
async def test_emergency_stop_clears_history_and_does_not_pollute_next_turn() -> None:
    store = EphemeralConversationStore()
    await store.append(
        "continuous-session",
        ConversationTurn(
            user_message="上一轮普通问题",
            assistant_message="上一轮普通回答",
            request_id="before-s3",
            route="nutrition",
        ),
    )
    provider = CapturingProvider()
    pipeline = ChatPipeline(
        provider=provider,
        index=KnowledgeIndex.load_default(),
        conversations=store,
    )

    await pipeline.run(
        ChatRequest(
            conversation_id="continuous-session",
            message="我现在胸痛而且呼吸困难。",
        ),
        request_id="s3-stop",
    )
    assert await store.history("continuous-session") == ()
    assert provider.requests == []

    await pipeline.run(
        ChatRequest(
            conversation_id="continuous-session",
            message="膳食纤维有什么营养作用？",
        ),
        request_id="after-s3",
    )
    assert len(provider.requests) == 1
    user_prompt = provider.requests[0].messages[-1].content
    assert "胸痛" not in user_prompt
    assert "呼吸困难" not in user_prompt
    assert "上一轮普通问题" not in user_prompt


@pytest.mark.anyio
async def test_deterministic_refusal_is_not_committed_to_generation_history() -> None:
    store = EphemeralConversationStore()
    provider = ForbiddenProvider()
    pipeline = ChatPipeline(
        provider=provider,
        index=KnowledgeIndex.load_default(),
        conversations=store,
    )
    await pipeline.run(
        ChatRequest(
            conversation_id="refusal-session",
            message="请告诉我怎么停药并调整剂量。",
        ),
        request_id="refusal",
    )
    assert await store.history("refusal-session") == ()
