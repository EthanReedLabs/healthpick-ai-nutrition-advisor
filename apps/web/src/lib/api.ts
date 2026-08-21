import type { components } from "@/lib/api-schema";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type ChatRequest = components["schemas"]["ChatRequest"];
export type ChatFinalEvent = components["schemas"]["ChatFinalEvent"];
export type Citation = components["schemas"]["Citation"];
export type ErrorResponse = components["schemas"]["ErrorResponse"];

const apiOrigin =
  process.env.NEXT_PUBLIC_API_ORIGIN?.replace(/\/$/, "") ??
  "http://127.0.0.1:8010";

export class ApiClientError extends Error {
  constructor(
    public readonly payload: ErrorResponse,
    public readonly status: number,
  ) {
    super(payload.message);
    this.name = "ApiClientError";
  }
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

export async function sendChat(payload: ChatRequest): Promise<ChatFinalEvent> {
  const response = await fetch(`${apiOrigin}/v1/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = (await response.json()) as ErrorResponse;
    throw new ApiClientError(body as ErrorResponse, response.status);
  }
  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("text/event-stream")) {
    return parseFinalSse(await response.text());
  }
  return (await response.json()) as ChatFinalEvent;
}

export function parseFinalSse(body: string): ChatFinalEvent {
  const normalized = body.replace(/\r\n/g, "\n");
  for (const block of normalized.split("\n\n")) {
    const lines = block.split("\n");
    const event = lines.find((line) => line.startsWith("event: "))?.slice(7);
    if (event !== "final") continue;
    const data = lines
      .filter((line) => line.startsWith("data: "))
      .map((line) => line.slice(6))
      .join("\n");
    const payload = JSON.parse(data) as Partial<ChatFinalEvent>;
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
      request_id: "client-generated",
      retryable: true,
    },
    502,
  );
}
