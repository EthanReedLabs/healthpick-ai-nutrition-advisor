import type { components } from "@/lib/api-schema";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type AnonymousSession = components["schemas"]["AnonymousSession"];
export type AuthResponse = components["schemas"]["AuthResponse"];
export type AuthUser = components["schemas"]["AuthUser"];
export type AccountDataExport = components["schemas"]["AccountDataExport"];
export type ChatRequest = components["schemas"]["ChatRequest"];
export type ChatFinalEvent = components["schemas"]["ChatFinalEvent"];
export type Citation = components["schemas"]["Citation"];
export type ConversationDetail = components["schemas"]["ConversationDetail"];
export type ConversationList = components["schemas"]["ConversationList"];
export type ConversationSummary = components["schemas"]["ConversationSummary"];
export type ConversationTurn = components["schemas"]["ConversationTurnView"];
export type ErrorResponse = components["schemas"]["ErrorResponse"];
export type EvaluationSummaryResponse = components["schemas"]["EvaluationSummaryResponse"];
export type ProfilePatch = components["schemas"]["ProfilePatch"];
export type ProfileAssessment = components["schemas"]["ProfileAssessment"];
export type RecommendationEvaluation = components["schemas"]["RecommendationEvaluation"];
export type TransparencyResponse = components["schemas"]["TransparencyResponse"];

export const SYSTEM_BUSY_MESSAGE = "服务繁忙，请稍后重试";

const apiOrigin =
  process.env.NEXT_PUBLIC_API_ORIGIN?.replace(/\/$/, "") ??
  "http://127.0.0.1:8010";
// Production allows the model provider up to 45 seconds. Keep the browser
// deadline comfortably beyond that boundary so retrieval, validation and SSE
// delivery cannot lose a race with the client timer.
const defaultChatTimeoutMs = 75_000;
let activeAuthToken: string | null = null;

export type SendChatOptions = {
  requestId?: string;
  timeoutMs?: number;
  signal?: AbortSignal;
};

export class ApiClientError extends Error {
  constructor(
    public readonly payload: ErrorResponse,
    public readonly status: number,
  ) {
    super(payload.message);
    this.name = "ApiClientError";
  }
}

export function setAuthToken(token: string | null) {
  activeAuthToken = token;
}

function authHeaders(initial?: HeadersInit): Headers {
  const headers = new Headers(initial);
  if (activeAuthToken) headers.set("Authorization", `Bearer ${activeAuthToken}`);
  return headers;
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${apiOrigin}/healthz`, {
    cache: "no-store",
    signal,
  });
  const payload = (await response.json()) as HealthResponse | ErrorResponse;
  if (!response.ok) {
    throw new ApiClientError(payload as ErrorResponse, response.status);
  }
  return payload as HealthResponse;
}

export async function fetchTransparency(signal?: AbortSignal): Promise<TransparencyResponse> {
  return requestJson<TransparencyResponse>("/v1/transparency", {
    cache: "no-store",
    signal,
  });
}

export async function fetchEvaluationSummary(
  signal?: AbortSignal,
): Promise<EvaluationSummaryResponse> {
  return requestJson<EvaluationSummaryResponse>("/v1/evaluation/summary", {
    cache: "no-store",
    signal,
  });
}

export async function createAnonymousSession(): Promise<AnonymousSession> {
  return requestJson<AnonymousSession>("/v1/sessions/anonymous", { method: "POST" });
}

export async function registerAccount(payload: {
  email: string;
  password: string;
  anonymous_session_id: string;
}): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function loginAccount(payload: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function fetchCurrentAccount(): Promise<AuthUser> {
  return requestJson<AuthUser>("/v1/auth/me", { cache: "no-store" });
}

export async function logoutAccount(): Promise<void> {
  const response = await fetch(`${apiOrigin}/v1/auth/logout`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new ApiClientError((await response.json()) as ErrorResponse, response.status);
  }
}

export async function exportAccountData(): Promise<AccountDataExport> {
  return requestJson<AccountDataExport>("/v1/account/export", { cache: "no-store" });
}

export async function deleteAccount(password: string): Promise<void> {
  const response = await fetch(`${apiOrigin}/v1/account`, {
    method: "DELETE",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    throw new ApiClientError((await response.json()) as ErrorResponse, response.status);
  }
}

export async function createConversation(
  sessionId: string,
  title = "新对话",
): Promise<ConversationSummary> {
  return requestJson<ConversationSummary>("/v1/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, title }),
  });
}

export async function listConversations(sessionId: string): Promise<ConversationList> {
  const query = new URLSearchParams({ session_id: sessionId });
  return requestJson<ConversationList>(`/v1/conversations?${query}`, {
    cache: "no-store",
  });
}

export async function fetchConversation(
  sessionId: string,
  conversationId: string,
): Promise<ConversationDetail> {
  const query = new URLSearchParams({ session_id: sessionId });
  return requestJson<ConversationDetail>(
    `/v1/conversations/${encodeURIComponent(conversationId)}?${query}`,
    { cache: "no-store" },
  );
}

export async function renameConversation(
  sessionId: string,
  conversationId: string,
  title: string,
): Promise<ConversationSummary> {
  return requestJson<ConversationSummary>(
    `/v1/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, title }),
    },
  );
}

export async function deleteConversation(
  sessionId: string,
  conversationId: string,
): Promise<void> {
  const query = new URLSearchParams({ session_id: sessionId });
  const response = await fetch(
    `${apiOrigin}/v1/conversations/${encodeURIComponent(conversationId)}?${query}`,
    { method: "DELETE", headers: authHeaders() },
  );
  if (!response.ok) {
    throw new ApiClientError((await response.json()) as ErrorResponse, response.status);
  }
}

export async function assessProfile(profile: ProfilePatch): Promise<ProfileAssessment> {
  const response = await fetch(`${apiOrigin}/v1/profile/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  const payload = (await response.json()) as ProfileAssessment | ErrorResponse;
  if (!response.ok) {
    throw new ApiClientError(payload as ErrorResponse, response.status);
  }
  return payload as ProfileAssessment;
}

export async function evaluateRecommendation(
  profile: ProfilePatch,
): Promise<RecommendationEvaluation> {
  const response = await fetch(`${apiOrigin}/v1/recommendations/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  const payload = (await response.json()) as RecommendationEvaluation | ErrorResponse;
  if (!response.ok) {
    throw new ApiClientError(payload as ErrorResponse, response.status);
  }
  return payload as RecommendationEvaluation;
}

export async function sendChat(
  payload: ChatRequest,
  options: SendChatOptions = {},
): Promise<ChatFinalEvent> {
  const requestId = options.requestId ?? globalThis.crypto.randomUUID();
  const controller = new AbortController();
  let timedOut = false;
  const abortFromCaller = () => controller.abort();
  if (options.signal?.aborted) controller.abort();
  else options.signal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeoutId = globalThis.setTimeout(
    () => {
      timedOut = true;
      controller.abort();
    },
    options.timeoutMs ?? defaultChatTimeoutMs,
  );
  try {
    const response = await fetch(`${apiOrigin}/v1/chat/stream`, {
      method: "POST",
      headers: authHeaders({
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
      }),
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new ApiClientError(
        await readErrorResponse(response, requestId),
        response.status,
      );
    }
    const contentType = response.headers.get("Content-Type") ?? "";
    if (!contentType.toLowerCase().includes("text/event-stream")) {
      throw new ApiClientError(
        {
          code: "unexpected_response_content_type",
          message: "回答服务返回了非预期的响应格式。",
          request_id: requestId,
          retryable: true,
        },
        502,
      );
    }
    return parseFinalSse(await response.text(), requestId);
  } catch (caught) {
    if (caught instanceof ApiClientError) throw caught;
    if (options.signal?.aborted) {
      throw new ApiClientError(
        {
          code: "request_cancelled",
          message: "本次生成已由用户停止。",
          request_id: requestId,
          retryable: false,
        },
        499,
      );
    }
    if (timedOut) {
      throw new ApiClientError(
        {
          code: "client_timeout",
          message: "等待回答超时，请重试。",
          request_id: requestId,
          retryable: true,
        },
        408,
      );
    }
    throw new ApiClientError(
      {
        code: "connection_failed",
        message: SYSTEM_BUSY_MESSAGE,
        request_id: requestId,
        retryable: true,
      },
      0,
    );
  } finally {
    globalThis.clearTimeout(timeoutId);
    options.signal?.removeEventListener("abort", abortFromCaller);
  }
}

export async function cancelChat(requestId: string): Promise<void> {
  const response = await fetch(
    `${apiOrigin}/v1/chat/cancel/${encodeURIComponent(requestId)}`,
    { method: "POST", headers: authHeaders() },
  );
  if (!response.ok) {
    throw new ApiClientError(await readErrorResponse(response, requestId), response.status);
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiOrigin}${path}`, {
    ...init,
    headers: authHeaders(init?.headers),
  });
  const payload = (await response.json()) as T | ErrorResponse;
  if (!response.ok) {
    throw new ApiClientError(payload as ErrorResponse, response.status);
  }
  return payload as T;
}

export function parseFinalSse(
  body: string,
  requestId = "client-generated",
): ChatFinalEvent {
  const normalized = body.replace(/\r\n/g, "\n");
  for (const block of normalized.split("\n\n")) {
    const lines = block.split("\n");
    const event = lines.find((line) => line.startsWith("event: "))?.slice(7);
    if (event !== "final") continue;
    const data = lines
      .filter((line) => line.startsWith("data: "))
      .map((line) => line.slice(6))
      .join("\n");
    let payload: Partial<ChatFinalEvent>;
    try {
      payload = JSON.parse(data) as Partial<ChatFinalEvent>;
    } catch {
      continue;
    }
    if (
      typeof payload.request_id === "string" &&
      typeof payload.answer === "string" &&
      Array.isArray(payload.citations) &&
      payload.model &&
      payload.safety
    ) {
      return payload as ChatFinalEvent;
    }
  }
  throw new ApiClientError(
    {
      code: "invalid_sse_stream",
      message: "回答流缺少有效的 final 事件。",
      request_id: requestId,
      retryable: true,
    },
    502,
  );
}

async function readErrorResponse(
  response: Response,
  fallbackRequestId: string,
): Promise<ErrorResponse> {
  try {
    const payload = (await response.json()) as Partial<ErrorResponse>;
    if (
      typeof payload.code === "string" &&
      typeof payload.message === "string" &&
      typeof payload.request_id === "string" &&
      typeof payload.retryable === "boolean"
    ) {
      return { ...payload, request_id: fallbackRequestId } as ErrorResponse;
    }
  } catch {
    // Fall through to a stable local protocol error without exposing response content.
  }
  return {
    code: "invalid_error_response",
    message: "服务返回了无法识别的错误格式。",
    request_id: fallbackRequestId,
    retryable: response.status >= 500,
  };
}
