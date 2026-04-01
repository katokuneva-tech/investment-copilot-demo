'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Square,
  BarChart3,
  FileText,
  TrendingUp,
  GitCompare,
  Shield,
  Paperclip,
  X,
} from 'lucide-react';
import { SKILLS } from '@/lib/constants';
import { ChatSession, KBDocument } from '@/lib/types';
import { uploadChatFile } from '@/lib/api';
import MessageBubble from './MessageBubble';
import SkillSelector from './SkillSelector';

const ICON_MAP: Record<string, React.ElementType> = {
  BarChart3,
  FileText,
  TrendingUp,
  GitCompare,
  Shield,
};

interface ChatAreaProps {
  activeSession: ChatSession | null;
  activeSkillId: string | null;
  isStreaming: boolean;
  activeAgents?: Array<{name: string; role: string; status?: string; elapsed?: number}>;
  onSendMessage: (text: string, attachmentIds?: string[], overrideSkillId?: string) => void;
  onSelectSkill: (skillId: string) => void;
  onStopStreaming: () => void;
}

export default function ChatArea({
  activeSession,
  activeSkillId,
  isStreaming,
  activeAgents = [],
  onSendMessage,
  onSelectSkill,
  onStopStreaming,
}: ChatAreaProps) {
  const [input, setInput] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<KBDocument[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const skill = SKILLS.find((s) => s.id === activeSkillId);
  const messages = activeSession?.messages || [];
  const showSelector = !activeSession || messages.length === 0;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  const handleAttach = () => fileInputRef.current?.click();

  const handleFileAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !activeSession) return;
    for (const file of Array.from(files)) {
      try {
        const doc = await uploadChatFile(file, activeSession.id);
        setAttachedFiles(prev => [...prev, doc]);
      } catch (err) {
        console.error('Upload failed:', err);
        alert(`Не удалось загрузить файл ${file.name}. Попробуйте ещё раз.`);
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (docId: string) => {
    setAttachedFiles(prev => prev.filter(f => f.id !== docId));
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    const ids = attachedFiles.map(f => f.id);
    setInput('');
    setAttachedFiles([]);
    onSendMessage(text, ids);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePromptClick = (skillId: string, prompt: string) => {
    onSendMessage(prompt, undefined, skillId);
  };

  const SkillIcon = skill ? ICON_MAP[skill.icon] || FileText : null;

  return (
    <div className="flex-1 flex flex-col h-screen bg-[#F9FAFB]">
      {/* Header */}
      <div className="px-6 py-3 border-b border-gray-200 bg-white flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
          <BarChart3 size={16} className="text-[#E11D48]" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-gray-800">
            Investment Intelligence Copilot
          </h1>
          <p className="text-xs text-gray-400">AI-аналитик портфеля АФК Система</p>
        </div>
      </div>

      {/* Messages or Selector */}
      {showSelector ? (
        <SkillSelector
          onSelectSkill={onSelectSkill}
          onSendPrompt={handlePromptClick}
        />
      ) : (
        <div className="flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          {/* V2 Agent Progress Indicator */}
          {isStreaming && activeAgents.length > 0 && (
            <div className="mx-4 mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
              <div className="text-xs font-medium text-gray-500 mb-2">
                AI Board — {activeAgents.length} аналитиков
              </div>
              <div className="space-y-1">
                {activeAgents.map((agent) => (
                  <div key={agent.name} className="flex items-center gap-2 text-xs">
                    <span className={`w-2 h-2 rounded-full ${
                      agent.status === 'done' ? 'bg-green-500' :
                      agent.status === 'error' ? 'bg-red-500' :
                      'bg-yellow-400 animate-pulse'
                    }`} />
                    <span className="text-gray-700 flex-1">{agent.role}</span>
                    {agent.elapsed && (
                      <span className="text-gray-400">{agent.elapsed}с</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input */}
      <div className="px-6 py-4 bg-white border-t border-gray-200">
        {attachedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2 max-w-4xl mx-auto">
            {attachedFiles.map(f => (
              <div key={f.id} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-50 text-[#E11D48] text-xs">
                <FileText size={12} />
                <span className="truncate max-w-[150px]">{f.original_name}</span>
                <button onClick={() => removeAttachment(f.id)} className="hover:text-red-700">
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2 max-w-4xl mx-auto">
          <button
            onClick={handleAttach}
            className="w-10 h-10 rounded-xl hover:bg-gray-100 flex items-center justify-center transition-colors shrink-0"
            title="Прикрепить файл"
          >
            <Paperclip size={16} className="text-gray-400" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.pdf,.docx,.xlsx,.xls,.txt,.md,.csv"
            multiple
            onChange={handleFileAttach}
            className="hidden"
          />
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Задайте вопрос по портфелю, проектам, рынкам..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E11D48]/20 focus:border-[#E11D48]/40 transition-all"
          />
          {isStreaming ? (
            <button
              onClick={onStopStreaming}
              className="w-10 h-10 rounded-xl bg-gray-200 hover:bg-gray-300 flex items-center justify-center transition-colors shrink-0"
            >
              <Square size={16} className="text-gray-600" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="w-10 h-10 rounded-xl bg-[#E11D48] hover:bg-[#BE123C] disabled:bg-gray-200 disabled:cursor-not-allowed flex items-center justify-center transition-colors shrink-0"
            >
              <Send
                size={16}
                className={input.trim() ? 'text-white' : 'text-gray-400'}
              />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
