'use client';

import React, { useState } from 'react';
import { Brain, Wrench, CheckCircle, ChevronDown, ChevronRight, Zap } from 'lucide-react';
import { ThinkingStep } from '@/lib/types';

interface ThinkingStepsProps {
  steps: ThinkingStep[];
  isStreaming: boolean;
}

const STEP_CONFIG = {
  thinking: { icon: Brain, color: 'text-gray-400', bg: 'bg-gray-50', label: 'Думаю' },
  tool_call: { icon: Wrench, color: 'text-[#E11D48]', bg: 'bg-red-50', label: 'Инструмент' },
  tool_result: { icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-50', label: 'Результат' },
};

export default function ThinkingSteps({ steps, isStreaming }: ThinkingStepsProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Auto-collapse when streaming ends (answer arrived)
  const shouldExpand = isStreaming || isExpanded;

  if (steps.length === 0) return null;

  // Collapsed view
  if (!shouldExpand) {
    return (
      <button
        onClick={() => setIsExpanded(true)}
        className="flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-gray-600 transition-colors py-1 mb-2"
      >
        <Zap size={11} className="text-amber-400" />
        <span>Анализ за {steps.length} {steps.length === 1 ? 'шаг' : steps.length < 5 ? 'шага' : 'шагов'}</span>
        <ChevronRight size={11} />
      </button>
    );
  }

  return (
    <div className="mb-3">
      {/* Header */}
      {!isStreaming && (
        <button
          onClick={() => setIsExpanded(false)}
          className="flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-gray-600 transition-colors py-1 mb-1"
        >
          <Zap size={11} className="text-amber-400" />
          <span>Анализ за {steps.length} {steps.length === 1 ? 'шаг' : steps.length < 5 ? 'шага' : 'шагов'}</span>
          <ChevronDown size={11} />
        </button>
      )}

      {/* Steps */}
      <div className="space-y-1 pl-0.5">
        {steps.map((step, i) => {
          const config = STEP_CONFIG[step.type];
          const Icon = config.icon;
          const isLast = i === steps.length - 1;
          const isActive = isLast && isStreaming;

          return (
            <div
              key={i}
              className={`flex items-start gap-2 animate-fade-in-up ${isActive ? '' : ''}`}
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className={`w-4 h-4 rounded flex items-center justify-center shrink-0 mt-0.5 ${config.bg}`}>
                {isActive ? (
                  <div className="w-1.5 h-1.5 rounded-full bg-[#E11D48] animate-pulse" />
                ) : (
                  <Icon size={10} className={config.color} />
                )}
              </div>
              <span className={`text-[11px] leading-relaxed ${
                isActive ? 'text-gray-600 font-medium' : 'text-gray-400'
              }`}>
                {step.type === 'tool_call' && (
                  <code className="text-[10px] bg-gray-100 px-1 py-0.5 rounded font-mono">
                    {step.content}
                  </code>
                )}
                {step.type !== 'tool_call' && step.content}
              </span>
            </div>
          );
        })}

        {/* Pulsing indicator while streaming */}
        {isStreaming && (
          <div className="flex items-center gap-2 animate-fade-in-up">
            <div className="w-4 h-4 rounded flex items-center justify-center shrink-0 bg-red-50">
              <div className="w-1.5 h-1.5 rounded-full bg-[#E11D48] animate-pulse" />
            </div>
            <span className="text-[11px] text-gray-400 animate-pulse">
              {steps[steps.length - 1]?.type === 'tool_call' ? 'Обрабатываю...' : 'Думаю...'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
