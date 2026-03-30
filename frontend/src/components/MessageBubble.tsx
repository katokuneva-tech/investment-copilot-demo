'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot } from 'lucide-react';
import { Message } from '@/lib/types';
import { exportBlocks, getReportUrl } from '@/lib/api';
import RichTable from './RichTable';
import RichChart from './RichChart';
import PdfDownload from './PdfDownload';
import SourceCitation from './SourceCitation';
import ThinkingSteps from './ThinkingSteps';

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
                  <div key={i} className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-headings:font-semibold prose-h2:text-base prose-h2:mt-4 prose-h2:mb-2 prose-h2:border-b prose-h2:border-gray-100 prose-h2:pb-1 prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1 prose-p:text-gray-700 prose-p:leading-relaxed prose-li:text-gray-700 prose-strong:text-gray-900 prose-a:text-[#E11D48] prose-code:text-[#E11D48] prose-code:bg-red-50 prose-code:px-1 prose-code:rounded prose-table:text-xs prose-th:bg-gray-50 prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1 prose-td:border-gray-200">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
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
          {/* Export button — only show if no auto-generated pdf_link exists */}
          {message.blocks.length > 0 && !message.blocks.some(b => b.type === 'pdf_link') && message.blocks.some(b => b.type === 'text' && String(b.data).length > 100) && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <button
                onClick={async () => {
                  try {
                    const url = await exportBlocks(message.blocks, message.blocks[0]?.data?.toString().slice(0, 50) || 'Ответ');
                    window.open(getReportUrl(url.split('/').pop() || ''), '_blank');
                  } catch (e) { console.error('Export failed:', e); }
                }}
                className="text-[11px] text-gray-400 hover:text-[#E11D48] transition-colors flex items-center gap-1"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Экспорт в PDF
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
