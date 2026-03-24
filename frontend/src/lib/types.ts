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

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  blocks: ContentBlock[];
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
  data: Record<string, any>[];
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
