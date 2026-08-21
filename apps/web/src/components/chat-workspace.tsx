"use client";

import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import {
  ApiClientError,
  fetchHealth,
  sendChat,
  type ChatFinalEvent,
  type Citation,
  type HealthResponse,
} from "@/lib/api";

const starterQuestions = [
  "低钠饮食应该怎样搭配一日三餐？",
  "帮我设计一份高蛋白早餐",
  "平台能否替代医生给出诊断？",
];

const profileItems = [
  ["目标", "稳糖与体重管理"],
  ["饮食偏好", "清淡、少油"],
  ["过敏原", "尚未填写"],
];

function Mark({ children }: { children: ReactNode }) {
  return <span className="brand-mark">{children}</span>;
}

function ConnectionBadge({ health }: { health: HealthResponse | null }) {
  const mode = health?.modes.llm ?? "unknown";
  const label = !health
    ? "API 离线"
    : mode === "mock"
      ? "API 在线 · Mock"
      : "API 在线 · Real";

  return (
    <span
      className={`connection-badge ${health ? "is-online" : "is-offline"}`}
      aria-label={`当前连接状态：${label}`}
    >
      <span className="status-dot" aria-hidden="true" />
      {label}
    </span>
  );
}

function CitationCard({ citation }: { citation: Citation }) {
  return (
    <article className={`citation-card source-${citation.source.toLowerCase()}`}>
      <div className="citation-head">
        <span className="source-chip">资料 {citation.source}</span>
        <span>第 {citation.page} 页</span>
      </div>
      <h3>{citation.title}</h3>
      <p>{citation.excerpt}</p>
      <small>{citation.section}</small>
    </article>
  );
}

export default function ChatWorkspace() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState<ChatFinalEvent | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then(setHealth)
      .catch(() => setHealth(null));
    return () => controller.abort();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || pending) return;

    setPending(true);
    setError("");
    setAnswer(null);
    try {
      const result = await sendChat({
        conversation_id: "web-demo-session",
        message: trimmed,
      });
      setAnswer(result);
    } catch (caught) {
      setError(
        caught instanceof ApiClientError
          ? `${caught.payload.message}（${caught.payload.code}）`
          : "暂时无法连接服务，请确认 API 已启动。",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="left-rail" aria-label="主导航">
        <div className="brand-lockup">
          <Mark>H</Mark>
          <div>
            <strong>HealthPick</strong>
            <span>营养知识助手</span>
          </div>
        </div>

        <button className="new-chat" type="button" onClick={() => setAnswer(null)}>
          <span aria-hidden="true">＋</span> 新对话
        </button>

        <nav className="nav-list">
          <a className="active" href="#workspace">
            <span aria-hidden="true">◌</span> 营养问答
          </a>
          <a href="#profile">
            <span aria-hidden="true">◇</span> 健康档案
          </a>
          <a href="#sources">
            <span aria-hidden="true">▤</span> 资料来源
          </a>
        </nav>

        <section className="rail-note">
          <span>安全边界</span>
          <p>仅提供营养科普与平台说明，不替代专业诊断和治疗。</p>
        </section>
      </aside>

      <main className="workspace" id="workspace">
        <header className="mobile-header">
          <div className="brand-lockup compact">
            <Mark>H</Mark>
            <strong>HealthPick</strong>
          </div>
          <ConnectionBadge health={health} />
        </header>

        <div className="workspace-head">
          <div>
            <span className="eyebrow">EVIDENCE-GROUNDED NUTRITION</span>
            <h1>你好，今天想了解什么？</h1>
            <p>我会依据指定资料回答，并标注可核验的来源。</p>
          </div>
          <div className="desktop-status">
            <ConnectionBadge health={health} />
          </div>
        </div>

        <section className="assistant-message" aria-live="polite">
          {!answer && !error && (
            <>
              <Mark>H</Mark>
              <div>
                <strong>HealthPick 助手</strong>
                <p>
                  你可以询问日常营养搭配、健康饮食原则，或平台规则。回答会区分资料 A、B、C；没有证据时会明确说明。
                </p>
              </div>
            </>
          )}

          {answer && (
            <>
              <Mark>H</Mark>
              <div>
                <div className="answer-meta">
                  <strong>HealthPick 助手</strong>
                  <span>{answer.safety.risk_level}</span>
                  <span>{answer.model.mode}</span>
                </div>
                <p>{answer.answer}</p>
                <div className="inline-citations">
                  {answer.citations.map((citation) => (
                    <CitationCard key={citation.chunk_id} citation={citation} />
                  ))}
                </div>
              </div>
            </>
          )}

          {error && (
            <div className="error-card" role="alert">
              <strong>回答服务尚未就绪</strong>
              <p>{error}</p>
              <small>当前界面不会用预置文本冒充模型结果。</small>
            </div>
          )}
        </section>

        <section className="quick-start" aria-label="快捷提问">
          <span>试试这样问</span>
          <div>
            {starterQuestions.map((question) => (
              <button key={question} type="button" onClick={() => setMessage(question)}>
                {question}
              </button>
            ))}
          </div>
        </section>

        <form className="composer" onSubmit={submit}>
          <label htmlFor="chat-message" className="sr-only">
            输入营养或平台问题
          </label>
          <textarea
            id="chat-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="输入营养、健康饮食或平台相关问题…"
            rows={2}
            maxLength={2000}
          />
          <div className="composer-foot">
            <span>{message.length}/2000 · Enter 发送</span>
            <button type="submit" disabled={!message.trim() || pending}>
              {pending ? "处理中…" : "发送"}
              <span aria-hidden="true">↗</span>
            </button>
          </div>
        </form>

        <p className="workspace-disclaimer">
          AI 生成内容仅供参考；涉及疾病、药物、急症或个体治疗，请咨询专业人员。
        </p>
      </main>

      <aside className="context-rail" aria-label="健康档案与资料说明">
        <section id="profile" className="context-card profile-card">
          <div className="card-title">
            <div>
              <span className="eyebrow">PERSONAL CONTEXT</span>
              <h2>我的健康档案</h2>
            </div>
            <button type="button" aria-label="编辑健康档案">编辑</button>
          </div>
          <div className="profile-list">
            {profileItems.map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          <p>档案仅用于个性化建议，不会改变资料中的原始事实。</p>
        </section>

        <section id="sources" className="context-card sources-card">
          <div className="card-title">
            <div>
              <span className="eyebrow">SOURCE BOUNDARY</span>
              <h2>资料边界</h2>
            </div>
          </div>
          <ul>
            <li><b className="source-a">A</b><span><strong>健康膳食指南</strong>用于营养事实与禁忌依据</span></li>
            <li><b className="source-b">B</b><span><strong>个性化饮食方案</strong>用于食谱、搭配与替换依据</span></li>
            <li><b className="source-c">C</b><span><strong>平台服务白皮书</strong>仅用于平台功能与规则解释</span></li>
          </ul>
        </section>

        <section className="context-card trust-card">
          <span aria-hidden="true">✓</span>
          <div>
            <strong>可追溯回答</strong>
            <p>每条正式回答均需通过安全分级，并带页码与分段引用。</p>
          </div>
        </section>
      </aside>
    </div>
  );
}
