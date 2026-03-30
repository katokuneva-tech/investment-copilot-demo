'use client';

import React, { useRef, useState } from 'react';
import {
  Database, Upload, Trash2, FileText, FileSpreadsheet, File,
  Eye, EyeOff, X, Search,
} from 'lucide-react';
import { useDocuments } from '@/hooks/useDocuments';
import { KBDocument } from '@/lib/types';
import { fetchDocumentContent } from '@/lib/api';

const FILE_ICONS: Record<string, React.ElementType> = {
  json: FileText,
  pdf: FileText,
  docx: FileText,
  md: FileText,
  txt: FileText,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
  csv: FileSpreadsheet,
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}

export default function KnowledgeBase() {
  const { documents, isLoading, upload, remove, toggle } = useDocuments();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [viewDoc, setViewDoc] = useState<{ doc: KBDocument; content: string } | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const handleUpload = () => fileInputRef.current?.click();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    for (const file of Array.from(files)) {
      await upload(file);
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDelete = (doc: KBDocument) => {
    const label = doc.id === 'kb_default'
      ? `Удалить системный документ "${doc.original_name}"? Это удалит базу знаний АФК Система.`
      : `Удалить "${doc.original_name}"?`;
    if (window.confirm(label)) {
      remove(doc.id);
    }
  };

  const handleToggle = async (doc: KBDocument) => {
    setTogglingId(doc.id);
    await toggle(doc.id);
    setTogglingId(null);
  };

  const handleView = async (doc: KBDocument) => {
    setLoadingContent(true);
    try {
      const data = await fetchDocumentContent(doc.id);
      setViewDoc({ doc: data.document, content: data.content });
    } catch (err) {
      console.error('Failed to load content:', err);
    } finally {
      setLoadingContent(false);
    }
  };

  const activeCount = documents.filter(d => d.is_active !== false).length;

  return (
    <div className="flex-1 flex flex-col h-screen bg-[#F9FAFB]">
      {/* Header */}
      <div className="px-6 py-3 border-b border-gray-200 bg-white flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
            <Database size={16} className="text-[#E11D48]" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-gray-800">База знаний</h1>
            <p className="text-xs text-gray-400">
              {activeCount} из {documents.length} активн{activeCount === 1 ? 'ый' : 'ых'}
            </p>
          </div>
        </div>
        <button
          onClick={handleUpload}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#E11D48] hover:bg-[#BE123C] text-white text-sm font-medium transition-colors"
        >
          <Upload size={14} />
          Загрузить
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,.pdf,.docx,.xlsx,.xls,.txt,.md,.csv"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-gray-300 border-t-[#E11D48] rounded-full animate-spin" />
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <Database size={48} className="mb-4 opacity-30" />
            <p className="text-sm">Нет загруженных документов</p>
            <p className="text-xs mt-1">Загрузите JSON, PDF, DOCX, XLSX, TXT или MD файлы</p>
          </div>
        ) : (
          <div className="space-y-2 max-w-4xl">
            {documents.map((doc) => {
              const Icon = FILE_ICONS[doc.file_type] || File;
              const isSystem = doc.id === 'kb_default';
              const isActive = doc.is_active !== false;
              const isToggling = togglingId === doc.id;
              return (
                <div
                  key={doc.id}
                  className={`flex items-center gap-4 p-4 bg-white rounded-xl border transition-all ${
                    isActive
                      ? 'border-gray-100 hover:border-gray-200'
                      : 'border-gray-100 opacity-50'
                  }`}
                >
                  {/* File icon */}
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                    isActive
                      ? isSystem ? 'bg-red-50' : 'bg-gray-50'
                      : 'bg-gray-100'
                  }`}>
                    <Icon
                      size={18}
                      className={isActive
                        ? isSystem ? 'text-[#E11D48]' : 'text-gray-400'
                        : 'text-gray-300'
                      }
                    />
                  </div>

                  {/* Meta */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className={`text-sm font-medium truncate ${isActive ? 'text-gray-800' : 'text-gray-400 line-through'}`}>
                        {doc.original_name}
                      </p>
                      {isSystem && (
                        <span className="shrink-0 text-[10px] font-medium text-[#E11D48] bg-red-50 px-2 py-0.5 rounded-full">
                          Системный
                        </span>
                      )}
                      <span className="shrink-0 text-[10px] font-medium text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full uppercase">
                        {doc.file_type}
                      </span>
                      {/* Active / Inactive badge */}
                      <span className={`shrink-0 inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        isActive
                          ? 'text-emerald-700 bg-emerald-50'
                          : 'text-gray-400 bg-gray-100'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                        {isActive ? 'Активный' : 'Неактивный'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {formatSize(doc.size_bytes)} · {formatDate(doc.uploaded_at)}
                    </p>
                  </div>

                  {/* Actions: View · Toggle · Delete */}
                  <div className="flex items-center gap-1 shrink-0">
                    {/* View content */}
                    <button
                      onClick={() => handleView(doc)}
                      className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center transition-colors group"
                      title="Просмотреть"
                    >
                      <Search size={14} className="text-gray-300 group-hover:text-gray-600" />
                    </button>
                    {/* Toggle active/inactive */}
                    <button
                      onClick={() => handleToggle(doc)}
                      disabled={isToggling}
                      className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors group ${
                        isActive ? 'hover:bg-amber-50' : 'hover:bg-emerald-50'
                      }`}
                      title={isActive ? 'Скрыть источник' : 'Показать источник'}
                    >
                      {isToggling ? (
                        <div className="w-3.5 h-3.5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin" />
                      ) : isActive ? (
                        <EyeOff size={14} className="text-gray-300 group-hover:text-amber-500" />
                      ) : (
                        <Eye size={14} className="text-gray-300 group-hover:text-emerald-500" />
                      )}
                    </button>
                    {/* Delete */}
                    <button
                      onClick={() => handleDelete(doc)}
                      className="w-8 h-8 rounded-lg hover:bg-red-50 flex items-center justify-center transition-colors group"
                      title="Удалить"
                    >
                      <Trash2 size={14} className="text-gray-300 group-hover:text-[#E11D48]" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Content viewer modal */}
      {(viewDoc || loadingContent) && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div className="flex items-center gap-3 min-w-0">
                <FileText size={18} className="text-[#E11D48] shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-800 truncate">
                    {viewDoc?.doc.original_name || 'Загрузка...'}
                  </p>
                  {viewDoc && (
                    <p className="text-xs text-gray-400">
                      {formatSize(viewDoc.doc.size_bytes)} · {viewDoc.doc.file_type.toUpperCase()}
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={() => setViewDoc(null)}
                className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center"
              >
                <X size={16} className="text-gray-400" />
              </button>
            </div>
            {/* Modal body */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {loadingContent ? (
                <div className="flex items-center justify-center py-10">
                  <div className="w-6 h-6 border-2 border-gray-300 border-t-[#E11D48] rounded-full animate-spin" />
                </div>
              ) : viewDoc ? (
                <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap break-words leading-relaxed">
                  {viewDoc.content || '[Пустой документ]'}
                </pre>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
