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

export interface UsageStage {
  stage: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  avg_latency_ms: number;
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
