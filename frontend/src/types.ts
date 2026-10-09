export interface OutlineSection {
  title: string;
  bullets: string[];
}

export interface SearchSummary {
  id: number;
  query: string;
  created_at: string;
  outline_approved: boolean;
}

export interface User {
  id: number;
  email: string;
  name: string;
  picture: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface BlogResponse {
  id: number | null;
  query: string;
  research_brief: string;
  outline: string[];
  sections: OutlineSection[];
  outline_approved: boolean;
  outline_revisions: number;
  outline_feedback: string;
  usage?: UsageBlock | null;
}

export interface UsageStage {
  stage: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  avg_latency_ms: number;
}

export interface UsageBlock {
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  est_cost_usd: number;
  by_stage: UsageStage[];
}

export interface UsageQueryRow {
  id: number;
  query: string;
  created_at: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  est_cost_usd: number;
  user_email?: string;
}

export interface UsageTotals {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  llm_calls: number;
  queries_tracked: number;
  avg_tokens_per_query: number;
  est_cost_usd: number;
}

export interface UsageDay {
  day: string;
  calls: number;
  total_tokens: number;
  queries: number;
}

export interface UsageSummary {
  totals: UsageTotals;
  by_stage: UsageStage[];
  by_day: UsageDay[];
  recent: UsageQueryRow[];
  pricing_per_1m_usd: Record<string, { input: number; output: number }>;
  pricing_note: string;
}

export interface UsageCall {
  id: number;
  stage: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  created_at: string;
}
