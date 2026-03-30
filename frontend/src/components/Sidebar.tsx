'use client';

import React, { useState, useEffect } from 'react';
import {
  MessageSquare, User, Database, Sparkles, Shield, Cpu,
  BarChart3, LogOut, ChevronDown,
} from 'lucide-react';
import { ChatSession } from '@/lib/types';
import { API_BASE_URL } from '@/lib/constants';

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  activeSkillId: string | null;
  onSelectSkill: (skillId: string) => void;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onSelectKB: () => void;
  isKBActive: boolean;
  onSelectCommittee: () => void;
  isCommitteeActive: boolean;
  isAdmin?: boolean;
  onSelectAnalytics?: () => void;
  isAnalyticsActive?: boolean;
  onLogout?: () => void;
}

function ModelSwitcher({ isAdmin = false }: { isAdmin?: boolean }) {
  const [provider, setProvider] = useState('cotype');
  const [modelName, setModelName] = useState('CoType Pro 2.6');
  const [isOpen, setIsOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('copilot_token');
    fetch(`${API_BASE_URL}/api/model`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.json())
      .then(d => { setProvider(d.provider); setModelName(d.model); })
      .catch(() => {});
  }, []);

  const switchModel = async (newProvider: string) => {
    setIsSwitching(true);
    try {
      const token = localStorage.getItem('copilot_token');
      const res = await fetch(`${API_BASE_URL}/api/model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ provider: newProvider }),
      });
      const d = await res.json();
      setProvider(d.provider);
      setModelName(d.model);
    } catch {}
    setIsSwitching(false);
    setIsOpen(false);
  };

  const models = [
    { id: 'cotype', name: 'CoType Pro 2.6', desc: 'MWS AI' },
    { id: 'claude', name: 'Claude Sonnet 4', desc: 'Anthropic' },
  ];

  // Non-admin: just show current model, no switching
  if (!isAdmin) {
    return (
      <div className="px-4 py-2 flex items-center gap-2 text-[11px] text-gray-400">
        <Cpu size={12} />
        <span>{modelName}</span>
        <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
      </div>
    );
  }

  return (
    <div className="relative px-4 py-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 text-[11px] text-gray-400 hover:text-gray-600 transition-colors"
      >
        <Cpu size={12} />
        <span className="flex-1 text-left">{isSwitching ? 'Переключение...' : modelName}</span>
        <span className={`w-1.5 h-1.5 rounded-full ${provider === 'claude' ? 'bg-blue-400' : 'bg-green-400'}`} />
        <ChevronDown size={10} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute bottom-full left-3 right-3 mb-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden z-50">
          {models.map(m => (
            <button
              key={m.id}
              onClick={() => switchModel(m.id)}
              className={`w-full px-3 py-2.5 text-left flex items-center gap-2 text-xs transition-colors ${
                provider === m.id ? 'bg-red-50 text-[#E11D48]' : 'hover:bg-gray-50 text-gray-600'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${m.id === 'claude' ? 'bg-blue-400' : 'bg-green-400'}`} />
              <div>
                <p className="font-medium">{m.name}</p>
                <p className="text-[10px] text-gray-400">{m.desc}</p>
              </div>
              {provider === m.id && <span className="ml-auto text-[10px]">Active</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onSelectKB,
  isKBActive,
  onSelectCommittee,
  isCommitteeActive,
  isAdmin = false,
  onSelectAnalytics,
  isAnalyticsActive = false,
  onLogout,
}: SidebarProps) {
  const chatSessions = sessions.filter((s) => s.messages.length > 0);
  const userName = typeof window !== 'undefined' ? localStorage.getItem('copilot_user') || 'Аналитик' : 'Аналитик';

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

      <div className="px-3 py-3 flex-1 overflow-y-auto custom-scrollbar">
        {/* New chat */}
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg text-sm font-medium text-[#E11D48] bg-red-50 hover:bg-red-100 transition-colors text-left mb-1"
        >
          <Sparkles size={16} />
          <span>Новый чат</span>
        </button>

        {/* Committee */}
        <button
          onClick={onSelectCommittee}
          className={`w-full flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg text-sm transition-colors text-left mb-3 ${
            isCommitteeActive
              ? 'bg-red-50 text-[#E11D48] font-medium'
              : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          <Shield size={16} className={isCommitteeActive ? 'text-[#E11D48]' : 'text-gray-400'} />
          <span>Комитет</span>
        </button>

        {/* Data section */}
        <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">
          Данные
        </p>
        <button
          onClick={onSelectKB}
          className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors text-left ${
            isKBActive
              ? 'bg-red-50 text-[#E11D48] font-medium'
              : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          <Database size={16} className={isKBActive ? 'text-[#E11D48]' : 'text-gray-400'} />
          <span>База знаний</span>
        </button>

        {/* Analytics (admin only) */}
        {isAdmin && onSelectAnalytics && (
          <button
            onClick={onSelectAnalytics}
            className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors text-left mt-1 ${
              isAnalyticsActive
                ? 'bg-red-50 text-[#E11D48] font-medium'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <BarChart3 size={16} className={isAnalyticsActive ? 'text-[#E11D48]' : 'text-gray-400'} />
            <span>Аналитика</span>
          </button>
        )}

        {/* Sessions */}
        {chatSessions.length > 0 && (
          <>
            <div className="border-b border-gray-100 my-3" />
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">
              Чаты
            </p>
            <div className="space-y-0.5">
              {chatSessions.map((session) => {
                const isCommittee = session.skillId === 'committee_advisor';
                const Icon = isCommittee ? Shield : MessageSquare;
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
                    <Icon size={14} className={isCommittee ? 'text-[#E11D48] shrink-0' : 'text-gray-400 shrink-0'} />
                    <p className="truncate text-xs">
                      {session.title || (isCommittee ? 'Комитет' : 'Новый чат')}
                    </p>
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Bottom: Model + User */}
      <div className="border-t border-gray-100">
        <ModelSwitcher isAdmin={isAdmin} />
        <div className="px-4 py-3 border-t border-gray-50 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
            <User size={16} className="text-gray-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-700 truncate">{userName}</p>
            <p className="text-[11px] text-gray-400">MWS Capital</p>
          </div>
          {onLogout && (
            <button onClick={onLogout} className="w-7 h-7 rounded-lg hover:bg-gray-100 flex items-center justify-center" title="Выйти">
              <LogOut size={13} className="text-gray-400" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
