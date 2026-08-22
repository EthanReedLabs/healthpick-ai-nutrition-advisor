import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChatWorkspace from "./chat-workspace";

const healthPayload = {
  service: "healthpick-api",
  version: "0.1.0",
  status: "ok",
  environment: "development",
  modes: { llm: "mock", embedding: "disabled", retrieval: "keyword" },
  dependencies: {},
  request_id: "req-health",
};

function jsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function sseResponse(payload: unknown) {
  return Promise.resolve(
    new Response(`event: meta\ndata: {}\n\nevent: final\ndata: ${JSON.stringify(payload)}\n\n`, {
      status: 200,
      headers: { "Content-Type": "text/event-stream; charset=utf-8" },
    }),
  );
}

type ResponseFactory = () => Promise<Response>;

let responseQueue: ResponseFactory[] = [];
let conversationSequence = 0;
let conversationListOverride: ReturnType<typeof conversationSummary>[] | null = null;
let conversationDetailOverride: Record<string, unknown> | null = null;

function queueResponses(...responses: ResponseFactory[]) {
  responseQueue.push(...responses);
}

function conversationSummary(conversationId: string) {
  return {
    conversation_id: conversationId,
    session_id: "11111111-1111-4111-8111-111111111111",
    title: "新对话",
    created_at: "2026-08-21T12:00:00Z",
    updated_at: "2026-08-21T12:00:00Z",
    turn_count: 0,
  };
}

describe("ChatWorkspace", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  beforeEach(() => {
    globalThis.localStorage.clear();
    responseQueue = [];
    conversationSequence = 0;
    conversationListOverride = null;
    conversationDetailOverride = null;
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:healthpick-account-export"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/healthz")) return jsonResponse(healthPayload);
      if (url.endsWith("/v1/transparency")) {
        return jsonResponse({
          version: "0.1.0",
          model: { provider: "healthpick_mock", name: "mock-v1", mode: "mock" },
          failover: {
            enabled: false,
            policy: "retryable_or_invalid_response",
            fallback: null,
          },
          embedding: {
            provider: "disabled",
            name: "disabled",
            mode: "disabled",
            dimensions: null,
          },
          retrieval_mode: "keyword",
          conversation_store: "ephemeral",
          profile_persistence: "ephemeral",
          evidence_policy: "仅返回通过来源边界、逐条引用和输出安全校验的完整回答。",
          sources: [
            { source: "A", title: "资料A", allowed_use: "营养", forbidden_use: "平台" },
            { source: "B", title: "资料B", allowed_use: "方案", forbidden_use: "平台" },
            { source: "C", title: "资料C", allowed_use: "平台", forbidden_use: "营养" },
          ],
        });
      }
      if (url.endsWith("/v1/evaluation/summary")) {
        return jsonResponse({
          schema_version: 1,
          report_id: "release-v1.1-test",
          source_report_sha256: "a".repeat(64),
          dataset_version: "release-golden-v1.1",
          dataset_sha256: "b".repeat(64),
          case_count: 72,
          turn_count: 80,
          completed_at: "2026-08-22T13:21:40+08:00",
          automatic_status: "PASS",
          overall_status: "PASS",
          cleanup_status: "PASS",
          gates_passed: 9,
          gates_total: 9,
          metrics: {
            route_accuracy: 1,
            source_leakage_rate: 0,
            numeric_fact_accuracy: 1,
            citation_support_rate: 0.955882,
            high_risk_recall: 1,
            contraindication_conflict_rate: 0,
            multi_turn_constraint_rate: 1,
            unhandled_5xx: 0,
            first_response_p95_ms: 2814,
          },
          gates: {},
          manual_review: { status: "PASS", action: "ACTION-06 CLOSED", case_count: 53 },
          first_attempt_preserved: true,
          public_note: "自动发布门已通过；人工复核仍独立跟踪。",
        });
      }
      if (url.endsWith("/v1/sessions/anonymous")) {
        return jsonResponse({
          session_id: "11111111-1111-4111-8111-111111111111",
          created_at: "2026-08-21T12:00:00Z",
        }, 201);
      }
      if (url.endsWith("/v1/auth/register")) {
        return jsonResponse({
          user_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          email: "judge@example.com",
          created_at: "2026-08-22T10:00:00Z",
          access_token: "registered-account-token",
          token_type: "bearer",
          expires_at: "2026-09-21T10:00:00Z",
          session_id: "11111111-1111-4111-8111-111111111111",
        }, 201);
      }
      if (url.endsWith("/v1/account/export")) {
        return jsonResponse({
          export_version: "1.0",
          exported_at: "2026-08-22T11:55:00Z",
          user: {
            user_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            email: "judge@example.com",
            created_at: "2026-08-22T10:00:00Z",
            updated_at: "2026-08-22T10:00:00Z",
          },
          inventory: {
            users: 1,
            auth_sessions: 1,
            anonymous_sessions: 1,
            conversations: 1,
            conversation_turns: 0,
            total_records: 4,
          },
          auth_sessions: [],
          sessions: [],
          conversations: [],
          excluded_static_data: ["knowledge_chunks"],
        });
      }
      if (url.endsWith("/v1/account") && method === "DELETE") {
        return new Response(null, { status: 204 });
      }
      if (url.includes("/v1/conversations")) {
        if (method === "POST") {
          conversationSequence += 1;
          return jsonResponse(conversationSummary(
            `22222222-2222-4222-8222-${String(conversationSequence).padStart(12, "0")}`,
          ), 201);
        }
        if (/\/v1\/conversations\?/.test(url)) {
          return jsonResponse({ items: conversationListOverride ?? [] });
        }
        const conversationId = url.match(/\/v1\/conversations\/([^?]+)/)?.[1]
          ?? "22222222-2222-4222-8222-000000000001";
        if (method === "PATCH") {
          const title = JSON.parse(String(init?.body)).title;
          const updated = { ...conversationSummary(conversationId), title };
          conversationListOverride = (conversationListOverride ?? []).map((item) =>
            item.conversation_id === conversationId ? updated : item
          );
          return jsonResponse(updated);
        }
        return jsonResponse(
          conversationDetailOverride
            ?? { ...conversationSummary(conversationId), turns: [] },
        );
      }
      const response = responseQueue.shift();
      return response
        ? response()
        : Promise.reject(new Error(`Unexpected API request in test: ${method} ${url}`));
    }));
  });

  it("shows the explicit API and model mode", async () => {
    render(<ChatWorkspace />);
    expect(await screen.findAllByText("API 在线 · Mock")).toHaveLength(2);
    const heading = await screen.findByRole("heading", { name: "模型与检索透明度" });
    const card = heading.closest(".transparency-card") as HTMLElement;
    expect(card).toHaveTextContent("healthpick_mock / mock-v1");
    expect(card).toHaveTextContent("keyword");
    expect(card).toHaveTextContent("ephemeral");
    expect(card).toHaveTextContent("未启用");
    expect(card).toHaveTextContent("可重试故障 / 无效响应");
    const evaluationHeading = await screen.findByRole("heading", { name: "冻结评测概览" });
    const evaluationCard = evaluationHeading.closest(".evaluation-card") as HTMLElement;
    expect(evaluationCard).toHaveTextContent("9/9 自动门通过");
    expect(evaluationCard).toHaveTextContent("95.6%");
    expect(evaluationCard).toHaveTextContent("整体状态：已通过");
    expect(evaluationCard).toHaveTextContent("ACTION-06 CLOSED · 53 个事实用例完成复核");
  });

  it("registers the current anonymous session and adopts the server canonical session", async () => {
    render(<ChatWorkspace />);
    await screen.findByText(/完善健康档案后可生成规则匹配方案/);

    fireEvent.click(screen.getByRole("button", { name: "登录或注册" }));
    fireEvent.change(screen.getByLabelText("邮箱"), {
      target: { value: "judge@example.com" },
    });
    fireEvent.change(screen.getByLabelText("密码（至少 10 位）"), {
      target: { value: "competition-passphrase" },
    });
    fireEvent.click(screen.getByRole("button", { name: "注册并迁移历史" }));

    expect(await screen.findByText("judge@example.com")).toBeInTheDocument();
    const registerCall = vi.mocked(fetch).mock.calls.find(([input]) =>
      String(input).endsWith("/v1/auth/register")
    );
    expect(JSON.parse(String(registerCall?.[1]?.body))).toMatchObject({
      email: "judge@example.com",
      anonymous_session_id: "11111111-1111-4111-8111-111111111111",
    });
    expect(globalThis.localStorage.getItem("healthpick.auth-token"))
      .toBe("registered-account-token");
    const claimedHistoryCall = vi.mocked(fetch).mock.calls.find(([input], index) =>
      index > (registerCall ? vi.mocked(fetch).mock.calls.indexOf(registerCall) : -1)
        && String(input).includes("/v1/conversations?")
    );
    expect(new Headers(claimedHistoryCall?.[1]?.headers).get("Authorization"))
      .toBe("Bearer registered-account-token");
  });

  it("exports personal data and permanently deletes the account after password re-entry", async () => {
    render(<ChatWorkspace />);
    await screen.findByText(/完善健康档案后可生成规则匹配方案/);

    fireEvent.click(screen.getByRole("button", { name: "登录或注册" }));
    fireEvent.change(screen.getByLabelText("邮箱"), {
      target: { value: "judge@example.com" },
    });
    fireEvent.change(screen.getByLabelText("密码（至少 10 位）"), {
      target: { value: "competition-passphrase" },
    });
    fireEvent.click(screen.getByRole("button", { name: "注册并迁移历史" }));
    await screen.findByText("judge@example.com");

    fireEvent.click(screen.getByRole("button", { name: "打开账号信息" }));
    fireEvent.click(screen.getByRole("button", { name: "导出我的数据" }));
    expect(await screen.findByText("已导出 4 条个人数据记录。")).toBeInTheDocument();
    const exportCall = vi.mocked(fetch).mock.calls.find(([input]) =>
      String(input).endsWith("/v1/account/export"),
    );
    expect(new Headers(exportCall?.[1]?.headers).get("Authorization"))
      .toBe("Bearer registered-account-token");
    expect(URL.createObjectURL).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "永久删除账号" }));
    fireEvent.change(screen.getByLabelText("再次输入密码确认删除"), {
      target: { value: "competition-passphrase" },
    });
    fireEvent.click(screen.getByRole("button", { name: "确认永久删除" }));

    await screen.findByRole("button", { name: "登录或注册" });
    expect(globalThis.localStorage.getItem("healthpick.auth-token")).toBeNull();
    const deleteCall = vi.mocked(fetch).mock.calls.find(
      ([input, init]) => String(input).endsWith("/v1/account") && init?.method === "DELETE",
    );
    expect(new Headers(deleteCall?.[1]?.headers).get("Authorization"))
      .toBe("Bearer registered-account-token");
    expect(JSON.parse(String(deleteCall?.[1]?.body))).toEqual({
      password: "competition-passphrase",
    });
  });

  it("fills the composer from a quick question without fabricating an answer", async () => {
    render(<ChatWorkspace />);
    const quickQuestion = screen.getByRole("button", {
      name: "帮我设计一份高蛋白早餐",
    });
    fireEvent.click(quickQuestion);
    expect(screen.getByLabelText("输入营养或平台问题")).toHaveValue(
      "帮我设计一份高蛋白早餐",
    );
    expect(screen.queryByText("这是模型生成的答案")).not.toBeInTheDocument();
  });

  it("restores a persisted server conversation from the anonymous session id", async () => {
    const sessionId = "11111111-1111-4111-8111-111111111111";
    const conversationId = "22222222-2222-4222-8222-000000000099";
    const summary = {
      ...conversationSummary(conversationId),
      title: "已恢复的膳食纤维对话",
      turn_count: 1,
    };
    conversationListOverride = [summary];
    conversationDetailOverride = {
      ...summary,
      turns: [
        {
          turn_id: "33333333-3333-4333-8333-333333333333",
          request_id: "44444444-4444-4444-8444-444444444444",
          user_message: "刷新前的问题",
          assistant_message: "刷新后恢复的回答【A-p01-c04】。",
          route: "nutrition",
          created_at: "2026-08-21T12:01:00Z",
          response: {
            request_id: "44444444-4444-4444-8444-444444444444",
            turn_id: "33333333-3333-4333-8333-333333333333",
            answer: "刷新后恢复的回答【A-p01-c04】。",
            route: "nutrition",
            citations: [],
            safety: {
              risk_level: "S0",
              matched_rules: ["standard_nutrition_scope"],
              blocked_food_tags: [],
              allow_personalized_targets: true,
              required_notice: "general",
              response_mode: "normal",
            },
            model: { provider: "healthpick_mock", name: "mock-v1", mode: "mock" },
          },
        },
      ],
    };
    globalThis.localStorage.setItem("healthpick.anonymous-session-id", sessionId);

    render(<ChatWorkspace />);

    expect(await screen.findByText("刷新前的问题")).toBeInTheDocument();
    expect(screen.getByText("刷新后恢复的回答【A-p01-c04】。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /已恢复的膳食纤维对话/ }))
      .toHaveAttribute("aria-current", "page");
    expect(vi.mocked(fetch).mock.calls.some(([input]) =>
      String(input).endsWith("/v1/sessions/anonymous")
    )).toBe(false);
  });

  it("keeps a health-profile editor entry in the mobile header", async () => {
    render(<ChatWorkspace />);
    expect(await screen.findByRole("button", { name: "完善档案，生成规则方案" })).toBeInTheDocument();
    expect(screen.getByLabelText("开始新对话（移动端）")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("打开健康档案编辑器（移动端）"));
    expect(screen.getByRole("dialog", { name: "编辑健康档案" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("关闭健康档案编辑器"));
    fireEvent.click(screen.getByRole("button", { name: "完善档案，生成规则方案" }));
    expect(screen.getByRole("dialog", { name: "编辑健康档案" })).toBeInTheDocument();
  });

  it("surfaces the API error and states that no preset answer is used", async () => {
    queueResponses(() =>
      jsonResponse(
          {
            code: "chat_not_ready",
            message: "Chat pipeline is not implemented yet.",
            request_id: "req-chat",
            retryable: false,
          },
          503,
      ),
    );

    render(<ChatWorkspace />);
    fireEvent.change(screen.getByLabelText("输入营养或平台问题"), {
      target: { value: "什么是低钠饮食？" },
    });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("chat_not_ready");
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "不会用预置文本冒充模型结果",
    );
  });

  it("stops an active generation, confirms the server cancel, and preserves input", async () => {
    const baselineFetch = vi.mocked(fetch).getMockImplementation();
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/v1/chat/stream")) {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        });
      }
      if (url.includes("/v1/chat/cancel/")) {
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      if (!baselineFetch) throw new Error("baseline fetch is unavailable");
      return baselineFetch(input, init);
    });

    render(<ChatWorkspace />);
    const composer = screen.getByLabelText("输入营养或平台问题");
    fireEvent.change(composer, { target: { value: "请生成一个较长的低钠方案" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));

    await waitFor(() => {
      expect(vi.mocked(fetch).mock.calls.some(([input]) =>
        String(input).endsWith("/v1/chat/stream")
      )).toBe(true);
    });
    fireEvent.click(screen.getByRole("button", { name: "停止生成本次回答" }));

    expect(await screen.findByText(/服务端已取消，半成品不会保存/)).toBeInTheDocument();
    expect(composer).toHaveValue("请生成一个较长的低钠方案");
    await waitFor(() => expect(composer).toHaveFocus());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    const chatCall = vi.mocked(fetch).mock.calls.find(([input]) =>
      String(input).endsWith("/v1/chat/stream")
    );
    const requestId = new Headers(chatCall?.[1]?.headers).get("X-Request-ID");
    expect(requestId).toBeTruthy();
    expect(vi.mocked(fetch).mock.calls.some(([input], index) =>
      index > (chatCall ? vi.mocked(fetch).mock.calls.indexOf(chatCall) : -1)
      && String(input).endsWith(`/v1/chat/cancel/${requestId}`)
    )).toBe(true);
  });

  it("retries a transient failure with the same request id", async () => {
    const mismatchedServerRequestId = "77777777-7777-4777-8777-777777777777";
    queueResponses(
      () => jsonResponse(
        {
          code: "provider_timeout",
          message: "模型服务响应超时，请稍后重试。",
          request_id: mismatchedServerRequestId,
          retryable: true,
        },
        504,
      ),
      () => sseResponse({
        request_id: mismatchedServerRequestId,
        turn_id: "88888888-8888-4888-8888-888888888888",
        answer: "重试后回答【A-p01-c04】。",
        route: "nutrition",
        citations: [],
        safety: {
          risk_level: "S0",
          matched_rules: ["standard_nutrition_scope"],
          blocked_food_tags: [],
          allow_personalized_targets: true,
          required_notice: "general",
          response_mode: "normal",
        },
        model: { provider: "healthpick_mock", name: "mock-v1", mode: "mock" },
      }),
    );

    render(<ChatWorkspace />);
    fireEvent.change(screen.getByLabelText("输入营养或平台问题"), {
      target: { value: "可重试的问题" },
    });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));

    const retry = await screen.findByRole("button", { name: "使用同一请求编号重试" });
    const firstChatCall = vi.mocked(fetch).mock.calls.find(([input]) =>
      String(input).endsWith("/v1/chat/stream")
    );
    const originalRequestId = new Headers(firstChatCall?.[1]?.headers).get("X-Request-ID");
    expect(originalRequestId).toBeTruthy();
    expect(screen.getByRole("alert")).toHaveTextContent(originalRequestId!);
    expect(screen.getByRole("alert")).not.toHaveTextContent(mismatchedServerRequestId);
    fireEvent.click(retry);

    expect(await screen.findByText("重试后回答【A-p01-c04】。")).toBeInTheDocument();
    const chatCalls = vi.mocked(fetch).mock.calls.filter(([input]) =>
      String(input).endsWith("/v1/chat/stream")
    );
    expect(chatCalls).toHaveLength(2);
    expect(new Headers(chatCalls[1][1]?.headers).get("X-Request-ID")).toBe(originalRequestId);
  });

  it("renders the validated final event from an SSE response", async () => {
    queueResponses(() =>
      sseResponse({
          request_id: "req-final",
          answer: "这是带引用的测试回答【A-p01-c04】。",
          route: "nutrition",
          citations: [
            {
              source: "A",
              title: "2026秋季健康膳食指南",
              section: "1.2 微量营养素与膳食纤维",
              page: 1,
              chunk_id: "A-p01-c04",
              excerpt: "膳食纤维测试摘录",
            },
          ],
          safety: {
            risk_level: "S0",
            matched_rules: ["phase03_baseline"],
            required_notice: "general",
          },
          model: { provider: "healthpick_mock", name: "mock-v1", mode: "mock" },
          retrieval_trace: {
            mode: "keyword",
            route: "nutrition",
            route_components: ["recommendation"],
            allowed_sources: ["A", "B"],
            query_terms: ["膳食纤维", "作用"],
            examined_chunks: 68,
            excluded_unknown_glyph_chunks: 8,
            eligible_chunks: 20,
            rejected_by_source_boundary: 20,
            returned_chunks: 1,
            selections: [
              {
                chunk_id: "A-p01-c04",
                source: "A",
                score: 4.125,
                matched_terms: ["膳食纤维"],
              },
            ],
            evidence_gate: "passed",
          },
      }),
    );

    render(<ChatWorkspace />);
    fireEvent.change(screen.getByLabelText("输入营养或平台问题"), {
      target: { value: "膳食纤维有什么作用？" },
    });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));

    expect(await screen.findByText("这是带引用的测试回答【A-p01-c04】。"))
      .toBeInTheDocument();
    expect(screen.getByText("2026秋季健康膳食指南")).toBeInTheDocument();
    expect(screen.getByText("资料 A")).toBeInTheDocument();
    fireEvent.click(screen.getByText("检索 trace · 证据门禁通过"));
    const trace = screen.getByText("检索 trace · 证据门禁通过")
      .closest(".retrieval-trace") as HTMLElement;
    expect(trace).toHaveTextContent("A-p01-c04");
    expect(trace).toHaveTextContent("来源隔离拒绝 20");
    expect(trace).toHaveTextContent("分数 4.125");
  });

  it("validates an ephemeral profile and sends it with the next chat request", async () => {
    const fetchMock = vi.mocked(fetch);
    queueResponses(
      () => jsonResponse({
          profile: {
            age_band: "adult_18_44",
            sex: null,
            height_cm: 170,
            weight_kg: 65,
            activity_level: null,
            goal: "stable_glucose",
            dietary_preferences: [],
            allergies: ["shellfish"],
            disliked_foods: [],
            conditions: [],
          },
          bmi: {
            value: 22.5,
            height_cm: 170,
            weight_kg: 65,
            formula: "weight_kg / (height_m ** 2)",
            label: "系统估算",
          },
          persistence: "ephemeral",
          collected_fields: ["age_band", "height_cm", "weight_kg", "goal", "allergies"],
      }),
      () => jsonResponse({
          status: "blocked",
          generated_by: "deterministic_rules",
          primary: null,
          alternate: null,
          blocked_reasons: ["knowledge_second_person_review_required"],
          blocked_rule_ids: ["rule-B-plate_321", "rule-B-gi_categories"],
          requires_second_person_review: true,
      }),
      () => sseResponse({
          request_id: "req-profile-chat",
          answer: "档案已随请求参与本轮上下文。【A-p01-c04】",
          route: "nutrition",
          citations: [
            {
              source: "A",
              title: "2026秋季健康膳食指南",
              section: "1.2 微量营养素与膳食纤维",
              page: 1,
              chunk_id: "A-p01-c04",
              excerpt: "膳食纤维测试摘录",
            },
          ],
          safety: {
            risk_level: "S0",
            matched_rules: ["phase03_baseline"],
            required_notice: "general",
          },
          model: { provider: "healthpick_mock", name: "mock-v1", mode: "mock" },
        }),
      );

    render(<ChatWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "编辑健康档案" }));
    fireEvent.change(screen.getByLabelText("健康目标"), {
      target: { value: "stable_glucose" },
    });
    fireEvent.change(screen.getByLabelText("年龄段"), {
      target: { value: "adult_18_44" },
    });
    fireEvent.change(screen.getByLabelText("身高（cm）"), { target: { value: "170" } });
    fireEvent.change(screen.getByLabelText("体重（kg）"), { target: { value: "65" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "甲壳类海鲜" }));
    fireEvent.click(screen.getByRole("button", { name: "保存档案" }));

    expect(await screen.findByText(/BMI 22.5/)).toBeInTheDocument();
    expect(screen.getByText("稳糖")).toBeInTheDocument();
    expect(screen.getByText("甲壳类海鲜")).toBeInTheDocument();
    expect(screen.getByLabelText("结构化方案暂未放行")).toHaveTextContent(
      "候选事实尚未完成第二人复核",
    );

    fireEvent.change(screen.getByLabelText("输入营养或平台问题"), {
      target: { value: "膳食纤维有什么作用？" },
    });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));
    expect(await screen.findByText(/档案已随请求参与本轮上下文/)).toBeInTheDocument();

    const assessCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith("/v1/profile/assess"),
    );
    const chatCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith("/v1/chat/stream"),
    );
    const assessed = JSON.parse(String(assessCall?.[1]?.body));
    const chatPayload = JSON.parse(String(chatCall?.[1]?.body));
    expect(assessed).toMatchObject({
      age_band: "adult_18_44",
      height_cm: 170,
      weight_kg: 65,
      goal: "stable_glucose",
      allergies: ["shellfish"],
    });
    expect(chatPayload.profile_patch).toEqual(
      expect.objectContaining({
        age_band: "adult_18_44",
        goal: "stable_glucose",
        allergies: ["shellfish"],
      }),
    );
  });

  it("renders a deterministic primary recommendation card from a ready contract", async () => {
    queueResponses(
      () => jsonResponse({
          profile: {
            age_band: "adult_18_44",
            sex: "female",
            height_cm: null,
            weight_kg: null,
            activity_level: "moderate",
            goal: "fat_loss",
            dietary_preferences: [],
            allergies: [],
            disliked_foods: [],
            conditions: [],
          },
          bmi: null,
          persistence: "ephemeral",
          collected_fields: ["age_band", "sex", "activity_level", "goal"],
      }),
      () => jsonResponse({
          status: "ready",
          generated_by: "deterministic_rules",
          primary: {
            plan_id: "plan-fat_loss",
            title: "轻盈减脂",
            selection_score: 95,
            match_reasons: ["健康目标匹配：轻盈减脂", "活动水平已纳入规则输入：moderate"],
            key_targets: ["建议周期：8–12 周", "资料能量范围：1200–1500 kcal"],
            actions: ["先组织餐盘。", "再选择同类替换。", "按周记录并复核。"],
            substitutions: ["糙米 / 燕麦米 / 黑米"],
            evidence: [
              {
                rule_id: "rule-B-fat_loss_targets",
                source: "B",
                title: "轻盈减脂每日目标",
                section: "2.2 每日营养素目标",
                pages: [1],
                review_status: "verified",
              },
            ],
            blocked_food_tags: [],
          },
          alternate: null,
          blocked_reasons: [],
          blocked_rule_ids: [],
          requires_second_person_review: false,
      }),
    );

    render(<ChatWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "编辑健康档案" }));
    fireEvent.change(screen.getByLabelText("健康目标"), { target: { value: "fat_loss" } });
    fireEvent.change(screen.getByLabelText("年龄段"), { target: { value: "adult_18_44" } });
    fireEvent.change(screen.getByLabelText("性别"), { target: { value: "female" } });
    fireEvent.change(screen.getByLabelText("活动水平"), { target: { value: "moderate" } });
    fireEvent.click(screen.getByRole("button", { name: "保存档案" }));

    const card = await screen.findByLabelText("结构化主方案：轻盈减脂");
    expect(card).toHaveTextContent("规则匹配 95 分");
    expect(card).toHaveTextContent("资料能量范围：1200–1500 kcal");
    expect(card).toHaveTextContent("糙米 / 燕麦米 / 黑米");
    expect(card).toHaveTextContent("资料 B · 第 1 页");
  });

  it("shows readable S1 restrictions and every blocked food tag", async () => {
    queueResponses(() =>
      sseResponse({
          request_id: "req-s1",
          answer: "以下只提供已经过滤禁忌的一般搭配原则。【A-p01-c04】",
          route: "nutrition",
          citations: [
            {
              source: "A",
              title: "2026秋季健康膳食指南",
              section: "食物过敏",
              page: 1,
              chunk_id: "A-p01-c04",
              excerpt: "过敏与低钠测试摘录",
            },
          ],
          safety: {
            risk_level: "S1",
            matched_rules: ["profile_allergy_shellfish", "profile_hypertension"],
            blocked_food_tags: ["shellfish", "high_sodium"],
            allow_personalized_targets: false,
            required_notice: "professional",
            response_mode: "general_only",
          },
          model: { provider: "healthpick_mock", name: "mock-v1", mode: "mock" },
      }),
    );

    render(<ChatWorkspace />);
    fireEvent.change(screen.getByLabelText("输入营养或平台问题"), {
      target: { value: "海鲜过敏和高血压应该怎样搭配？" },
    });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));

    expect(await screen.findByRole("status", { name: /S1，约束过滤已启用/ }))
      .toBeInTheDocument();
    expect(screen.getByText("甲壳类海鲜")).toBeInTheDocument();
    expect(screen.getByText("高钠食物")).toBeInTheDocument();
    expect(screen.getByText("健康档案包含食物过敏")).toBeInTheDocument();
  });

  it("renders S3 as an explicit emergency stop without citations", async () => {
    queueResponses(() =>
      sseResponse({
          request_id: "req-s3",
          answer: "请立即联系当地急救电话或尽快前往急诊。",
          route: "nutrition",
          citations: [],
          safety: {
            risk_level: "S3",
            matched_rules: ["emergency_chest_pain"],
            blocked_food_tags: [],
            allow_personalized_targets: false,
            required_notice: "emergency",
            response_mode: "emergency_stop",
          },
          model: {
            provider: "healthpick_guard",
            name: "deterministic_safety_guard",
            mode: "mock",
          },
      }),
    );

    render(<ChatWorkspace />);
    fireEvent.change(screen.getByLabelText("输入营养或平台问题"), {
      target: { value: "我现在胸痛，应该吃什么？" },
    });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));

    expect(await screen.findByRole("alert", { name: /S3，紧急安全中止/ }))
      .toBeInTheDocument();
    expect(screen.getByText(/本轮未调用生成模型或资料检索/)).toBeInTheDocument();
    expect(screen.queryByText(/资料 A/)).not.toBeInTheDocument();
  });

  it("distinguishes evidence-gate failure from a connection error", async () => {
    queueResponses(() =>
      jsonResponse(
          {
            code: "insufficient_evidence",
            message: "指定资料中没有找到足够证据，无法生成回答。",
            request_id: "req-evidence",
            retryable: false,
          },
          422,
      ),
    );

    render(<ChatWorkspace />);
    fireEvent.change(screen.getByLabelText("输入营养或平台问题"), {
      target: { value: "资料里没有的特殊问题" },
    });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("证据不足，已停止生成");
    expect(alert).toHaveTextContent("未通过证据门禁的内容不会展示");
  });

  it("creates a fresh conversation id when the user starts a new chat", async () => {
    const makeFinal = (requestId: string, answer: string) => ({
      request_id: requestId,
      answer,
      route: "nutrition",
      citations: [
        {
          source: "A",
          title: "2026秋季健康膳食指南",
          section: "膳食纤维",
          page: 1,
          chunk_id: "A-p01-c04",
          excerpt: "膳食纤维测试摘录",
        },
      ],
      safety: {
        risk_level: "S0",
        matched_rules: ["standard_nutrition_scope"],
        blocked_food_tags: [],
        allow_personalized_targets: true,
        required_notice: "general",
        response_mode: "normal",
      },
      model: { provider: "healthpick_mock", name: "mock-v1", mode: "mock" },
    });
    const fetchMock = vi.mocked(fetch);
    queueResponses(
      () => sseResponse(makeFinal("first", "第一轮回答【A-p01-c04】")),
      () => sseResponse(makeFinal("second", "第二轮回答【A-p01-c04】")),
    );

    render(<ChatWorkspace />);
    const composer = screen.getByLabelText("输入营养或平台问题");
    fireEvent.change(composer, { target: { value: "第一轮问题" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));
    expect(await screen.findByText(/第一轮回答/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "新对话" }));
    expect(composer).toHaveValue("");
    fireEvent.change(composer, { target: { value: "第二轮问题" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/ }));
    expect(await screen.findByText(/第二轮回答/)).toBeInTheDocument();

    const chatCalls = fetchMock.mock.calls.filter(([input]) =>
      String(input).endsWith("/v1/chat/stream"),
    );
    const firstPayload = JSON.parse(String(chatCalls[0][1]?.body));
    const secondPayload = JSON.parse(String(chatCalls[1][1]?.body));
    expect(firstPayload.conversation_id).not.toBe(secondPayload.conversation_id);
  });

  it("distinguishes initial restoration from the ready empty state", async () => {
    render(<ChatWorkspace />);

    expect(screen.getByRole("status", { name: /正在恢复你的对话/ })).toBeInTheDocument();
    expect(screen.queryByText(/完善健康档案后可生成规则匹配方案/)).not.toBeInTheDocument();
    expect(await screen.findByText(/完善健康档案后可生成规则匹配方案/)).toBeInTheDocument();
  });

  it("recovers a failed session initialization in place", async () => {
    const baselineFetch = vi.mocked(fetch).getMockImplementation()!;
    let failedOnce = false;
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/v1/sessions/anonymous") && !failedOnce) {
        failedOnce = true;
        return jsonResponse(
          {
            code: "database_unavailable",
            message: "会话数据库暂时不可用。",
            request_id: "req-bootstrap-failed",
            retryable: true,
          },
          503,
        );
      }
      return baselineFetch(input, init);
    });

    render(<ChatWorkspace />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("对话暂时未就绪");
    expect(alert).toHaveTextContent("不需要前往其他面板");
    fireEvent.click(within(alert).getByRole("button", { name: "重新恢复对话" }));
    expect(await screen.findByText(/完善健康档案后可生成规则匹配方案/)).toBeInTheDocument();
  });

  it("opens mobile history and closes it with Escape", async () => {
    render(<ChatWorkspace />);
    await screen.findByRole("button", { name: /新对话，0 轮，当前对话/ });

    fireEvent.click(screen.getByRole("button", { name: "打开最近对话（移动端）" }));
    const dialog = screen.getByRole("dialog", { name: "最近对话" });
    expect(within(dialog).getByRole("button", { name: /新对话，0 轮，当前对话/ }))
      .toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "最近对话" })).not.toBeInTheDocument();
  });

  it("sends with Enter and preserves Shift+Enter for a newline", async () => {
    queueResponses(() =>
      sseResponse({
        request_id: "keyboard-request",
        turn_id: "88888888-8888-4888-8888-888888888889",
        answer: "键盘发送成功【A-p01-c04】。",
        route: "nutrition",
        citations: [],
        safety: {
          risk_level: "S0",
          matched_rules: ["standard_nutrition_scope"],
          blocked_food_tags: [],
          allow_personalized_targets: true,
          required_notice: "general",
          response_mode: "normal",
        },
        model: { provider: "healthpick_mock", name: "mock-v1", mode: "mock" },
      }),
    );
    render(<ChatWorkspace />);
    const composer = screen.getByLabelText("输入营养或平台问题");
    fireEvent.change(composer, { target: { value: "键盘问题" } });

    fireEvent.keyDown(composer, { key: "Enter", shiftKey: true });
    expect(vi.mocked(fetch).mock.calls.filter(([input]) =>
      String(input).endsWith("/v1/chat/stream")
    )).toHaveLength(0);
    fireEvent.keyDown(composer, { key: "Enter" });
    expect(await screen.findByText("键盘发送成功【A-p01-c04】。"))
      .toBeInTheDocument();
  });

  it("selects the next conversation after deleting the active one", async () => {
    const first = { ...conversationSummary("first-conversation"), title: "第一条对话" };
    const second = { ...conversationSummary("second-conversation"), title: "第二条对话" };
    conversationListOverride = [first, second];
    globalThis.localStorage.setItem(
      "healthpick.anonymous-session-id",
      "11111111-1111-4111-8111-111111111111",
    );
    render(<ChatWorkspace />);

    const firstSelect = await screen.findByRole("button", {
      name: /第一条对话，0 轮，当前对话/,
    });
    const firstRow = firstSelect.closest(".conversation-row") as HTMLElement;
    fireEvent.click(within(firstRow).getByRole("button", { name: "删除这条对话" }));
    fireEvent.click(within(firstRow).getByRole("button", { name: "确认" }));

    const secondSelect = await screen.findByRole("button", {
      name: /第二条对话，0 轮，当前对话/,
    });
    expect(secondSelect).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("button", { name: /第一条对话，0 轮/ }))
      .not.toBeInTheDocument();
  });

  it("filters history by title and persists an inline rename through the API", async () => {
    const first = { ...conversationSummary("first-conversation"), title: "膳食纤维记录" };
    const second = { ...conversationSummary("second-conversation"), title: "低钠早餐记录" };
    conversationListOverride = [first, second];
    globalThis.localStorage.setItem(
      "healthpick.anonymous-session-id",
      "11111111-1111-4111-8111-111111111111",
    );
    render(<ChatWorkspace />);

    const search = await screen.findByRole("searchbox", { name: "搜索最近对话" });
    fireEvent.change(search, { target: { value: "纤维" } });
    expect(screen.getByRole("button", { name: /膳食纤维记录/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /低钠早餐记录/ })).not.toBeInTheDocument();

    const row = screen.getByRole("button", { name: /膳食纤维记录/ })
      .closest(".conversation-row") as HTMLElement;
    fireEvent.click(within(row).getByRole("button", { name: "重命名这条对话" }));
    fireEvent.change(within(row).getByRole("textbox", { name: "重命名 膳食纤维记录" }), {
      target: { value: "膳食纤维复盘" },
    });
    fireEvent.click(within(row).getByRole("button", { name: "保存" }));

    expect(await screen.findByRole("button", { name: /膳食纤维复盘/ }))
      .toBeInTheDocument();
    const patchCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(patchCall?.[1]?.body))).toMatchObject({
      session_id: "11111111-1111-4111-8111-111111111111",
      title: "膳食纤维复盘",
    });
  });
});
