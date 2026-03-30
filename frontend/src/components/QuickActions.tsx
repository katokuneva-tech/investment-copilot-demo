'use client';

import React from 'react';
import {
  Search, AlertTriangle, ClipboardCheck, FileEdit, HelpCircle,
  ScrollText, FileText, Zap,
} from 'lucide-react';

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

interface QuickActionsProps {
  isStreaming: boolean;
  onAction: (prompt: string) => void;
}

export { QUICK_ACTIONS };

export default function QuickActions({ isStreaming, onAction }: QuickActionsProps) {
  return (
    <div className="border-t border-gray-100 mt-4 pt-3">
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Быстрые действия
      </p>
      <div className="space-y-1">
        {QUICK_ACTIONS.map(action => {
          const Icon = action.icon;
          return (
            <button key={action.id}
              onClick={() => onAction(action.prompt)}
              disabled={isStreaming}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors text-left">
              <Icon size={14} className={action.color} />
              <span>{action.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
