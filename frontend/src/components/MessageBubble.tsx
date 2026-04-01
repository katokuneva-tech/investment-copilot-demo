'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot, Download } from 'lucide-react';
import { Message } from '@/lib/types';
import { getReportUrl } from '@/lib/api';
import RichTable from './RichTable';
import RichChart from './RichChart';
import PdfDownload from './PdfDownload';
import SourceCitation from './SourceCitation';
import ThinkingSteps from './ThinkingSteps';

function exportToPdf(message: Message) {
  // Collect all text blocks as markdown
  const textParts = message.blocks
    .filter(b => b.type === 'text')
    .map(b => String(b.data));
  const markdown = textParts.join('\n\n');

  // Convert basic markdown to HTML
  let html = markdown
    // Headers
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Bullet lists
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // Numbered lists
    .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
    // Paragraphs (double newline)
    .replace(/\n\n/g, '</p><p>')
    // Single newlines within paragraphs
    .replace(/\n/g, '<br/>');

  // Wrap consecutive <li> in <ul>
  html = html.replace(/(<li>[^]*?<\/li>(?:<br\/>)?)+/g, (match) => {
    return '<ul>' + match.replace(/<br\/>/g, '') + '</ul>';
  });

  // Simple markdown table → HTML table
  const tableRegex = /\|(.+)\|\s*\n\|[-| :]+\|\s*\n((?:\|.+\|\s*\n?)+)/g;
  html = html.replace(tableRegex, (_match, headerRow, bodyRows) => {
    const headers = headerRow.split('|').map((h: string) => h.trim()).filter(Boolean);
    const rows = bodyRows.trim().split('\n').map((row: string) =>
      row.split('|').map((c: string) => c.trim()).filter(Boolean)
    );
    let table = '<table><thead><tr>';
    headers.forEach((h: string) => { table += `<th>${h}</th>`; });
    table += '</tr></thead><tbody>';
    rows.forEach((row: string[]) => {
      table += '<tr>';
      row.forEach((c: string) => { table += `<td>${c}</td>`; });
      table += '</tr>';
    });
    table += '</tbody></table>';
    return table;
  });

  const now = new Date().toLocaleDateString('ru-RU');
  const printWindow = window.open('', '_blank');
  if (!printWindow) return;

  printWindow.document.write(`<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>MWS AI — Отчёт</title>
<style>
  @page { margin: 20mm 15mm; size: A4; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1e293b; font-size: 11pt; line-height: 1.6; max-width: 700px; margin: 0 auto; padding: 20px; }
  h1 { font-size: 18pt; color: #E11D48; border-bottom: 2px solid #E11D48; padding-bottom: 6px; }
  h2 { font-size: 14pt; color: #1a2b4a; margin-top: 20px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
  h3 { font-size: 12pt; color: #374151; margin-top: 14px; }
  p { margin: 6px 0; }
  ul { padding-left: 20px; }
  li { margin: 3px 0; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 9pt; }
  th { background: #1a2b4a; color: white; padding: 6px 8px; text-align: left; border: 1px solid #1a2b4a; }
  td { padding: 5px 8px; border: 1px solid #e5e7eb; }
  tr:nth-child(even) { background: #f8fafc; }
  strong { color: #111827; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #E11D48; }
  .logo { font-size: 20pt; font-weight: bold; color: #E11D48; }
  .meta { font-size: 9pt; color: #9ca3af; text-align: right; }
  .footer { margin-top: 30px; padding-top: 10px; border-top: 1px solid #e5e7eb; font-size: 8pt; color: #9ca3af; text-align: center; }
  @media print { body { padding: 0; } .no-print { display: none; } }
</style></head><body>
<div class="header">
  <div class="logo">MWS</div>
  <div class="meta">AI Corporate Copilot Hub<br/>АФК Система<br/>${now}</div>
</div>
<p>${html}</p>
<div class="footer">MWS AI Corporate Copilot Hub · Конфиденциально · ${now}</div>
<script>window.onload = function() { window.print(); }</script>
</body></html>`);
  printWindow.document.close();
}

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble = React.memo(function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    const text = message.blocks[0]?.data || '';
    return (
      <div className="flex justify-end mb-4">
        <div className="flex items-end gap-2 max-w-[70%]">
          <div className="bg-gray-100 rounded-2xl rounded-br-md px-4 py-2.5">
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{text}</p>
          </div>
          <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
            <User size={14} className="text-gray-500" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex mb-4">
      <div className="flex items-start gap-2.5 w-full max-w-[85%]">
        <div className="w-7 h-7 rounded-full bg-red-50 flex items-center justify-center shrink-0 mt-0.5">
          <Bot size={14} className="text-[#E11D48]" />
        </div>
        <div className="flex-1 min-w-0">
          {message.blocks.map((block, i) => {
            switch (block.type) {
              case 'text':
                return (
                  <div key={i} className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-headings:font-semibold prose-h2:text-base prose-h2:mt-4 prose-h2:mb-2 prose-h2:border-b prose-h2:border-gray-100 prose-h2:pb-1 prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1 prose-p:text-gray-700 prose-p:leading-relaxed prose-li:text-gray-700 prose-strong:text-gray-900 prose-a:text-[#E11D48] prose-code:text-[#E11D48] prose-code:bg-red-50 prose-code:px-1 prose-code:rounded">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        table: ({ children }) => (
                          <div className="my-3 overflow-x-auto rounded-lg border border-gray-200">
                            <table className="w-full text-xs border-collapse">{children}</table>
                          </div>
                        ),
                        thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
                        th: ({ children }) => <th className="text-left px-3 py-2 font-semibold text-gray-700 border border-gray-200 whitespace-nowrap">{children}</th>,
                        td: ({ children }) => <td className="px-3 py-1.5 text-gray-600 border border-gray-100">{children}</td>,
                      }}
                    >
                      {String(block.data)}
                    </ReactMarkdown>
                  </div>
                );
              case 'table':
                return <RichTable key={i} data={block.data} />;
              case 'chart':
                return <RichChart key={i} data={block.data} />;
              case 'pdf_link':
                return <PdfDownload key={i} data={block.data} />;
              case 'sources':
                return <SourceCitation key={i} sources={block.data} />;
              default:
                return null;
            }
          })}
          {/* Client-side PDF export via browser print */}
          {message.blocks.length > 0 && message.blocks.some(b => b.type === 'text' && String(b.data).length > 100) && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <button
                onClick={() => exportToPdf(message)}
                className="text-[11px] text-gray-400 hover:text-[#E11D48] transition-colors flex items-center gap-1"
              >
                <Download size={11} />
                Сохранить в PDF
              </button>
            </div>
          )}
          {/* Thinking steps */}
          {message.thinkingSteps && message.thinkingSteps.length > 0 && (
            <ThinkingSteps
              steps={message.thinkingSteps}
              isStreaming={message.blocks.length === 0}
            />
          )}
          {/* Fallback: bounce dots if no steps and no blocks */}
          {message.blocks.length === 0 && (!message.thinkingSteps || message.thinkingSteps.length === 0) && (
            <div className="flex items-center gap-1.5 py-2">
              <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0ms]" />
              <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:150ms]" />
              <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

export default MessageBubble;
