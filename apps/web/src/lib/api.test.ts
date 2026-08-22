import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiClientError,
  cancelChat,
  listConversations,
  parseFinalSse,
  sendChat,
  setAuthToken,
} from "./api";

const requestId = "f116eb45-eac7-4a60-aeb2-7aa9002f0175";
const chatPayload = {
  conversation_id: "demo",
  message: "膳食纤维有什么作用？",
};

afterEach(() => {
  setAuthToken(null);
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("account authorization", () => {
  it("adds the bearer token to protected history requests without leaking it into the URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    setAuthToken("account-secret-token");

    await listConversations("11111111-1111-4111-8111-111111111111");

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).not.toContain("account-secret-token");
    expect(new Headers(init.headers).get("Authorization"))
      .toBe("Bearer account-secret-token");
  });
});

describe("chat transport error boundaries", () => {
  it("rejects a malformed final event with a stable retryable error", () => {
    let caught: unknown;
    try {
      parseFinalSse("event: final\ndata: {not-json}\n\n", requestId);
    } catch (error) {
      caught = error;
    }
    expect(caught).toBeInstanceOf(ApiClientError);
    expect(caught).toMatchObject({
      payload: {
        code: "invalid_sse_stream",
        request_id: requestId,
        retryable: true,
      },
      status: 502,
    });
  });

  it("rejects a successful response whose content type is not SSE", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("{}", {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(sendChat(chatPayload, { requestId, timeoutMs: 100 })).rejects.toMatchObject({
      payload: {
        code: "unexpected_response_content_type",
        request_id: requestId,
        retryable: true,
      },
      status: 502,
    });
  });

  it("aborts a stalled request and preserves its request id for safe retry", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        }),
      ),
    );
    await expect(sendChat(chatPayload, { requestId, timeoutMs: 1 })).rejects.toMatchObject({
      payload: {
        code: "client_timeout",
        request_id: requestId,
        retryable: true,
      },
      status: 408,
    });
  });

  it("keeps the default client deadline beyond the 45-second provider budget", async () => {
    vi.useFakeTimers();
    const signals: AbortSignal[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          const signal = init?.signal;
          if (signal) {
            signals.push(signal);
            signal.addEventListener("abort", () => {
              reject(new DOMException("aborted", "AbortError"));
            });
          }
        }),
      ),
    );

    const pending = sendChat(chatPayload, { requestId });
    const rejection = expect(pending).rejects.toMatchObject({
      payload: { code: "client_timeout", request_id: requestId },
      status: 408,
    });

    await vi.advanceTimersByTimeAsync(45_000);
    expect(signals[0]?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(29_999);
    expect(signals[0]?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await rejection;
  });

  it("distinguishes an explicit caller cancellation from a timeout", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        }),
      ),
    );
    const controller = new AbortController();
    const pending = sendChat(chatPayload, {
      requestId,
      timeoutMs: 10_000,
      signal: controller.signal,
    });
    controller.abort();
    await expect(pending).rejects.toMatchObject({
      payload: {
        code: "request_cancelled",
        request_id: requestId,
        retryable: false,
      },
      status: 499,
    });
  });

  it("uses an idempotent server cancellation endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await cancelChat(requestId);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/v1/chat/cancel/${requestId}`),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not expose an invalid upstream error body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("private upstream stack", {
          status: 502,
          headers: { "Content-Type": "text/plain" },
        }),
      ),
    );
    await expect(sendChat(chatPayload, { requestId, timeoutMs: 100 })).rejects.toMatchObject({
      payload: {
        code: "invalid_error_response",
        request_id: requestId,
        retryable: true,
      },
      status: 502,
    });
  });

  it("keeps the client request id when an error body contains a mismatched id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "provider_timeout",
            message: "timeout",
            request_id: "00000000-0000-4000-8000-000000000000",
            retryable: true,
          }),
          {
            status: 504,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );
    await expect(sendChat(chatPayload, { requestId, timeoutMs: 100 })).rejects.toMatchObject({
      payload: {
        code: "provider_timeout",
        request_id: requestId,
        retryable: true,
      },
      status: 504,
    });
  });
});
