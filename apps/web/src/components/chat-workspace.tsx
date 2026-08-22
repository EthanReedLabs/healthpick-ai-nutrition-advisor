"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent as ReactKeyboardEvent, ReactNode } from "react";

import {
  ApiClientError,
  assessProfile,
  cancelChat,
  createAnonymousSession,
  createConversation,
  deleteAccount,
  deleteConversation,
  evaluateRecommendation,
  exportAccountData,
  fetchConversation,
  fetchEvaluationSummary,
  fetchHealth,
  fetchTransparency,
  loginAccount,
  listConversations,
  logoutAccount,
  renameConversation,
  registerAccount,
  sendChat,
  setAuthToken,
  type AuthResponse,
  type ChatFinalEvent,
  type Citation,
  type ConversationSummary,
  type ConversationTurn,
  type EvaluationSummaryResponse,
  type HealthResponse,
  type ProfileAssessment,
  type ProfilePatch,
  type RecommendationEvaluation,
  type TransparencyResponse,
} from "@/lib/api";

const starterQuestions = [
  "低钠饮食应该怎样搭配一日三餐？",
  "帮我设计一份高蛋白早餐",
  "平台能否替代医生给出诊断？",
];

type Option = { value: string; label: string };
type WorkspaceError = {
  code: string;
  message: string;
  request_id: string;
  retryable: boolean;
};
type SessionActivity = "restoring" | "creating" | "loading" | "renaming" | "deleting" | null;
type RecoveryAction =
  | { kind: "bootstrap" }
  | { kind: "create" }
  | { kind: "load"; conversationId: string }
  | { kind: "rename"; conversationId: string; title: string }
  | { kind: "delete"; conversationId: string }
  | null;

const sessionActivityCopy: Record<Exclude<SessionActivity, null>, [string, string]> = {
  restoring: ["正在恢复你的对话", "正在读取匿名会话和最近历史，请稍候。"],
  creating: ["正在创建新对话", "服务端正在分配新的对话标识。"],
  loading: ["正在加载历史对话", "已保存的消息和引用正在恢复。"],
  renaming: ["正在重命名对话", "新标题正在保存到服务端历史。"],
  deleting: ["正在删除对话", "删除完成后会自动选择下一条可用对话。"],
};

const maxMessageLength = 2_000;

function errorPresentation(error: WorkspaceError, isSessionError: boolean) {
  const evidenceFailure = ["insufficient_evidence", "evidence_validation_failed"].includes(
    error.code,
  );
  if (evidenceFailure) {
    return {
      evidenceFailure: true,
      title: "证据不足，已停止生成",
      guidance: "未通过证据门禁的内容不会展示；请换一种问法或缩小问题范围。",
    };
  }
  if (isSessionError) {
    return {
      evidenceFailure: false,
      title: "对话暂时未就绪",
      guidance: "已保留当前输入；可使用下方操作恢复，不需要前往其他面板。",
    };
  }
  if (["provider_timeout", "client_timeout"].includes(error.code)) {
    return {
      evidenceFailure: false,
      title: "回答等待超时",
      guidance: "本次没有保存半成品；可使用同一请求编号安全重试。",
    };
  }
  return {
    evidenceFailure: false,
    title: "回答服务尚未就绪",
    guidance: "当前界面不会用预置文本冒充模型结果。",
  };
}

const goalOptions = [
  { value: "fat_loss", label: "减脂" },
  { value: "muscle_gain", label: "增肌" },
  { value: "stable_glucose", label: "稳糖" },
] as const;

const ageOptions = [
  { value: "under_18", label: "未满 18 岁" },
  { value: "adult_18_44", label: "18–44 岁" },
  { value: "adult_45_64", label: "45–64 岁" },
  { value: "older_65_plus", label: "65 岁及以上" },
] as const;

const sexOptions = [
  { value: "female", label: "女性" },
  { value: "male", label: "男性" },
  { value: "prefer_not_to_say", label: "不愿说明" },
] as const;

const activityOptions = [
  { value: "sedentary", label: "久坐" },
  { value: "light", label: "轻度活动" },
  { value: "moderate", label: "中度活动" },
  { value: "high", label: "高活动量" },
] as const;

const preferenceOptions = [
  { value: "vegetarian", label: "蛋奶素" },
  { value: "vegan", label: "纯素" },
  { value: "low_sodium", label: "低钠" },
  { value: "gluten_free", label: "无麸质" },
  { value: "lactose_free", label: "无乳糖" },
] as const;

const allergyOptions = [
  { value: "eggs", label: "蛋类" },
  { value: "milk", label: "乳制品" },
  { value: "peanuts", label: "花生" },
  { value: "tree_nuts", label: "坚果" },
  { value: "wheat", label: "小麦" },
  { value: "soy", label: "大豆" },
  { value: "fish", label: "鱼类" },
  { value: "shellfish", label: "甲壳类海鲜" },
  { value: "sesame", label: "芝麻" },
] as const;

const conditionOptions = [
  { value: "diabetes", label: "糖尿病" },
  { value: "kidney_disease", label: "肾病" },
  { value: "gout", label: "痛风/高尿酸" },
  { value: "hypertension", label: "高血压" },
  { value: "cardiovascular_disease", label: "心血管疾病" },
  { value: "pregnancy", label: "孕期" },
  { value: "breastfeeding", label: "哺乳期" },
  { value: "celiac_disease", label: "乳糜泻" },
  { value: "lactose_intolerance", label: "乳糖不耐" },
  { value: "eating_disorder_history", label: "进食障碍史" },
] as const;

const blockedFoodLabels: Record<string, string> = {
  animal_product: "动物性食材",
  dairy: "乳制品",
  egg: "蛋类",
  fish: "鱼类",
  gluten: "麸质",
  high_purine: "高嘌呤食物",
  high_sodium: "高钠食物",
  meat: "肉类",
  peanut: "花生",
  sesame: "芝麻",
  shellfish: "甲壳类海鲜",
  soy: "大豆",
  tree_nut: "坚果",
  wheat: "小麦",
};

const safetyRuleLabels: Record<string, string> = {
  emergency_chest_pain: "胸痛等紧急表现",
  emergency_breathing: "呼吸困难等紧急表现",
  emergency_syncope: "晕厥或意识异常",
  emergency_severe_allergy: "严重过敏表现",
  emergency_severe_hypoglycemia: "严重低血糖表现",
  medication_adjustment_forbidden: "涉及药物调整",
  extreme_weight_control_forbidden: "涉及极端体重控制",
  precise_prescription_request: "涉及精确个体化处方",
  message_allergy_or_intolerance: "提问包含过敏或不耐受",
  message_gout: "提问包含痛风或高尿酸",
  message_hypertension: "提问包含高血压",
  message_gluten_restriction: "提问包含麸质限制",
  standard_nutrition_scope: "普通营养信息范围",
};

const emptyProfile: ProfilePatch = {
  dietary_preferences: [],
  allergies: [],
  disliked_foods: [],
  conditions: [],
};

const anonymousSessionStorageKey = "healthpick.anonymous-session-id";
const authTokenStorageKey = "healthpick.auth-token";
const authEmailStorageKey = "healthpick.auth-email";

function optionLabel(options: readonly Option[], value: string | null | undefined) {
  return options.find((option) => option.value === value)?.label ?? "未设置";
}

function listLabels(options: readonly Option[], values: readonly string[] | undefined) {
  if (!values?.length) return "未设置";
  return values.map((value) => optionLabel(options, value)).join("、");
}

function hasProfileData(profile: ProfilePatch) {
  return Object.values(profile).some((value) =>
    Array.isArray(value) ? value.length > 0 : value !== null && value !== undefined,
  );
}

function TagChecklist({
  legend,
  options,
  selected,
  onToggle,
}: {
  legend: string;
  options: readonly Option[];
  selected: readonly string[];
  onToggle: (value: string, checked: boolean) => void;
}) {
  return (
    <fieldset className="tag-fieldset">
      <legend>{legend}</legend>
      <div className="tag-options">
        {options.map((option) => (
          <label key={option.value}>
            <input
              type="checkbox"
              checked={selected.includes(option.value)}
              onChange={(event) => onToggle(option.value, event.target.checked)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function Mark({ children }: { children: ReactNode }) {
  return <span className="brand-mark">{children}</span>;
}

function percent(value: number) {
  const percentage = value * 100;
  return `${Number.isInteger(percentage) ? percentage.toFixed(0) : percentage.toFixed(1)}%`;
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

function safetyRuleLabel(rule: string) {
  if (safetyRuleLabels[rule]) return safetyRuleLabels[rule];
  if (rule.startsWith("profile_allergy_")) return "健康档案包含食物过敏";
  if (rule.startsWith("profile_")) return "健康档案包含医疗安全标签";
  if (rule.startsWith("message_")) return "提问包含需谨慎处理的健康情况";
  return "安全规则已触发";
}

function SafetyPanel({ safety }: { safety: ChatFinalEvent["safety"] }) {
  const isEmergency = safety.response_mode === "emergency_stop";
  const isRefusal = safety.response_mode === "refuse";
  const content = isEmergency
    ? {
        icon: "!",
        title: "紧急安全中止",
        description: "普通营养问答已经停止，以免延误可能需要紧急处理的情况。",
        next: "请立即联系当地急救电话或尽快前往急诊；不要等待本系统继续生成建议。",
      }
    : isRefusal
      ? {
          icon: "×",
          title: "已拒绝高风险请求",
          description: "系统不会提供药物调整、极端减重或高风险个体化处方。",
          next: "请联系医生、药师或注册营养专业人员评估；可继续询问一般饮食信息。",
        }
      : safety.risk_level === "S2"
        ? {
            icon: "△",
            title: "仅提供一般性信息",
            description: "当前情况需要专业判断，系统已关闭个体化目标和精确处方。",
            next: "请让医生或注册营养专业人员结合病史、检查结果和用药情况评估。",
          }
        : safety.risk_level === "S1"
          ? {
              icon: "✓",
              title: "约束过滤已启用",
              description: "相关禁忌已在回答生成前用于过滤，不会作为可选食材推荐。",
              next: "仍请核对配料表和交叉接触风险；严重过敏应遵循医生提供的应急方案。",
            }
          : {
              icon: "✓",
              title: "一般营养信息",
              description: "本轮未触发个体化医疗风险规则，回答仍受资料来源和引用门禁约束。",
              next: "如问题涉及疾病、药物或紧急症状，请补充说明并优先咨询专业人员。",
            };
  const reasonLabels = [...new Set((safety.matched_rules ?? []).map(safetyRuleLabel))];

  return (
    <section
      className={`safety-panel risk-${safety.risk_level.toLowerCase()}`}
      aria-label={`安全分级：${safety.risk_level}，${content.title}`}
      role={isEmergency || isRefusal ? "alert" : "status"}
    >
      <div className="safety-panel-head">
        <span className="safety-icon" aria-hidden="true">{content.icon}</span>
        <div>
          <span>{safety.risk_level} 安全分级</span>
          <h3>{content.title}</h3>
        </div>
      </div>
      <p>{content.description}</p>
      {reasonLabels.length > 0 && safety.risk_level !== "S0" && (
        <div className="safety-detail">
          <strong>触发原因</strong>
          <ul>
            {reasonLabels.map((label) => <li key={label}>{label}</li>)}
          </ul>
        </div>
      )}
      {safety.blocked_food_tags && safety.blocked_food_tags.length > 0 && (
        <div className="safety-detail">
          <strong>已排除</strong>
          <div className="blocked-tags">
            {safety.blocked_food_tags.map((tag) => (
              <span key={tag}>{blockedFoodLabels[tag] ?? "受限食材"}</span>
            ))}
          </div>
        </div>
      )}
      <div className="safety-next">
        <strong>下一步</strong>
        <p>{content.next}</p>
      </div>
    </section>
  );
}

function RecommendationCard({ evaluation }: { evaluation: RecommendationEvaluation }) {
  if (evaluation.status === "blocked" || !evaluation.primary) {
    const reviewBlocked = evaluation.requires_second_person_review;
    return (
      <section className="recommendation-card is-blocked" aria-label="结构化方案暂未放行">
        <div className="recommendation-head">
          <div>
            <span className="eyebrow">DETERMINISTIC PLAN</span>
            <h2>结构化方案暂未放行</h2>
          </div>
          <span className="plan-state">已安全拦截</span>
        </div>
        <p>
          {reviewBlocked
            ? "候选事实尚未完成第二人复核，规则引擎没有把它们放入推荐池。"
            : "当前档案缺少必要信息，或触发了只允许一般性信息的安全边界。"}
        </p>
        <small>
          {reviewBlocked
            ? `待复核规则 ${evaluation.blocked_rule_ids?.length ?? 0} 条；完成复核前不展示占位方案。`
            : "请检查年龄段、健康目标和医疗安全标签；疾病或过敏情况请咨询专业人员。"}
        </small>
      </section>
    );
  }

  const plan = evaluation.primary;
  return (
    <section className="recommendation-card" aria-label={`结构化主方案：${plan.title}`}>
      <div className="recommendation-head">
        <div>
          <span className="eyebrow">DETERMINISTIC PLAN</span>
          <h2>{plan.title}</h2>
        </div>
        <span className="plan-state">规则匹配 {plan.selection_score} 分</span>
      </div>
      <div className="match-reasons">
        {plan.match_reasons.map((reason) => <span key={reason}>{reason}</span>)}
      </div>
      <div className="plan-grid">
        <div>
          <h3>关键目标</h3>
          <ul>{plan.key_targets.map((target) => <li key={target}>{target}</li>)}</ul>
        </div>
        <div>
          <h3>三步行动</h3>
          <ol>{plan.actions.map((action) => <li key={action}>{action}</li>)}</ol>
        </div>
      </div>
      {plan.substitutions && plan.substitutions.length > 0 && (
        <div className="plan-substitutions">
          <h3>同类替换</h3>
          <div>{plan.substitutions.map((item) => <span key={item}>{item}</span>)}</div>
        </div>
      )}
      <div className="plan-evidence">
        <strong>已复核依据</strong>
        {plan.evidence.map((item) => (
          <span key={item.rule_id}>资料 {item.source} · 第 {item.pages.join("/")} 页</span>
        ))}
      </div>
    </section>
  );
}

function AnswerResult({ answer }: { answer: ChatFinalEvent }) {
  const trace = answer.retrieval_trace;
  return (
    <div>
      <div className="answer-meta">
        <strong>HealthPick 助手</strong>
        <span>{answer.safety.risk_level} 安全分级</span>
        <span>{answer.model.provider} · {answer.model.name} · {answer.model.mode}</span>
      </div>
      <SafetyPanel safety={answer.safety} />
      <p>{answer.answer}</p>
      {answer.citations.length > 0 ? (
        <div className="inline-citations">
          {answer.citations.map((citation) => (
            <CitationCard key={citation.chunk_id} citation={citation} />
          ))}
        </div>
      ) : answer.model.provider === "healthpick_guard" ? (
        <p className="guard-note">确定性安全规则直接返回，本轮未调用生成模型或资料检索。</p>
      ) : (
        <p className="guard-note">本轮没有可展示的资料引用，请勿将内容视为有证据支持的个体化建议。</p>
      )}
      {trace && (
        <details className="retrieval-trace">
          <summary>检索 trace · 证据门禁通过</summary>
          <div className="trace-metrics">
            <span>公开路由 <strong>{trace.route}</strong></span>
            <span>检索模式 <strong>{trace.mode}</strong></span>
            <span>允许来源 <strong>{trace.allowed_sources.join(" / ")}</strong></span>
            <span>候选 <strong>{trace.eligible_chunks}</strong></span>
            <span>返回 <strong>{trace.returned_chunks}</strong></span>
            <span>来源隔离拒绝 <strong>{trace.rejected_by_source_boundary}</strong></span>
          </div>
          <p>查询词：{trace.query_terms.join("、") || "无"}</p>
          <ol>
            {trace.selections.map((selection) => (
              <li key={selection.chunk_id}>
                <code>{selection.chunk_id}</code>
                <span>资料 {selection.source} · 分数 {selection.score.toFixed(3)}</span>
                <small>命中词：{(selection.matched_terms ?? []).join("、") || "语义匹配"}</small>
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function ConversationTurnCard({ turn }: { turn: ConversationTurn }) {
  return (
    <article className="conversation-turn" data-turn-id={turn.turn_id}>
      <div className="user-message">
        <strong>你</strong>
        <p>{turn.user_message}</p>
      </div>
      <div className="assistant-turn">
        <Mark>H</Mark>
        {turn.response ? (
          <AnswerResult answer={turn.response} />
        ) : (
          <div>
            <strong>HealthPick 助手</strong>
            <p>{turn.assistant_message}</p>
          </div>
        )}
      </div>
    </article>
  );
}

type ConversationHistoryListProps = {
  idPrefix: "desktop" | "mobile";
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  pending: boolean;
  emptyLabel?: string;
  deleteCandidateId: string | null;
  renameCandidateId: string | null;
  renameDraft: string;
  onSelect: (conversationId: string) => void;
  onRequestRename: (item: ConversationSummary) => void;
  onRenameDraftChange: (value: string) => void;
  onCancelRename: () => void;
  onConfirmRename: (conversationId: string) => void;
  onRequestDelete: (conversationId: string) => void;
  onCancelDelete: () => void;
  onConfirmDelete: (conversationId: string) => void;
};

function ConversationHistoryList({
  idPrefix,
  conversations,
  activeConversationId,
  pending,
  emptyLabel,
  deleteCandidateId,
  renameCandidateId,
  renameDraft,
  onSelect,
  onRequestRename,
  onRenameDraftChange,
  onCancelRename,
  onConfirmRename,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
}: ConversationHistoryListProps) {
  if (!conversations.length) {
    return (
      <p className="history-empty" role="status">
        {pending ? "正在恢复对话…" : emptyLabel ?? "还没有历史对话"}
      </p>
    );
  }

  return (
    <div className="conversation-list" aria-busy={pending}>
      {conversations.map((item) => {
        const isActive = item.conversation_id === activeConversationId;
        const confirmingDelete = item.conversation_id === deleteCandidateId;
        const renaming = item.conversation_id === renameCandidateId;
        return (
          <div className={`conversation-row ${isActive ? "active" : ""}`} key={item.conversation_id}>
            {renaming ? (
              <form
                className="conversation-rename"
                aria-label={`重命名 ${item.title}`}
                onSubmit={(event) => {
                  event.preventDefault();
                  onConfirmRename(item.conversation_id);
                }}
              >
                <input
                  id={`${idPrefix}-conversation-rename-${item.conversation_id}`}
                  autoFocus
                  aria-label={`重命名 ${item.title}`}
                  value={renameDraft}
                  maxLength={80}
                  onChange={(event) => onRenameDraftChange(event.target.value)}
                />
                <button type="submit" disabled={pending || !renameDraft.trim()}>保存</button>
                <button type="button" disabled={pending} onClick={onCancelRename}>取消</button>
              </form>
            ) : (
              <button
                className="conversation-select"
                type="button"
                disabled={pending}
                onClick={() => onSelect(item.conversation_id)}
                aria-current={isActive ? "page" : undefined}
                aria-label={`${item.title}，${item.turn_count} 轮${isActive ? "，当前对话" : ""}`}
              >
                <strong id={`${idPrefix}-conversation-title-${item.conversation_id}`}>
                  {item.title}
                </strong>
                <small>{item.turn_count} 轮</small>
              </button>
            )}
            {!renaming && confirmingDelete ? (
              <div className="conversation-confirm" role="group" aria-label={`确认删除 ${item.title}`}>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => onConfirmDelete(item.conversation_id)}
                >
                  确认
                </button>
                <button type="button" disabled={pending} onClick={onCancelDelete}>
                  取消
                </button>
              </div>
            ) : !renaming ? (
              <div className="conversation-actions">
                <button
                  className="conversation-rename-action"
                  type="button"
                  disabled={pending}
                  aria-label="重命名这条对话"
                  aria-describedby={`${idPrefix}-conversation-title-${item.conversation_id}`}
                  onClick={() => onRequestRename(item)}
                >
                  改名
                </button>
                <button
                  className="conversation-delete"
                  type="button"
                  disabled={pending}
                  aria-label="删除这条对话"
                  aria-describedby={`${idPrefix}-conversation-title-${item.conversation_id}`}
                  onClick={() => onRequestDelete(item.conversation_id)}
                >
                  删除
                </button>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function ConversationHistorySearch({
  idPrefix,
  value,
  resultCount,
  onChange,
  onClear,
}: {
  idPrefix: "desktop" | "mobile";
  value: string;
  resultCount: number;
  onChange: (value: string) => void;
  onClear: () => void;
}) {
  const mobile = idPrefix === "mobile";
  return (
    <div className="history-search">
      <label className="sr-only" htmlFor={`${idPrefix}-history-search`}>
        {mobile ? "搜索最近对话（移动端）" : "搜索最近对话"}
      </label>
      <input
        id={`${idPrefix}-history-search`}
        type="search"
        value={value}
        placeholder="按标题搜索"
        aria-label={mobile ? "搜索最近对话（移动端）" : "搜索最近对话"}
        onChange={(event) => onChange(event.target.value)}
      />
      {value && (
        <button
          type="button"
          aria-label={mobile ? "清除历史搜索（移动端）" : "清除历史搜索"}
          onClick={onClear}
        >
          清除
        </button>
      )}
      <small aria-live="polite">{value.trim() ? `${resultCount} 条匹配` : ""}</small>
    </div>
  );
}

export default function ChatWorkspace() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [transparency, setTransparency] = useState<TransparencyResponse | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationSummaryResponse | null>(null);
  const [message, setMessage] = useState("");
  const [composerError, setComposerError] = useState("");
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [error, setError] = useState<WorkspaceError | null>(null);
  const [pending, setPending] = useState(false);
  const [sessionPending, setSessionPending] = useState(true);
  const [sessionActivity, setSessionActivity] = useState<SessionActivity>("restoring");
  const [recoveryAction, setRecoveryAction] = useState<RecoveryAction>(null);
  const [bootstrapAttempt, setBootstrapAttempt] = useState(0);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historySearch, setHistorySearch] = useState("");
  const [deleteCandidateId, setDeleteCandidateId] = useState<string | null>(null);
  const [renameCandidateId, setRenameCandidateId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [profile, setProfile] = useState<ProfilePatch>(emptyProfile);
  const [profileDraft, setProfileDraft] = useState<ProfilePatch>(emptyProfile);
  const [profileAssessment, setProfileAssessment] = useState<ProfileAssessment | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profilePending, setProfilePending] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [dislikedFoodsText, setDislikedFoodsText] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const bootstrapRef = useRef<Promise<void> | null>(null);
  const messageInputRef = useRef<HTMLTextAreaElement | null>(null);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const activeChatRef = useRef<{ requestId: string; controller: AbortController } | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationEvaluation | null>(null);
  const [recommendationError, setRecommendationError] = useState("");
  const [accountEmail, setAccountEmail] = useState<string | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"register" | "login">("register");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authPending, setAuthPending] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authNotice, setAuthNotice] = useState("");
  const [accountDeleteOpen, setAccountDeleteOpen] = useState(false);
  const [accountDeletePassword, setAccountDeletePassword] = useState("");
  const [cancellationNotice, setCancellationNotice] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then(setHealth)
      .catch(() => setHealth(null));
    fetchTransparency(controller.signal)
      .then(setTransparency)
      .catch(() => setTransparency(null));
    fetchEvaluationSummary(controller.signal)
      .then(setEvaluation)
      .catch(() => setEvaluation(null));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    let active = true;
    const bootstrap = async () => {
      setSessionPending(true);
      setSessionActivity("restoring");
      setRecoveryAction(null);
      setError(null);
      setTurns([]);
      try {
        const storedAuthToken = globalThis.localStorage?.getItem(authTokenStorageKey) ?? null;
        setAuthToken(storedAuthToken);
        setAccountEmail(globalThis.localStorage?.getItem(authEmailStorageKey) ?? null);
        let activeSessionId = globalThis.localStorage?.getItem(anonymousSessionStorageKey);
        let items: ConversationSummary[] = [];
        if (activeSessionId) {
          try {
            items = (await listConversations(activeSessionId)).items;
          } catch (caught) {
            if (
              !(caught instanceof ApiClientError) ||
              ![401, 403, 404].includes(caught.status)
            ) {
              throw caught;
            }
            setAuthToken(null);
            setAccountEmail(null);
            globalThis.localStorage?.removeItem(authTokenStorageKey);
            globalThis.localStorage?.removeItem(authEmailStorageKey);
            globalThis.localStorage?.removeItem(anonymousSessionStorageKey);
            activeSessionId = null;
          }
        }
        if (!activeSessionId) {
          const session = await createAnonymousSession();
          activeSessionId = session.session_id;
          globalThis.localStorage?.setItem(anonymousSessionStorageKey, activeSessionId);
        }
        const selected = items[0] ?? await createConversation(activeSessionId);
        if (!items.length) items = [selected];
        const detail = await fetchConversation(activeSessionId, selected.conversation_id);
        if (!active) return;
        sessionIdRef.current = activeSessionId;
        conversationIdRef.current = selected.conversation_id;
        setSessionId(activeSessionId);
        setConversationId(selected.conversation_id);
        setConversations(items);
        setTurns(detail.turns);
        setRecoveryAction(null);
      } catch (caught) {
        if (!active) return;
        setRecoveryAction({ kind: "bootstrap" });
        setError(
          caught instanceof ApiClientError
            ? caught.payload
            : {
                code: "session_initialization_failed",
                message: "匿名会话初始化失败，请稍后重试。",
                request_id: "client-bootstrap",
                retryable: true,
              },
        );
      } finally {
        if (active) {
          setSessionPending(false);
          setSessionActivity(null);
        }
      }
    };
    bootstrapRef.current = bootstrap();
    return () => {
      active = false;
    };
  }, [bootstrapAttempt]);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [turns, pending, error]);

  useEffect(() => {
    if (!historyOpen && !profileOpen && !authOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (authOpen) setAuthOpen(false);
      else if (profileOpen) setProfileOpen(false);
      else setHistoryOpen(false);
    };
    globalThis.document.addEventListener("keydown", closeOnEscape);
    return () => globalThis.document.removeEventListener("keydown", closeOnEscape);
  }, [authOpen, historyOpen, profileOpen]);

  async function activeConversation() {
    await bootstrapRef.current;
    if (!sessionIdRef.current || !conversationIdRef.current) {
      throw new Error("conversation is not ready");
    }
    return {
      sessionId: sessionIdRef.current,
      conversationId: conversationIdRef.current,
    };
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitMessage();
  }

  async function submitMessage(retryRequestId?: string) {
    const trimmed = message.trim();
    if (pending) return;
    if (!trimmed) {
      setComposerError("请输入您的问题。");
      messageInputRef.current?.focus();
      return;
    }
    if (message.length > maxMessageLength) {
      setComposerError("输入内容过长，请精简后重试（最多 2000 字）。");
      messageInputRef.current?.focus();
      return;
    }

    const requestId = retryRequestId ?? globalThis.crypto.randomUUID();
    const controller = new AbortController();
    activeChatRef.current = { requestId, controller };
    setPending(true);
    setComposerError("");
    setError(null);
    setCancellationNotice("");
    setRecoveryAction(null);
    try {
      const active = await activeConversation();
      const result = await sendChat(
        {
          session_id: active.sessionId,
          conversation_id: active.conversationId,
          message: trimmed,
          profile_patch: hasProfileData(profile) ? profile : undefined,
        },
        { requestId, signal: controller.signal },
      );
      setTurns((current) => [
        ...current,
        {
          turn_id: result.turn_id ?? result.request_id,
          request_id: result.request_id,
          user_message: trimmed,
          assistant_message: result.answer,
          route: result.route,
          created_at: new Date().toISOString(),
          response: result,
        },
      ]);
      setMessage("");
      setComposerError("");
      try {
        const latest = await listConversations(active.sessionId);
        setConversations(latest.items);
      } catch {
        // The committed turn remains visible even if the sidebar refresh fails.
      }
    } catch (caught) {
      setRecoveryAction(null);
      if (caught instanceof ApiClientError && caught.payload.code === "request_cancelled") {
        setError(null);
        globalThis.setTimeout(() => messageInputRef.current?.focus(), 0);
        return;
      }
      setError(
        caught instanceof ApiClientError
          ? caught.payload
          : {
              code: "connection_failed",
              message: "暂时无法连接服务，请确认 API 已启动。",
              request_id: requestId,
              retryable: true,
            },
      );
    } finally {
      if (activeChatRef.current?.requestId === requestId) activeChatRef.current = null;
      setPending(false);
    }
  }

  async function stopGeneration() {
    const active = activeChatRef.current;
    if (!active) return;
    active.controller.abort();
    setCancellationNotice("正在停止本次生成并确认服务端状态…");
    try {
      await cancelChat(active.requestId);
      setCancellationNotice("已停止本次生成；服务端已取消，半成品不会保存。输入内容已保留。");
    } catch {
      setCancellationNotice("页面已停止接收；服务端取消状态未确认，请稍后刷新历史核对。");
    }
  }

  async function startNewConversation() {
    if (sessionPending || pending) return;
    setSessionPending(true);
    setSessionActivity("creating");
    setRecoveryAction(null);
    setError(null);
    setCancellationNotice("");
    setMessage("");
    conversationIdRef.current = null;
    setConversationId(null);
    setTurns([]);
    const previousBootstrap = bootstrapRef.current;
    const creation = async () => {
      try {
        await previousBootstrap;
        const activeSessionId = sessionIdRef.current;
        if (!activeSessionId) throw new Error("session is not ready");
        const created = await createConversation(activeSessionId);
        sessionIdRef.current = activeSessionId;
        conversationIdRef.current = created.conversation_id;
        setSessionId(activeSessionId);
        setConversationId(created.conversation_id);
        setConversations((current) => [created, ...current]);
        setTurns([]);
        setDeleteCandidateId(null);
        setHistoryOpen(false);
        messageInputRef.current?.focus();
      } catch (caught) {
        setRecoveryAction({ kind: "create" });
        setError(
          caught instanceof ApiClientError
            ? caught.payload
            : {
                code: "conversation_create_failed",
                message: "新对话创建失败，请稍后重试。",
                request_id: "client-create-conversation",
                retryable: true,
              },
        );
      } finally {
        setSessionPending(false);
        setSessionActivity(null);
      }
    };
    bootstrapRef.current = creation();
    await bootstrapRef.current;
  }

  async function selectConversation(selectedId: string) {
    if (!sessionId || selectedId === conversationId || sessionPending || pending) return;
    setSessionPending(true);
    setSessionActivity("loading");
    setRecoveryAction(null);
    setError(null);
    setTurns([]);
    try {
      const detail = await fetchConversation(sessionId, selectedId);
      conversationIdRef.current = selectedId;
      setConversationId(selectedId);
      setTurns(detail.turns);
      setHistoryOpen(false);
      setDeleteCandidateId(null);
      setRenameCandidateId(null);
      messageInputRef.current?.focus();
    } catch (caught) {
      setRecoveryAction({ kind: "load", conversationId: selectedId });
      setError(
        caught instanceof ApiClientError
          ? caught.payload
          : {
              code: "conversation_load_failed",
              message: "历史对话加载失败，请稍后重试。",
              request_id: "client-load-conversation",
              retryable: true,
            },
      );
    } finally {
      setSessionPending(false);
      setSessionActivity(null);
    }
  }

  function requestRenameConversation(item: ConversationSummary) {
    setDeleteCandidateId(null);
    setRenameCandidateId(item.conversation_id);
    setRenameDraft(item.title);
  }

  async function confirmRenameConversation(selectedId: string, requestedTitle = renameDraft) {
    const title = requestedTitle.trim();
    if (!sessionId || !title || sessionPending || pending) return;
    setSessionPending(true);
    setSessionActivity("renaming");
    setRecoveryAction(null);
    setError(null);
    try {
      const updated = await renameConversation(sessionId, selectedId, title);
      setConversations((current) =>
        current.map((item) => item.conversation_id === selectedId ? updated : item)
      );
      setRenameCandidateId(null);
      setRenameDraft("");
    } catch (caught) {
      setRecoveryAction({ kind: "rename", conversationId: selectedId, title });
      setError(
        caught instanceof ApiClientError
          ? caught.payload
          : {
              code: "conversation_rename_failed",
              message: "对话重命名失败，请稍后重试。",
              request_id: "client-rename-conversation",
              retryable: true,
            },
      );
    } finally {
      setSessionPending(false);
      setSessionActivity(null);
    }
  }

  async function confirmDeleteConversation(selectedId: string) {
    if (!sessionId || sessionPending || pending) return;
    setSessionPending(true);
    setSessionActivity("deleting");
    setRecoveryAction(null);
    setError(null);
    let deleted = false;
    try {
      await deleteConversation(sessionId, selectedId);
      deleted = true;
      const remaining = conversations.filter((item) => item.conversation_id !== selectedId);
      setConversations(remaining);
      setDeleteCandidateId(null);
      setRenameCandidateId(null);
      if (selectedId !== conversationId) return;

      setTurns([]);
      const next = remaining[0] ?? await createConversation(sessionId);
      if (!remaining.length) setConversations([next]);
      const detail = await fetchConversation(sessionId, next.conversation_id);
      conversationIdRef.current = next.conversation_id;
      setConversationId(next.conversation_id);
      setTurns(detail.turns);
      setHistoryOpen(false);
      messageInputRef.current?.focus();
    } catch (caught) {
      setRecoveryAction(
        deleted ? { kind: "bootstrap" } : { kind: "delete", conversationId: selectedId },
      );
      setError(
        caught instanceof ApiClientError
          ? caught.payload
          : {
              code: deleted ? "conversation_recovery_failed" : "conversation_delete_failed",
              message: deleted
                ? "对话已删除，但下一条对话恢复失败。"
                : "对话删除失败，请稍后重试。",
              request_id: "client-delete-conversation",
              retryable: true,
            },
      );
    } finally {
      setSessionPending(false);
      setSessionActivity(null);
    }
  }

  async function retrySessionAction() {
    const action = recoveryAction;
    if (!action) return;
    setError(null);
    if (action.kind === "bootstrap") {
      setBootstrapAttempt((current) => current + 1);
      return;
    }
    if (action.kind === "create") {
      await startNewConversation();
      return;
    }
    if (action.kind === "load") {
      await selectConversation(action.conversationId);
      return;
    }
    if (action.kind === "rename") {
      await confirmRenameConversation(action.conversationId, action.title);
      return;
    }
    await confirmDeleteConversation(action.conversationId);
  }

  function handleComposerKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key !== "Enter"
      || event.shiftKey
      || event.nativeEvent.isComposing
      || pending
    ) {
      return;
    }
    event.preventDefault();
    void submitMessage();
  }

  function openAuthDialog(mode: "register" | "login" = "register") {
    setAuthMode(mode);
    setAuthEmail(accountEmail ?? "");
    setAuthPassword("");
    setAuthError("");
    setAuthNotice("");
    setAccountDeleteOpen(false);
    setAccountDeletePassword("");
    setAuthOpen(true);
  }

  async function adoptAuthenticatedSession(result: AuthResponse) {
    setAuthToken(result.access_token);
    globalThis.localStorage?.setItem(authTokenStorageKey, result.access_token);
    globalThis.localStorage?.setItem(authEmailStorageKey, result.email);
    globalThis.localStorage?.setItem(anonymousSessionStorageKey, result.session_id);
    setAccountEmail(result.email);
    sessionIdRef.current = result.session_id;
    setSessionId(result.session_id);

    let items = (await listConversations(result.session_id)).items;
    const selected = items[0] ?? (await createConversation(result.session_id));
    if (!items.length) items = [selected];
    const detail = await fetchConversation(result.session_id, selected.conversation_id);
    conversationIdRef.current = selected.conversation_id;
    setConversationId(selected.conversation_id);
    setConversations(items);
    setTurns(detail.turns);
    setAuthOpen(false);
    setAuthPassword("");
    messageInputRef.current?.focus();
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authPending) return;
    setAuthPending(true);
    setAuthError("");
    try {
      await bootstrapRef.current;
      const result =
        authMode === "register"
          ? await registerAccount({
              email: authEmail,
              password: authPassword,
              anonymous_session_id: sessionIdRef.current ?? "",
            })
          : await loginAccount({ email: authEmail, password: authPassword });
      await adoptAuthenticatedSession(result);
    } catch (caught) {
      setAuthError(
        caught instanceof ApiClientError
          ? `${caught.payload.message}（${caught.payload.code}）`
          : "账号操作暂时无法完成，请稍后重试。",
      );
    } finally {
      setAuthPending(false);
    }
  }

  async function logout() {
    if (authPending) return;
    setAuthPending(true);
    setAuthError("");
    try {
      await logoutAccount();
      await resetToAnonymousSession();
    } catch (caught) {
      setAuthError(
        caught instanceof ApiClientError
          ? `${caught.payload.message}（${caught.payload.code}）`
          : "退出失败，请稍后重试。",
      );
    } finally {
      setAuthPending(false);
    }
  }

  async function resetToAnonymousSession() {
      setAuthToken(null);
      globalThis.localStorage?.removeItem(authTokenStorageKey);
      globalThis.localStorage?.removeItem(authEmailStorageKey);
      setAccountEmail(null);
      const anonymous = await createAnonymousSession();
      const conversation = await createConversation(anonymous.session_id);
      globalThis.localStorage?.setItem(anonymousSessionStorageKey, anonymous.session_id);
      sessionIdRef.current = anonymous.session_id;
      conversationIdRef.current = conversation.conversation_id;
      setSessionId(anonymous.session_id);
      setConversationId(conversation.conversation_id);
      setConversations([conversation]);
      setTurns([]);
      setAuthOpen(false);
  }

  async function exportMyData() {
    if (authPending) return;
    setAuthPending(true);
    setAuthError("");
    setAuthNotice("");
    try {
      const payload = await exportAccountData();
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = href;
      link.download = `healthpick-account-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(href);
      setAuthNotice(`已导出 ${payload.inventory.total_records} 条个人数据记录。`);
    } catch (caught) {
      setAuthError(
        caught instanceof ApiClientError
          ? `${caught.payload.message}（${caught.payload.code}）`
          : "导出失败，请稍后重试。",
      );
    } finally {
      setAuthPending(false);
    }
  }

  async function permanentlyDeleteAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authPending) return;
    setAuthPending(true);
    setAuthError("");
    setAuthNotice("");
    try {
      await deleteAccount(accountDeletePassword);
      await resetToAnonymousSession();
      setAccountDeletePassword("");
      setAccountDeleteOpen(false);
    } catch (caught) {
      setAuthError(
        caught instanceof ApiClientError
          ? `${caught.payload.message}（${caught.payload.code}）`
          : "删除失败，请稍后重试。",
      );
    } finally {
      setAuthPending(false);
    }
  }

  function openProfileEditor() {
    setProfileDraft(profile);
    setDislikedFoodsText(profile.disliked_foods?.join("、") ?? "");
    setProfileError("");
    setProfileOpen(true);
  }

  function toggleProfileList(
    field: "dietary_preferences" | "allergies" | "conditions",
    value: string,
    checked: boolean,
  ) {
    setProfileDraft((current) => {
      const values = (current[field] ?? []) as string[];
      const next = checked
        ? [...values, value]
        : values.filter((item) => item !== value);
      return { ...current, [field]: next } as ProfilePatch;
    });
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (profilePending) return;
    const dislikedFoods = dislikedFoodsText
      .split(/[、,，]/)
      .map((item) => item.trim())
      .filter(Boolean);
    setProfilePending(true);
    setProfileError("");
    try {
      const assessment = await assessProfile({
        ...profileDraft,
        disliked_foods: dislikedFoods,
      });
      setProfile(assessment.profile);
      setProfileDraft(assessment.profile);
      setProfileAssessment(assessment);
      setRecommendation(null);
      setRecommendationError("");
      if (assessment.profile.goal) {
        try {
          setRecommendation(await evaluateRecommendation(assessment.profile));
        } catch (caught) {
          setRecommendationError(
            caught instanceof ApiClientError
              ? `${caught.payload.message}（${caught.payload.code}）`
              : "结构化方案评估暂时不可用。",
          );
        }
      }
      setProfileOpen(false);
    } catch (caught) {
      setProfileError(
        caught instanceof ApiClientError
          ? `${caught.payload.message}（${caught.payload.code}）`
          : "档案暂时无法校验，请确认 API 已启动。",
      );
    } finally {
      setProfilePending(false);
    }
  }

  const profileItems = [
    ["目标", optionLabel(goalOptions, profile.goal)],
    ["年龄段", optionLabel(ageOptions, profile.age_band)],
    ["过敏原", listLabels(allergyOptions, profile.allergies)],
    ["安全标签", listLabels(conditionOptions, profile.conditions)],
  ];
  const activityCopy = sessionActivity ? sessionActivityCopy[sessionActivity] : null;
  const presentedError = error ? errorPresentation(error, recoveryAction !== null) : null;
  const recoveryLabel = recoveryAction
    ? {
        bootstrap: "重新恢复对话",
        create: "重新创建对话",
        load: "重新加载对话",
        rename: "重新重命名对话",
        delete: "重新删除对话",
      }[recoveryAction.kind]
    : null;
  const interactionsDisabled = sessionPending || pending;
  const normalizedHistorySearch = historySearch.trim().toLocaleLowerCase("zh-CN");
  const visibleConversations = normalizedHistorySearch
    ? conversations.filter((item) =>
        item.title.toLocaleLowerCase("zh-CN").includes(normalizedHistorySearch)
      )
    : conversations;
  const historyEmptyLabel = conversations.length && normalizedHistorySearch
    ? "没有匹配的历史对话"
    : undefined;

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

        <button
          className="new-chat"
          type="button"
          disabled={interactionsDisabled}
          onClick={startNewConversation}
        >
          <span aria-hidden="true">＋</span> 新对话
        </button>

        <section className="conversation-history" aria-label="最近对话">
          <span>最近对话</span>
          <ConversationHistorySearch
            idPrefix="desktop"
            value={historySearch}
            resultCount={visibleConversations.length}
            onChange={setHistorySearch}
            onClear={() => setHistorySearch("")}
          />
          <ConversationHistoryList
            idPrefix="desktop"
            conversations={visibleConversations}
            activeConversationId={conversationId}
            pending={sessionPending}
            emptyLabel={historyEmptyLabel}
            deleteCandidateId={deleteCandidateId}
            renameCandidateId={renameCandidateId}
            renameDraft={renameDraft}
            onSelect={(selectedId) => void selectConversation(selectedId)}
            onRequestRename={requestRenameConversation}
            onRenameDraftChange={setRenameDraft}
            onCancelRename={() => setRenameCandidateId(null)}
            onConfirmRename={(selectedId) => void confirmRenameConversation(selectedId)}
            onRequestDelete={(selectedId) => {
              setRenameCandidateId(null);
              setDeleteCandidateId(selectedId);
            }}
            onCancelDelete={() => setDeleteCandidateId(null)}
            onConfirmDelete={(selectedId) => void confirmDeleteConversation(selectedId)}
          />
        </section>

        <nav className="nav-list">
          <a className="active" href="#workspace">
            <span aria-hidden="true">◌</span> 营养问答
          </a>
          <a href="#profile">
            <span aria-hidden="true">◇</span> 健康档案
          </a>
          <a href="#transparency">
            <span aria-hidden="true">▤</span> 透明度与来源
          </a>
          <a href="#evaluation">
            <span aria-hidden="true">✓</span> 评测概览
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
          <div className="mobile-actions">
            <button
              className="profile-shortcut mobile-history"
              type="button"
              aria-label="打开最近对话（移动端）"
              aria-expanded={historyOpen}
              disabled={pending}
              onClick={() => setHistoryOpen(true)}
            >
              历史
            </button>
            <button
              className="profile-shortcut mobile-new-chat"
              type="button"
              aria-label="开始新对话（移动端）"
              disabled={interactionsDisabled}
              onClick={startNewConversation}
            >
              ＋
            </button>
            <button
              className="profile-shortcut"
              type="button"
              aria-label="打开健康档案编辑器（移动端）"
              disabled={pending}
              onClick={openProfileEditor}
            >
              档案
            </button>
            <button
              className="profile-shortcut"
              type="button"
              aria-label={accountEmail ? "打开账号信息（移动端）" : "登录或注册（移动端）"}
              onClick={() => openAuthDialog(accountEmail ? "login" : "register")}
            >
              {accountEmail ? "账号" : "登录"}
            </button>
            <ConnectionBadge health={health} />
          </div>
        </header>

        <div className="workspace-head">
          <div>
            <span className="eyebrow">EVIDENCE-GROUNDED NUTRITION</span>
            <h1>你好，今天想了解什么？</h1>
            <p>我会依据指定资料回答，并标注可核验的来源。</p>
          </div>
          <div className="desktop-status">
            <button
              className="profile-shortcut"
              type="button"
              aria-label={accountEmail ? "打开账号信息" : "登录或注册"}
              onClick={() => openAuthDialog(accountEmail ? "login" : "register")}
            >
              {accountEmail ?? "登录 / 注册"}
            </button>
            <button
              className="profile-shortcut"
              type="button"
              aria-label="打开健康档案编辑器（顶部）"
              disabled={pending}
              onClick={openProfileEditor}
            >
              健康档案
            </button>
            <ConnectionBadge health={health} />
          </div>
        </div>

        <section
          className="assistant-message"
          aria-live="polite"
          aria-busy={sessionPending || pending}
        >
          {sessionPending && activityCopy && (
            <div
              className="workspace-state is-loading"
              role="status"
              aria-label={activityCopy[0]}
            >
              <span className="state-spinner" aria-hidden="true" />
              <div>
                <strong>{activityCopy[0]}</strong>
                <p>{activityCopy[1]}</p>
              </div>
            </div>
          )}

          {!sessionPending && !turns.length && !error && (
            <div className="assistant-welcome">
              <Mark>H</Mark>
              <div>
                <strong>HealthPick 助手</strong>
                <p>
                  完善健康档案后可生成规则匹配方案；也可以直接询问日常营养搭配、健康饮食原则或平台规则。回答会区分资料 A、B、C，没有证据时会明确说明。
                </p>
                <div className="welcome-actions">
                  <button type="button" onClick={openProfileEditor}>
                    完善档案，生成规则方案
                  </button>
                  <span>或直接选择下方问题开始</span>
                </div>
              </div>
            </div>
          )}

          {turns.map((turn) => <ConversationTurnCard key={turn.turn_id} turn={turn} />)}

          {pending && (
            <div
              className="workspace-state is-generating"
              role="status"
              aria-label="正在接收并安全校验回答"
            >
              <span className="state-spinner" aria-hidden="true" />
              <div>
                <strong>正在接收并安全校验回答</strong>
                <p>请求已发送；只有完整通过证据与安全门禁的回答才会加入历史。</p>
              </div>
            </div>
          )}

          {cancellationNotice && !pending && (
            <div className="workspace-state is-cancelled" role="status">
              <span aria-hidden="true">■</span>
              <div>
                <strong>生成已停止</strong>
                <p>{cancellationNotice}</p>
              </div>
            </div>
          )}

          {error && presentedError && (
            <div
              className={`error-card ${presentedError.evidenceFailure ? "is-evidence" : ""}`}
              role="alert"
            >
              <strong>{presentedError.title}</strong>
              <p>{error.message}（{error.code}）</p>
              <small>{presentedError.guidance}</small>
              <small>请求编号：{error.request_id}</small>
              {error.retryable && recoveryAction && !sessionPending && (
                <button
                  className="retry-action"
                  type="button"
                  disabled={pending}
                  onClick={() => void retrySessionAction()}
                >
                  {recoveryLabel}
                </button>
              )}
              {error.retryable && !recoveryAction && message.trim() && !sessionPending && (
                <button
                  className="retry-action"
                  type="button"
                  disabled={pending}
                  onClick={() => void submitMessage(error.request_id)}
                >
                  使用同一请求编号重试
                </button>
              )}
            </div>
          )}
          <div ref={conversationEndRef} aria-hidden="true" />
        </section>

        {recommendation && <RecommendationCard evaluation={recommendation} />}
        {recommendationError && (
          <div className="recommendation-error" role="alert">
            <strong>结构化方案评估失败</strong>
            <p>{recommendationError}</p>
          </div>
        )}

        <section className="quick-start" aria-label="快捷提问">
          <span>试试这样问</span>
          <div>
            {starterQuestions.map((question) => (
              <button
                key={question}
                type="button"
                disabled={pending}
                onClick={() => {
                  setMessage(question);
                  setComposerError("");
                  messageInputRef.current?.focus();
                }}
              >
                {question}
              </button>
            ))}
          </div>
        </section>

        <form className={`composer ${composerError ? "has-error" : ""}`} onSubmit={submit}>
          <label htmlFor="chat-message" className="sr-only">
            输入营养或平台问题
          </label>
          <textarea
            ref={messageInputRef}
            id="chat-message"
            value={message}
            onChange={(event) => {
              const nextMessage = event.target.value;
              setMessage(nextMessage);
              setComposerError(
                nextMessage.length > maxMessageLength
                  ? "输入内容过长，请精简后重试（最多 2000 字）。"
                  : "",
              );
            }}
            onKeyDown={handleComposerKeyDown}
            placeholder="输入营养、健康饮食或平台相关问题…"
            rows={2}
            disabled={pending}
            aria-invalid={Boolean(composerError)}
            aria-describedby={composerError ? "composer-hint composer-error" : "composer-hint"}
          />
          {composerError && (
            <p className="composer-error" id="composer-error" role="alert">
              {composerError}
            </p>
          )}
          <div className="composer-foot">
            <span id="composer-hint">
              {message.length}/{maxMessageLength} · Enter 发送 · Shift+Enter 换行
            </span>
            {pending ? (
              <button
                className="stop-generation"
                type="button"
                aria-label="停止生成本次回答"
                onClick={() => void stopGeneration()}
              >
                停止生成 <span aria-hidden="true">■</span>
              </button>
            ) : (
              <button type="submit">
                发送 <span aria-hidden="true">↗</span>
              </button>
            )}
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
            <button type="button" aria-label="编辑健康档案" onClick={openProfileEditor}>
              编辑
            </button>
          </div>
          <div className="profile-list">
            {profileItems.map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          {profileAssessment?.bmi && (
            <p className="bmi-estimate">
              BMI {profileAssessment.bmi.value} · {profileAssessment.bmi.label}
              <small>{profileAssessment.bmi.formula}</small>
            </p>
          )}
          <p>
            档案仍不落库；{accountEmail ? "对话历史已由账号令牌保护" : "对话历史按本机匿名会话 ID 持久化"}，不会改变资料原文。
          </p>
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

        <section id="evaluation" className="context-card evaluation-card">
          <div className="card-title">
            <div>
              <span className="eyebrow">RELEASE EVALUATION</span>
              <h2>冻结评测概览</h2>
            </div>
            {evaluation && (
              <span className="evaluation-gate-status">
                {evaluation.gates_passed}/{evaluation.gates_total} 自动门通过
              </span>
            )}
          </div>
          {evaluation ? (
            <>
              <div className="evaluation-dataset" aria-label="评测数据集规模">
                <strong>{evaluation.case_count}</strong>
                <span>用例</span>
                <strong>{evaluation.turn_count}</strong>
                <span>轮对话</span>
              </div>
              <dl className="evaluation-metrics">
                <div>
                  <dt>路由准确率</dt>
                  <dd>{percent(evaluation.metrics.route_accuracy)}</dd>
                </div>
                <div>
                  <dt>引用支持率</dt>
                  <dd>{percent(evaluation.metrics.citation_support_rate)}</dd>
                </div>
                <div>
                  <dt>高风险召回</dt>
                  <dd>{percent(evaluation.metrics.high_risk_recall)}</dd>
                </div>
                <div>
                  <dt>多轮约束</dt>
                  <dd>{percent(evaluation.metrics.multi_turn_constraint_rate)}</dd>
                </div>
                <div>
                  <dt>来源泄漏</dt>
                  <dd>{percent(evaluation.metrics.source_leakage_rate)}</dd>
                </div>
                <div>
                  <dt>首字 P95</dt>
                  <dd>{evaluation.metrics.first_response_p95_ms} ms</dd>
                </div>
              </dl>
              <div className="evaluation-review" role="status">
                <strong>
                  整体状态：{evaluation.manual_review.status === "PASS" ? "已通过" : "待人工复核"}
                </strong>
                <span>
                  {evaluation.manual_review.action} · {evaluation.manual_review.case_count} 个事实用例
                  {evaluation.manual_review.status === "PASS" ? "完成复核" : ""}
                </span>
              </div>
              <p>{evaluation.public_note}</p>
              <small>
                冻结版本 {evaluation.dataset_version}；首轮失败记录已保留，公开摘要不含内部路径和密钥。
              </small>
            </>
          ) : (
            <p role="status">评测摘要暂未读取；不会使用演示占位分数。</p>
          )}
        </section>

        <section id="transparency" className="context-card transparency-card">
          <div className="card-title">
            <div>
              <span className="eyebrow">SYSTEM TRANSPARENCY</span>
              <h2>模型与检索透明度</h2>
            </div>
          </div>
          {transparency ? (
            <>
              <dl>
                <div>
                  <dt>生成模型</dt>
                  <dd>{transparency.model.provider} / {transparency.model.name}</dd>
                </div>
                <div>
                  <dt>模型模式</dt>
                  <dd>{transparency.model.mode}</dd>
                </div>
                <div>
                  <dt>检索模式</dt>
                  <dd>{transparency.retrieval_mode}</dd>
                </div>
                <div>
                  <dt>嵌入模型</dt>
                  <dd>
                    {transparency.embedding.name}
                    {transparency.embedding.dimensions
                      ? ` / ${transparency.embedding.dimensions} 维`
                      : ""}
                  </dd>
                </div>
                <div>
                  <dt>历史存储</dt>
                  <dd>{transparency.conversation_store}</dd>
                </div>
                <div>
                  <dt>健康档案</dt>
                  <dd>{transparency.profile_persistence}</dd>
                </div>
                <div>
                  <dt>备用模型</dt>
                  <dd>
                    {transparency.failover.enabled && transparency.failover.fallback
                      ? `${transparency.failover.fallback.provider} / ${transparency.failover.fallback.name}`
                      : "未启用"}
                  </dd>
                </div>
                <div>
                  <dt>切换策略</dt>
                  <dd>可重试故障 / 无效响应</dd>
                </div>
              </dl>
              <p>{transparency.evidence_policy}</p>
              <small>接口仅披露非秘密配置，不返回密钥、授权头或供应商地址。</small>
            </>
          ) : (
            <p role="status">透明度接口暂未读取；回答中的模型和引用仍会逐轮展示。</p>
          )}
        </section>

        <section className="context-card trust-card">
          <span aria-hidden="true">✓</span>
          <div>
            <strong>可追溯回答</strong>
            <p>每条正式回答均需通过安全分级，并带页码与分段引用。</p>
          </div>
        </section>
      </aside>

      {historyOpen && (
        <div
          className="dialog-backdrop history-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setHistoryOpen(false);
          }}
        >
          <section
            className="history-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="history-dialog-title"
          >
            <div className="dialog-head">
              <div>
                <span className="eyebrow">CONVERSATION HISTORY</span>
                <h2 id="history-dialog-title">最近对话</h2>
              </div>
              <button
                className="dialog-close"
                type="button"
                autoFocus
                aria-label="关闭最近对话"
                onClick={() => setHistoryOpen(false)}
              >
                ×
              </button>
            </div>
            <p className="history-dialog-note">选择一条历史可恢复消息和引用；删除当前对话后会自动选择下一条。</p>
            <ConversationHistorySearch
              idPrefix="mobile"
              value={historySearch}
              resultCount={visibleConversations.length}
              onChange={setHistorySearch}
              onClear={() => setHistorySearch("")}
            />
            <ConversationHistoryList
              idPrefix="mobile"
              conversations={visibleConversations}
              activeConversationId={conversationId}
              pending={sessionPending}
              emptyLabel={historyEmptyLabel}
              deleteCandidateId={deleteCandidateId}
              renameCandidateId={renameCandidateId}
              renameDraft={renameDraft}
              onSelect={(selectedId) => void selectConversation(selectedId)}
              onRequestRename={requestRenameConversation}
              onRenameDraftChange={setRenameDraft}
              onCancelRename={() => setRenameCandidateId(null)}
              onConfirmRename={(selectedId) => void confirmRenameConversation(selectedId)}
              onRequestDelete={(selectedId) => {
                setRenameCandidateId(null);
                setDeleteCandidateId(selectedId);
              }}
              onCancelDelete={() => setDeleteCandidateId(null)}
              onConfirmDelete={(selectedId) => void confirmDeleteConversation(selectedId)}
            />
          </section>
        </div>
      )}

      {profileOpen && (
        <div className="dialog-backdrop" role="presentation">
          <section
            className="profile-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="profile-dialog-title"
          >
            <div className="dialog-head">
              <div>
                <span className="eyebrow">EPHEMERAL PROFILE</span>
                <h2 id="profile-dialog-title">编辑健康档案</h2>
                <p>只填写当前建议必要的结构化信息；不收集姓名和自由文本病史。</p>
              </div>
              <button
                type="button"
                aria-label="关闭健康档案编辑器"
                onClick={() => setProfileOpen(false)}
              >
                ×
              </button>
            </div>

            <form className="profile-form" onSubmit={saveProfile}>
              <div className="profile-grid">
                <label>
                  <span>目标</span>
                  <select
                    aria-label="健康目标"
                    value={profileDraft.goal ?? ""}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        goal: (event.target.value || undefined) as ProfilePatch["goal"],
                      })
                    }
                  >
                    <option value="">暂不设置</option>
                    {goalOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>年龄段</span>
                  <select
                    aria-label="年龄段"
                    value={profileDraft.age_band ?? ""}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        age_band: (event.target.value || undefined) as ProfilePatch["age_band"],
                      })
                    }
                  >
                    <option value="">暂不设置</option>
                    {ageOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>性别</span>
                  <select
                    aria-label="性别"
                    value={profileDraft.sex ?? ""}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        sex: (event.target.value || undefined) as ProfilePatch["sex"],
                      })
                    }
                  >
                    <option value="">暂不设置</option>
                    {sexOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>活动水平</span>
                  <select
                    aria-label="活动水平"
                    value={profileDraft.activity_level ?? ""}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        activity_level: (event.target.value || undefined) as ProfilePatch["activity_level"],
                      })
                    }
                  >
                    <option value="">暂不设置</option>
                    {activityOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>身高（cm）</span>
                  <input
                    aria-label="身高（cm）"
                    type="number"
                    min="100"
                    max="230"
                    step="0.1"
                    value={profileDraft.height_cm ?? ""}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        height_cm: event.target.value ? Number(event.target.value) : undefined,
                      })
                    }
                  />
                </label>
                <label>
                  <span>体重（kg）</span>
                  <input
                    aria-label="体重（kg）"
                    type="number"
                    min="25"
                    max="300"
                    step="0.1"
                    value={profileDraft.weight_kg ?? ""}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        weight_kg: event.target.value ? Number(event.target.value) : undefined,
                      })
                    }
                  />
                </label>
              </div>

              <TagChecklist
                legend="饮食偏好"
                options={preferenceOptions}
                selected={profileDraft.dietary_preferences ?? []}
                onToggle={(value, checked) =>
                  toggleProfileList("dietary_preferences", value, checked)
                }
              />
              <TagChecklist
                legend="过敏原"
                options={allergyOptions}
                selected={profileDraft.allergies ?? []}
                onToggle={(value, checked) => toggleProfileList("allergies", value, checked)}
              />
              <TagChecklist
                legend="医疗安全标签"
                options={conditionOptions}
                selected={profileDraft.conditions ?? []}
                onToggle={(value, checked) => toggleProfileList("conditions", value, checked)}
              />

              <label className="disliked-foods-field">
                <span>不喜欢的食材</span>
                <input
                  aria-label="不喜欢的食材"
                  value={dislikedFoodsText}
                  maxLength={400}
                  placeholder="用逗号分隔，例如：香菜、苦瓜"
                  onChange={(event) => setDislikedFoodsText(event.target.value)}
                />
              </label>

              {profileError && <p className="profile-error" role="alert">{profileError}</p>}

              <div className="dialog-actions">
                <button type="button" onClick={() => setProfileOpen(false)}>取消</button>
                <button type="submit" disabled={profilePending}>
                  {profilePending ? "校验中…" : "保存档案"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {authOpen && (
        <div className="dialog-backdrop" role="presentation">
          <section
            className="auth-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="auth-dialog-title"
          >
            <div className="dialog-head">
              <div>
                <span className="eyebrow">ACCOUNT & HISTORY</span>
                <h2 id="auth-dialog-title">{accountEmail ? "账号信息" : "保存跨设备历史"}</h2>
                <p>注册会把当前匿名历史一次性绑定到账号；登录后使用服务端返回的规范会话。</p>
              </div>
              <button autoFocus={Boolean(accountEmail)} type="button" aria-label="关闭账号窗口" onClick={() => setAuthOpen(false)}>
                ×
              </button>
            </div>

            {accountEmail ? (
              <div className="account-summary">
                <span>当前账号</span>
                <strong>{accountEmail}</strong>
                <p>历史已受账号令牌保护；退出后会创建新的匿名会话，不删除账号历史。</p>
                <div className="account-data-actions" aria-label="个人数据操作">
                  <button type="button" disabled={authPending} onClick={() => void exportMyData()}>
                    {authPending ? "处理中…" : "导出我的数据"}
                  </button>
                  <button className="danger-button" type="button" disabled={authPending} onClick={() => setAccountDeleteOpen(true)}>
                    永久删除账号
                  </button>
                </div>
                {authNotice && <p className="account-notice" role="status">{authNotice}</p>}
                {authError && <p className="profile-error" role="alert">{authError}</p>}
                {accountDeleteOpen && (
                  <form className="account-danger-zone" onSubmit={permanentlyDeleteAccount}>
                    <strong>此操作不可撤销</strong>
                    <p>账号、登录会话、匿名会话、全部对话和轮次将永久删除；静态知识资料不受影响。</p>
                    <input
                      className="sr-only"
                      type="email"
                      autoComplete="username"
                      tabIndex={-1}
                      aria-hidden="true"
                      readOnly
                      value={accountEmail}
                    />
                    <label>
                      <span>再次输入密码确认删除</span>
                      <input
                        autoFocus
                        type="password"
                        autoComplete="current-password"
                        required
                        minLength={10}
                        maxLength={128}
                        value={accountDeletePassword}
                        onChange={(event) => setAccountDeletePassword(event.target.value)}
                      />
                    </label>
                    <div className="dialog-actions">
                      <button type="button" onClick={() => { setAccountDeleteOpen(false); setAccountDeletePassword(""); }}>取消删除</button>
                      <button className="danger-button" type="submit" disabled={authPending}>
                        {authPending ? "删除中…" : "确认永久删除"}
                      </button>
                    </div>
                  </form>
                )}
                <div className="dialog-actions">
                  <button type="button" onClick={() => setAuthOpen(false)}>关闭</button>
                  <button type="button" disabled={authPending} onClick={() => void logout()}>
                    {authPending ? "退出中…" : "退出登录"}
                  </button>
                </div>
              </div>
            ) : (
              <form className="auth-form" onSubmit={submitAuth}>
                <div className="auth-mode-tabs" role="tablist" aria-label="账号操作">
                  <button type="button" role="tab" aria-selected={authMode === "register"} onClick={() => setAuthMode("register")}>注册并迁移</button>
                  <button type="button" role="tab" aria-selected={authMode === "login"} onClick={() => setAuthMode("login")}>已有账号登录</button>
                </div>
                <label>
                  <span>邮箱</span>
                  <input autoFocus type="email" autoComplete="email" required maxLength={254} value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} />
                </label>
                <label>
                  <span>密码（至少 10 位）</span>
                  <input type="password" autoComplete={authMode === "register" ? "new-password" : "current-password"} required minLength={10} maxLength={128} value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} />
                </label>
                {authError && <p className="profile-error" role="alert">{authError}</p>}
                <div className="dialog-actions">
                  <button type="button" onClick={() => setAuthOpen(false)}>取消</button>
                  <button type="submit" disabled={authPending}>
                    {authPending ? "处理中…" : authMode === "register" ? "注册并迁移历史" : "登录"}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
