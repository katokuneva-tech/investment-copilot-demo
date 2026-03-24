'use client';

import React from 'react';
import { useChat } from '@/hooks/useChat';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';

export default function AppShell() {
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

  const handleNewChat = () => {
    if (activeSkillId) {
      startNewChat(activeSkillId);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        activeSkillId={activeSkillId}
        onSelectSkill={selectSkill}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
      />
      <ChatArea
        activeSession={activeSession}
        activeSkillId={activeSkillId}
        isStreaming={isStreaming}
        onSendMessage={sendMessage}
        onSelectSkill={selectSkill}
        onStopStreaming={stopStreaming}
      />
    </div>
  );
}
