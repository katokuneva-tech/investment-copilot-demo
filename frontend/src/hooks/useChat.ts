'use client';

import { useState, useCallback, useRef } from 'react';
import { ChatSession, Message, ContentBlock, ThinkingStep } from '@/lib/types';
import { streamChatV2, SSEEvent } from '@/lib/api';

function generateId(): string {
  return Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
}

export function useChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSkillId, setActiveSkillId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgents, setActiveAgents] = useState<Array<{name: string; role: string; status?: string; elapsed?: number}>>([]);
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
    async (text: string, attachmentIds?: string[], overrideSkillId?: string) => {
      const skillId = overrideSkillId || activeSkillId || 'auto';
      if (isStreaming) return;

      let sessionId = activeSessionId;

      // Create session if needed (or if skill changed)
      if (!sessionId || (overrideSkillId && sessions.find(s => s.id === sessionId)?.skillId !== overrideSkillId)) {
        const id = generateId();
        const session: ChatSession = {
          id,
          skillId: skillId,
          title: text.slice(0, 60),
          messages: [],
        };
        setSessions((prev) => [session, ...prev]);
        setActiveSessionId(id);
        setActiveSkillId(skillId);
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

      const updateThinkingSteps = (step: ThinkingStep) => {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: s.messages.map((m) =>
                    m.id === assistantId
                      ? { ...m, thinkingSteps: [...(m.thinkingSteps || []), step] }
                      : m,
                  ),
                }
              : s,
          ),
        );
      };

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
          case 'status': {
            const content = (event as any).content || (event as any).message || '';
            let stepType: ThinkingStep['type'] = 'tool_result';
            if (content.startsWith('... ')) stepType = 'thinking';
            else if (content.startsWith('>> ')) stepType = 'tool_call';
            updateThinkingSteps({
              type: stepType,
              content: content.replace(/^\.\.\.\s*/, '').replace(/^>>\s*/, ''),
              timestamp: Date.now(),
            });
            break;
          }
          // V2: agents lifecycle events
          case 'agents_started': {
            const ev = event as any;
            setActiveAgents((ev.agents || []).map((a: any) => ({ name: a.name, role: a.role, status: 'running' })));
            updateThinkingSteps({
              type: 'thinking',
              content: `Запущено ${ev.agents?.length || 0} аналитиков: ${(ev.agents || []).map((a: any) => a.role).join(', ')}`,
              timestamp: Date.now(),
            });
            break;
          }
          case 'agent_progress': {
            const ev = event as any;
            setActiveAgents(prev => prev.map(a =>
              a.name === ev.agent ? { ...a, status: ev.status, elapsed: ev.elapsed } : a
            ));
            const icon = ev.status === 'done' ? '[OK]' : '[!]';
            const errorInfo = ev.status !== 'done' && ev.error ? ` — ${ev.error}` : '';
            updateThinkingSteps({
              type: 'tool_result',
              content: `${icon} ${ev.role} (${ev.elapsed}с)${errorInfo}`,
              timestamp: Date.now(),
            });
            break;
          }
          // V2: text chunks from director streaming
          case 'text': {
            const content = (event as any).content || '';
            if (!currentTextBlock) {
              currentTextBlock = { type: 'text', data: content };
              updateAssistantBlocks((blocks) => [...blocks, { ...currentTextBlock! }]);
            } else {
              currentTextBlock.data += content;
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
          case 'error': {
            updateAssistantBlocks((blocks) => [
              ...blocks,
              { type: 'text', data: `\n\n[!] Ошибка: ${(event as any).content}` },
            ]);
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
          case 'heartbeat': {
            // Keepalive from server — ignore
            break;
          }
          case 'done': {
            // Check if assistant message ended up empty — show error instead of blank
            setSessions((prev) =>
              prev.map((s) =>
                s.id === sessionId
                  ? {
                      ...s,
                      messages: s.messages.map((m) =>
                        m.id === assistantId && m.blocks.length === 0
                          ? { ...m, blocks: [{ type: 'text' as const, data: 'Не удалось получить ответ. Попробуйте ещё раз.' }] }
                          : m,
                      ),
                    }
                  : s,
              ),
            );
            setIsStreaming(false);
            setActiveAgents([]);
            abortRef.current = null;
            break;
          }
        }
      };

      const handleError = (error: Error) => {
        console.error('Stream error:', error);
        currentTextBlock = null;
        // If significant content already streamed, show a subtle note instead
        // of the alarming "error" banner. Many late-stream drops still leave
        // 95%+ of a useful answer on screen.
        updateAssistantBlocks((blocks) => {
          const streamedChars = blocks
            .filter((b) => b.type === 'text')
            .reduce((acc, b) => acc + String(b.data).length, 0);
          const message =
            streamedChars > 200
              ? '\n\n_(соединение прервано — ответ может быть неполным)_'
              : '\n\n⚠️ Произошла ошибка при получении ответа. Попробуйте ещё раз.';
          return [...blocks, { type: 'text', data: message }];
        });
        setIsStreaming(false);
        abortRef.current = null;
      };

      // Build conversation history for LLM context
      const currentSession = sessions.find(s => s.id === sessionId);
      const history = (currentSession?.messages || [])
          .filter(m => m.blocks.some(b => b.type === 'text'))
          .slice(-10)
          .map(m => ({
              role: m.role,
              content: m.blocks
                  .filter(b => b.type === 'text')
                  .map(b => String(b.data))
                  .join('\n'),
          }));

      await streamChatV2(
        skillId,
        text,
        sessionId,
        handleEvent,
        handleError,
        abortController.signal,
        attachmentIds,
        history,
      );
    },
    [activeSessionId, activeSkillId, isStreaming, sessions],
  );

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      setIsStreaming(false);
      setActiveAgents([]);
      abortRef.current = null;
    }
  }, []);

  return {
    sessions,
    activeSession,
    activeSessionId,
    activeSkillId,
    isStreaming,
    activeAgents,
    sendMessage,
    startNewChat,
    selectSession,
    selectSkill,
    stopStreaming,
  };
}
