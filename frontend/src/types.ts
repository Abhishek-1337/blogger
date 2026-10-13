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
}
