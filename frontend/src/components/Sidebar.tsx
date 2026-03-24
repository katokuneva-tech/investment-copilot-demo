'use client';

import React from 'react';
import {
  BarChart3,
  FileText,
  TrendingUp,
  GitCompare,
  Shield,
  Plus,
  MessageSquare,
  User,
} from 'lucide-react';
import { SKILLS } from '@/lib/constants';
import { ChatSession } from '@/lib/types';

const ICON_MAP: Record<string, React.ElementType> = {
  BarChart3,
  FileText,
  TrendingUp,
  GitCompare,
  Shield,
};

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  activeSkillId: string | null;
  onSelectSkill: (skillId: string) => void;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
}

export default function Sidebar({
  sessions,
  activeSessionId,
  activeSkillId,
  onSelectSkill,
  onSelectSession,
  onNewChat,
}: SidebarProps) {
  return (
    <aside className="w-60 h-screen flex flex-col bg-white border-r border-gray-200 shrink-0">
      {/* Logo */}
      <div className="px-5 pt-5 pb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold text-[#E11D48]">MWS</span>
          <span className="text-[10px] font-semibold tracking-wide text-gray-400 uppercase leading-tight">
            AI Corporate
            <br />
            Copilot Hub
          </span>
        </div>
        <p className="text-xs text-gray-400 mt-1">АФК Система</p>
      </div>

      <div className="border-b border-gray-100 mx-4" />

      {/* Skills */}
      <div className="px-3 py-3 flex-1 overflow-y-auto custom-scrollbar">
        <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">
          Инструменты
        </p>
        <nav className="space-y-0.5">
          {SKILLS.map((skill) => {
            const Icon = ICON_MAP[skill.icon] || FileText;
            const isActive = activeSkillId === skill.id;
            return (
              <button
                key={skill.id}
                onClick={() => onSelectSkill(skill.id)}
                className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors text-left ${
                  isActive
                    ? 'bg-red-50 text-[#E11D48] font-medium'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Icon size={16} className={isActive ? 'text-[#E11D48]' : 'text-gray-400'} />
                <span className="truncate">{skill.name}</span>
              </button>
            );
          })}
        </nav>

        {/* Sessions */}
        {sessions.length > 0 && (
          <>
            <div className="border-b border-gray-100 my-3" />
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">
              Чаты
            </p>
            <div className="space-y-0.5">
              {sessions
                .filter((s) => s.messages.length > 0)
                .map((session) => {
                  const skill = SKILLS.find((s) => s.id === session.skillId);
                  return (
                    <button
                      key={session.id}
                      onClick={() => onSelectSession(session.id)}
                      className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors text-left ${
                        activeSessionId === session.id
                          ? 'bg-gray-100 text-gray-900 font-medium'
                          : 'text-gray-500 hover:bg-gray-50'
                      }`}
                    >
                      <MessageSquare size={14} className="text-gray-400 shrink-0" />
                      <div className="truncate">
                        <p className="truncate text-xs">
                          {session.title || skill?.name || 'Новый чат'}
                        </p>
                      </div>
                    </button>
                  );
                })}
            </div>
          </>
        )}
      </div>

      {/* New chat button */}
      <div className="px-3 pb-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
        >
          <Plus size={16} />
          Новый чат
        </button>
      </div>

      {/* User */}
      <div className="px-4 py-3 border-t border-gray-100 flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
          <User size={16} className="text-gray-500" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-700">Аналитик</p>
          <p className="text-[11px] text-gray-400">MWS Capital</p>
        </div>
      </div>
    </aside>
  );
}
