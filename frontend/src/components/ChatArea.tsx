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
} from 'lucide-react';
import { SKILLS } from '@/lib/constants';
import { ChatSession } from '@/lib/types';
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
  onSendMessage: (text: string) => void;
  onSelectSkill: (skillId: string) => void;
  onStopStreaming: () => void;
}

export default function ChatArea({
  activeSession,
  activeSkillId,
  isStreaming,
  onSendMessage,
  onSelectSkill,
  onStopStreaming,
}: ChatAreaProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput('');
    onSendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePromptClick = (skillId: string, prompt: string) => {
    onSelectSkill(skillId);
    setTimeout(() => onSendMessage(prompt), 50);
  };

  const SkillIcon = skill ? ICON_MAP[skill.icon] || FileText : null;

  return (
    <div className="flex-1 flex flex-col h-screen bg-[#F9FAFB]">
      {/* Header */}
      {skill && (
        <div className="px-6 py-3 border-b border-gray-200 bg-white flex items-center gap-3">
          {SkillIcon && (
            <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
              <SkillIcon size={16} className="text-[#E11D48]" />
            </div>
          )}
          <div>
            <h1 className="text-sm font-semibold text-gray-800">
              {skill.name}
            </h1>
            <p className="text-xs text-gray-400">{skill.description}</p>
          </div>
        </div>
      )}

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
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input */}
      <div className="px-6 py-4 bg-white border-t border-gray-200">
        <div className="flex items-end gap-2 max-w-4xl mx-auto">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              skill
                ? `Задайте вопрос по «${skill.name}»...`
                : 'Выберите инструмент и задайте вопрос...'
            }
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
