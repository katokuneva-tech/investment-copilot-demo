'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Shield, Upload, Eye, EyeOff, Trash2, FileText, FileSpreadsheet, File,
  Search, AlertTriangle, ClipboardCheck, FileEdit, HelpCircle,
  ScrollText, Send, Square, X, Zap,
} from 'lucide-react';
import { API_BASE_URL } from '@/lib/constants';
import { useDocuments } from '@/hooks/useDocuments';
import { useChat } from '@/hooks/useChat';
import { KBDocument } from '@/lib/types';
import { fetchDocumentContent } from '@/lib/api';
import MessageBubble from './MessageBubble';

const FILE_ICONS: Record<string, React.ElementType> = {
  pdf: FileText, docx: FileText, json: FileText, md: FileText, txt: FileText,
  xlsx: FileSpreadsheet, xls: FileSpreadsheet, csv: FileSpreadsheet,
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const QUICK_ACTIONS = [
  { id: 'pre_analysis', icon: Zap, label: 'Pre-Analysis Brief', color: 'text-[#E11D48]',
    prompt: 'Проведи Pre-Analysis Brief: инвентаризация документов, ключевые метрики сделки (CAPEX, IRR, NPV, payback), перекрёстная проверка данных между документами, red flags и рекомендации. Будь скептичен.' },
  { id: 'contradictions', icon: Search, label: 'Противоречия', color: 'text-red-500',
    prompt: 'Найди все противоречия и расхождения между загруженными документами. Сравни цифры в презентации, финансовой модели, отчёте оценщика и юридическом DD. Покажи таблицу.' },
  { id: 'risks', icon: AlertTriangle, label: 'Матрица рисков', color: 'text-amber-500',
    prompt: 'Составь полную матрицу рисков по материалам сделки. Для каждого риска укажи: название, критичность, вероятность, влияние на NPV/IRR, источник (документ и страница). Покажи таблицу.' },
  { id: 'recommendation', icon: ClipboardCheck, label: 'Рекомендация', color: 'text-green-500',
    prompt: 'Подготовь рекомендацию по сделке: структурированные аргументы ЗА и ПРОТИВ. В конце дай итоговое заключение с условиями.' },
  { id: 'summary', icon: ScrollText, label: 'Executive Summary', color: 'text-blue-500',
    prompt: 'Подготовь executive summary по материалам сделки на 1 страницу: суть сделки, стороны, объём инвестиций, ключевые финансовые параметры (NPV, IRR, payback), основные условия, краткая оценка.' },
  { id: 'dd_checklist', icon: FileEdit, label: 'Чеклист DD', color: 'text-purple-500',
    prompt: 'Проверь полноту due diligence: какие документы загружены, какие обычно требуются для инвесткомитета но отсутствуют, есть ли red flags в имеющихся документах. Покажи таблицу с чеклистом.' },
  { id: 'questions', icon: HelpCircle, label: 'Вопросы комитета', color: 'text-cyan-500',
    prompt: 'Какие вопросы должен задать инвестиционный комитет менеджменту проекта? Составь пронумерованный список из 10-15 критичных вопросов, сгруппированных по темам: финансы, рынок, риски, управление.' },
  { id: 'protocol', icon: FileText, label: 'Драфт протокола', color: 'text-gray-600',
    prompt: 'Сгенерируй драфт протокола заседания инвестиционного комитета АФК Система по рассматриваемой сделке. Формат: дата, участники, повестка, ключевые замечания, решение (условно положительное с перечнем условий), ответственные, сроки.' },
];

export default function CommitteeView() {
  const { documents: allDocs, upload: uploadDoc, remove: removeDocs, toggle: toggleDoc } = useDocuments();
  const {
    sessions, activeSession, activeSessionId, isStreaming,
    sendMessage, startNewChat, selectSession,
  } = useChat();

  const [input, setInput] = useState('');
  const [viewDoc, setViewDoc] = useState<{ doc: KBDocument; content: string } | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [preAnalysis, setPreAnalysis] = useState<string | null>(null);
  const [isPreAnalysisLoading, setIsPreAnalysisLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Filter committee-relevant docs
  const committeeDocs = allDocs.filter(d =>
    d.id.startsWith('src_project') || d.id.startsWith('src_finmodel') ||
    d.id.startsWith('src_appraiser') || d.id.startsWith('src_mgmt') ||
    d.id.startsWith('src_legal_dd') || d.id.startsWith('src_committee') ||
    (!d.id.startsWith('src_') && d.id !== 'kb_default')
  );

  const activeCommitteeDocs = committeeDocs.filter(d => d.is_active !== false);

  // Ensure committee session exists
  useEffect(() => {
    const withMessages = sessions.filter(s => s.skillId === 'committee_advisor' && s.messages.length > 0);
    const empty = sessions.find(s => s.skillId === 'committee_advisor' && s.messages.length === 0);
    const target = withMessages[0] || empty;

    if (target) {
      if (activeSessionId !== target.id) selectSession(target.id);
    } else {
      startNewChat('committee_advisor');
    }
  }, [sessions.length]);

  const messages = activeSession?.messages || [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput('');
    sendMessage(text);
  };

  const handleQuickAction = (prompt: string) => {
    if (isStreaming) return;
    sendMessage(prompt);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleUpload = () => fileInputRef.current?.click();
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    for (const file of Array.from(files)) { await uploadDoc(file); }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleView = async (doc: KBDocument) => {
    setLoadingContent(true);
    try {
      const data = await fetchDocumentContent(doc.id);
      setViewDoc({ doc: data.document, content: data.content });
    } catch {} finally { setLoadingContent(false); }
  };

  const handleToggle = async (doc: KBDocument) => {
    setTogglingId(doc.id);
    await toggleDoc(doc.id);
    setTogglingId(null);
  };

  const handleDelete = (doc: KBDocument) => {
    if (window.confirm(`Удалить "${doc.original_name}"?`)) removeDocs(doc.id);
  };

  const handlePreAnalysis = async () => {
    setIsPreAnalysisLoading(true);
    // Send as a chat message so it renders with full markdown
    sendMessage('Проведи Pre-Analysis Brief: инвентаризация документов, ключевые метрики сделки, перекрёстная проверка данных, red flags и рекомендации');
    setIsPreAnalysisLoading(false);
  };

  return (
    <div className="flex-1 flex h-screen bg-[#F9FAFB]">
      {/* Left panel: Documents + Quick Actions */}
      <div className="w-80 border-r border-gray-200 bg-white flex flex-col shrink-0">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
              <Shield size={16} className="text-[#E11D48]" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-gray-800">Виртуальный член комитета</h1>
              <p className="text-[11px] text-gray-400">Анализ материалов заседания</p>
            </div>
          </div>
        </div>

        {/* Documents */}
        <div className="flex-1 overflow-y-auto px-3 py-3 custom-scrollbar">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              Материалы ({activeCommitteeDocs.length}/{committeeDocs.length})
            </p>
            <button onClick={handleUpload}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-[#E11D48] hover:bg-red-50 transition-colors">
              <Upload size={12} /> Загрузить
            </button>
            <input ref={fileInputRef} type="file" accept=".json,.pdf,.docx,.xlsx,.xls,.txt,.md,.csv" multiple
              onChange={handleFileChange} className="hidden" />
          </div>

          <div className="space-y-1">
            {committeeDocs.map(doc => {
              const Icon = FILE_ICONS[doc.file_type] || File;
              const isActive = doc.is_active !== false;
              const isToggling = togglingId === doc.id;
              return (
                <div key={doc.id}
                  className={`flex items-center gap-2 p-2 rounded-lg group transition-all ${
                    isActive ? 'hover:bg-gray-50' : 'opacity-50 hover:bg-gray-50'
                  }`}
                >
                  <Icon size={14} className={isActive ? 'text-gray-400 shrink-0' : 'text-gray-300 shrink-0'} />
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-medium truncate ${isActive ? 'text-gray-700' : 'text-gray-400 line-through'}`}>
                      {doc.original_name}
                    </p>
                    <div className="flex items-center gap-1.5">
                      <p className="text-[10px] text-gray-400">{formatSize(doc.size_bytes)}</p>
                      <span className={`inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0 rounded-full ${
                        isActive ? 'text-emerald-600 bg-emerald-50' : 'text-gray-400 bg-gray-100'
                      }`}>
                        <span className={`w-1 h-1 rounded-full ${isActive ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                        {isActive ? 'Акт.' : 'Скрыт'}
                      </span>
                    </div>
                  </div>
                  {/* Actions: View · Toggle · Delete */}
                  <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {/* View */}
                    <button onClick={() => handleView(doc)}
                      className="w-6 h-6 rounded hover:bg-gray-200 flex items-center justify-center"
                      title="Просмотреть">
                      <Search size={11} className="text-gray-400" />
                    </button>
                    {/* Toggle active/inactive */}
                    <button onClick={() => handleToggle(doc)} disabled={isToggling}
                      className={`w-6 h-6 rounded flex items-center justify-center ${
                        isActive ? 'hover:bg-amber-50' : 'hover:bg-emerald-50'
                      }`}
                      title={isActive ? 'Скрыть источник' : 'Показать источник'}>
                      {isToggling ? (
                        <div className="w-2.5 h-2.5 border border-gray-300 border-t-gray-500 rounded-full animate-spin" />
                      ) : isActive ? (
                        <EyeOff size={11} className="text-gray-300 hover:text-amber-500" />
                      ) : (
                        <Eye size={11} className="text-gray-300 hover:text-emerald-500" />
                      )}
                    </button>
                    {/* Delete (only user-uploaded) */}
                    {!doc.id.startsWith('src_') && (
                      <button onClick={() => handleDelete(doc)}
                        className="w-6 h-6 rounded hover:bg-red-50 flex items-center justify-center"
                        title="Удалить">
                        <Trash2 size={11} className="text-gray-300 hover:text-red-500" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Actions */}
          <div className="border-t border-gray-100 mt-4 pt-3">
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Быстрые действия
            </p>
            <div className="space-y-1">
              {QUICK_ACTIONS.map(action => {
                const Icon = action.icon;
                return (
                  <button key={action.id}
                    onClick={() => handleQuickAction(action.prompt)}
                    disabled={isStreaming}
                    className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors text-left">
                    <Icon size={14} className={action.color} />
                    <span>{action.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Right panel: Chat */}
      <div className="flex-1 flex flex-col">
        {/* Chat messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Shield size={48} className="mb-4 opacity-20" />
              <p className="text-sm font-medium text-gray-500">Готов к анализу</p>
              <p className="text-xs mt-1 text-center max-w-sm">
                Выберите быстрое действие слева или задайте свободный вопрос по материалам комитета
              </p>
            </div>
          ) : (
            <>
              {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="px-6 py-3 bg-white border-t border-gray-200">
          <div className="flex items-end gap-2 max-w-4xl mx-auto">
            <textarea ref={textareaRef} value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Задайте вопрос по материалам комитета..."
              rows={1}
              className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E11D48]/20 focus:border-[#E11D48]/40 transition-all"
            />
            {isStreaming ? (
              <button className="w-10 h-10 rounded-xl bg-gray-200 hover:bg-gray-300 flex items-center justify-center shrink-0">
                <Square size={16} className="text-gray-600" />
              </button>
            ) : (
              <button onClick={handleSend} disabled={!input.trim()}
                className="w-10 h-10 rounded-xl bg-[#E11D48] hover:bg-[#BE123C] disabled:bg-gray-200 disabled:cursor-not-allowed flex items-center justify-center shrink-0">
                <Send size={16} className={input.trim() ? 'text-white' : 'text-gray-400'} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Document viewer modal */}
      {(viewDoc || loadingContent) && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div className="flex items-center gap-3 min-w-0">
                <FileText size={18} className="text-[#E11D48] shrink-0" />
                <p className="text-sm font-semibold text-gray-800 truncate">{viewDoc?.doc.original_name || 'Загрузка...'}</p>
              </div>
              <button onClick={() => setViewDoc(null)} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center">
                <X size={16} className="text-gray-400" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {loadingContent ? (
                <div className="flex items-center justify-center py-10">
                  <div className="w-6 h-6 border-2 border-gray-300 border-t-[#E11D48] rounded-full animate-spin" />
                </div>
              ) : (
                <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap break-words leading-relaxed">
                  {viewDoc?.content || '[Пустой документ]'}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
