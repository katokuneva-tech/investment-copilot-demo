'use client';

import { useState, useCallback, useRef } from 'react';
import { ChatSession, Message, ContentBlock } from '@/lib/types';
import { streamChat, SSEEvent } from '@/lib/api';

function generateId(): string {
  return Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
}

export function useChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSkillId, setActiveSkillId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  const startNewChat = useCallback((skillId: string) => {
    const id = generateId();
    const session: ChatSession = {
      id,
      skillId,
      title: '',
      messages: [],
    };
    setSessions((prev) => [session, ...prev]);
    setActiveSessionId(id);
    setActiveSkillId(skillId);
  }, []);

  const selectSession = useCallback(
    (sessionId: string) => {
      const session = sessions.find((s) => s.id === sessionId);
      if (session) {
        setActiveSessionId(sessionId);
        setActiveSkillId(session.skillId);
      }
    },
    [sessions],
  );

  const selectSkill = useCallback(
    (skillId: string) => {
      // If there's already an empty session for this skill, activate it
      const existing = sessions.find(
        (s) => s.skillId === skillId && s.messages.length === 0,
      );
      if (existing) {
        setActiveSessionId(existing.id);
        setActiveSkillId(skillId);
      } else {
        startNewChat(skillId);
      }
    },
    [sessions, startNewChat],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!activeSkillId || isStreaming) return;

      let sessionId = activeSessionId;

      // Create session if needed
      if (!sessionId) {
        const id = generateId();
        const session: ChatSession = {
          id,
          skillId: activeSkillId,
          title: text.slice(0, 60),
          messages: [],
        };
        setSessions((prev) => [session, ...prev]);
        setActiveSessionId(id);
        sessionId = id;
      }

      // Add user message
      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        blocks: [{ type: 'text', data: text }],
        timestamp: new Date(),
      };

      // Update title if first message
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                title: s.title || text.slice(0, 60),
                messages: [...s.messages, userMessage],
              }
            : s,
        ),
      );

      // Create assistant message placeholder
      const assistantId = generateId();
      const assistantMessage: Message = {
        id: assistantId,
        role: 'assistant',
        blocks: [],
        timestamp: new Date(),
      };

      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, messages: [...s.messages, assistantMessage] }
            : s,
        ),
      );

      setIsStreaming(true);

      const abortController = new AbortController();
      abortRef.current = abortController;

      let currentTextBlock: ContentBlock | null = null;

      const updateAssistantBlocks = (
        updater: (blocks: ContentBlock[]) => ContentBlock[],
      ) => {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: s.messages.map((m) =>
                    m.id === assistantId
                      ? { ...m, blocks: updater(m.blocks) }
                      : m,
                  ),
                }
              : s,
          ),
        );
      };

      const handleEvent = (event: SSEEvent) => {
        switch (event.type) {
          case 'text_delta': {
            if (!currentTextBlock) {
              currentTextBlock = { type: 'text', data: event.content };
              updateAssistantBlocks((blocks) => [...blocks, { ...currentTextBlock! }]);
            } else {
              currentTextBlock.data += event.content;
              const snapshot = currentTextBlock.data;
              updateAssistantBlocks((blocks) => {
                const last = blocks[blocks.length - 1];
                if (last && last.type === 'text') {
                  return [...blocks.slice(0, -1), { type: 'text', data: snapshot }];
                }
                return [...blocks, { type: 'text', data: snapshot }];
              });
            }
            break;
          }
          case 'text_done': {
            currentTextBlock = null;
            break;
          }
          case 'table':
          case 'chart':
          case 'pdf_link':
          case 'sources': {
            currentTextBlock = null;
            updateAssistantBlocks((blocks) => [
              ...blocks,
              { type: event.type, data: event.data },
            ]);
            break;
          }
          case 'done': {
            setIsStreaming(false);
            abortRef.current = null;
            break;
          }
        }
      };

      const handleError = (error: Error) => {
        console.error('Stream error:', error);
        currentTextBlock = null;
        updateAssistantBlocks((blocks) => [
          ...blocks,
          {
            type: 'text',
            data: '\n\n⚠️ Произошла ошибка при получении ответа. Попробуйте ещё раз.',
          },
        ]);
        setIsStreaming(false);
        abortRef.current = null;
      };

      await streamChat(
        activeSkillId,
        text,
        sessionId,
        handleEvent,
        handleError,
        abortController.signal,
      );
    },
    [activeSessionId, activeSkillId, isStreaming],
  );

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, []);

  return {
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
  };
}
