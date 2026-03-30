'use client';

import React, { useState, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';
import KnowledgeBase from './KnowledgeBase';
import CommitteeView from './CommitteeView';
import LoginScreen from './LoginScreen';
import AnalyticsDashboard from './AnalyticsDashboard';

export default function AppShell() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userRole, setUserRole] = useState('user');
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  const {
    sessions,
    activeSession,
    activeSessionId,
    activeSkillId,
    isStreaming,
    sendMessage,
    startNewChat,
    selectSession,
    selectSkill,
    stopStreaming,
  } = useChat();

  const [view, setView] = useState<'chat' | 'kb' | 'committee' | 'analytics'>('chat');

  // Check existing token on mount
  useEffect(() => {
    const token = localStorage.getItem('copilot_token');
    const role = localStorage.getItem('copilot_role');
    if (token) {
      setIsAuthenticated(true);
      setUserRole(role || 'user');
    }
    setIsCheckingAuth(false);
  }, []);

  const handleLogin = (token: string, name: string, role: string) => {
    setIsAuthenticated(true);
    setUserRole(role);
  };

  const handleLogout = () => {
    localStorage.removeItem('copilot_token');
    localStorage.removeItem('copilot_user');
    localStorage.removeItem('copilot_role');
    setIsAuthenticated(false);
    setUserRole('user');
  };

  // Loading state
  if (isCheckingAuth) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#F9FAFB]">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#E11D48] rounded-full animate-spin" />
      </div>
    );
  }

  // Auth gate
  if (!isAuthenticated) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  const handleSelectSkill = (skillId: string) => {
    setView('chat');
    selectSkill(skillId);
  };

  const handleSelectSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session?.skillId === 'committee_advisor') {
      setView('committee');
    } else {
      setView('chat');
    }
    selectSession(sessionId);
  };

  const handleNewChat = () => {
    setView('chat');
    startNewChat('auto');
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        activeSkillId={view === 'chat' ? activeSkillId : null}
        onSelectSkill={handleSelectSkill}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onSelectKB={() => setView('kb')}
        isKBActive={view === 'kb'}
        onSelectCommittee={() => setView('committee')}
        isCommitteeActive={view === 'committee'}
        isAdmin={userRole === 'admin'}
        onSelectAnalytics={() => setView('analytics')}
        isAnalyticsActive={view === 'analytics'}
        onLogout={handleLogout}
      />
      {view === 'kb' ? (
        <KnowledgeBase />
      ) : view === 'committee' ? (
        <CommitteeView />
      ) : view === 'analytics' && userRole === 'admin' ? (
        <AnalyticsDashboard />
      ) : (
        <ChatArea
          activeSession={activeSession}
          activeSkillId={activeSkillId || 'auto'}
          isStreaming={isStreaming}
          onSendMessage={sendMessage}
          onSelectSkill={handleSelectSkill}
          onStopStreaming={stopStreaming}
        />
      )}
    </div>
  );
}
