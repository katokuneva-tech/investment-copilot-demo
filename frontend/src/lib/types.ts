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
