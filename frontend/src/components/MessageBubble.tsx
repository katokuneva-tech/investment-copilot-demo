'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';
import { Message } from '@/lib/types';
import RichTable from './RichTable';
import RichChart from './RichChart';
import PdfDownload from './PdfDownload';
import SourceCitation from './SourceCitation';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
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
                  <div
                    key={i}
                    className="prose prose-sm max-w-none text-gray-700 prose-headings:text-gray-800 prose-strong:text-gray-800 prose-a:text-[#E11D48] prose-code:text-[#E11D48] prose-code:bg-red-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200"
                  >
                    <ReactMarkdown>{block.data}</ReactMarkdown>
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
          {message.blocks.length === 0 && (
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
}
