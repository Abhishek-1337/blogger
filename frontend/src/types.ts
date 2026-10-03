export interface OutlineSection {
  title: string;
  bullets: string[];
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
