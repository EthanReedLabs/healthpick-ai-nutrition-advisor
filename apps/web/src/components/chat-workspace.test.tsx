import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

describe("ChatWorkspace", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(healthPayload)));
  });

  it("shows the explicit API and model mode", async () => {
    render(<ChatWorkspace />);
    expect(await screen.findAllByText("API 在线 · Mock")).toHaveLength(2);
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

  it("surfaces the API error and states that no preset answer is used", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockImplementationOnce(() => jsonResponse(healthPayload))
      .mockImplementationOnce(() =>
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

  it("renders the validated final event from an SSE response", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockImplementationOnce(() => jsonResponse(healthPayload))
      .mockImplementationOnce(() =>
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
  });
});
