export interface Skill {
  id: string;
  name: string;
  description: string;
  icon: string;
  suggestedPrompts: string[];
}

export interface ContentBlock {
  type: 'text' | 'table' | 'chart' | 'pdf_link' | 'sources';
  data: any;
}

export interface ThinkingStep {
  type: 'thinking' | 'tool_call' | 'tool_result';
  content: string;
  timestamp: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  blocks: ContentBlock[];
  thinkingSteps?: ThinkingStep[];
  timestamp: Date;
}

export interface ChatSession {
  id: string;
  skillId: string;
  title: string;
  messages: Message[];
}

export interface TableData {
  headers: string[];
  rows: string[][];
  caption?: string;
}

export interface ChartSeries {
  key: string;
  name: string;
  color: string;
}

export interface ChartData {
  chart_type: 'bar' | 'line';
  title: string;
  x_key: string;
  series: ChartSeries[];
  data: Record<string, string | number>[];
}

export interface PdfLinkData {
  report_id: string;
  title: string;
  description?: string;
}

export interface SourceData {
  title: string;
  type?: string;
}

// --- V2 Multi-Agent Types ---

export interface AgentInfo {
  name: string;
  role: string;
}

export interface AgentProgress {
  agent: string;
  role: string;
  status: 'done' | 'error';
  elapsed: number;
  preview: string;
}

export interface AgentsMetadata {
  use_case: string;
  agents_used: string[];
  total_elapsed_sec: number;
  agent_details: Array<{
    name: string;
    role: string;
    elapsed_sec: number;
    has_error: boolean;
  }>;
}

export interface KBDocument {
  id: string;
  filename: string;
  original_name: string;
  file_type: string;
  scope: 'global' | 'session';
  session_id: string | null;
  uploaded_at: string;
  size_bytes: number;
  status: 'ready' | 'processing' | 'error';
  text_preview: string;
  is_active: boolean;
}

// --- News Monitoring ---

export interface PortfolioImpact {
  company_slug: string;
  metric: string;
  direction: 'positive' | 'negative' | 'risk' | 'opportunity';
  context: string;
}

export interface NewsArticle {
  id: string;
  company_slug: string;
  company_name: string;
  title: string;
  url: string;
  snippet: string;
  source: string;
  published_approx: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  summary: string;
  alert_type: string | null;
  portfolio_impact: PortfolioImpact | null;
}

export interface NewsAlert {
  id: string;
  company_slug: string;
  company_name: string;
  alert_type: string;
  title: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
}

export interface NewsCompany {
  slug: string;
  name: string;
  article_count?: number;
}

export interface NewsDashboard {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  sentiment_by_company: Array<{
    slug: string;
    name: string;
    positive: number;
    negative: number;
    neutral: number;
    total: number;
  }>;
  alerts: NewsAlert[];
  top_companies: Array<{ slug: string; name: string; count: number }>;
}

export interface NewsDigest {
  digest: string;
  period: string;
  article_count: number;
  generated_at: string;
}
