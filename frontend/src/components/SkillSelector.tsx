'use client';

import React from 'react';
import { Sparkles } from 'lucide-react';

const SUGGESTED_PROMPTS = [
  // Комплексный запрос — wow-эффект
  'Проанализируй портфель АФК: кто генерирует прибыль, кто убыточен, какие компании готовы к IPO и где основные риски',
  // Портфельная аналитика
  'Какая компания растёт по выручке быстрее всего?',
  'У кого самая высокая долговая нагрузка?',
  'Кто сможет заплатить дивиденды в этом году?',
  'IPO pipeline',
  // Инвестиционный анализ
  'Подготовь заключение по логистическому хабу',
];

interface SkillSelectorProps {
  onSelectSkill: (skillId: string) => void;
  onSendPrompt: (skillId: string, prompt: string) => void;
}

export default function SkillSelector({
  onSendPrompt,
}: SkillSelectorProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
      <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mb-5">
        <Sparkles size={28} className="text-[#E11D48]" />
      </div>
      <h2 className="text-2xl font-semibold text-gray-800 mb-1">
        Investment Intelligence Copilot
      </h2>
      <p className="text-gray-400 mb-8 text-center max-w-lg text-sm">
        AI-аналитик. Задайте любой вопрос по компаниям,
        инвестпроектам, рынкам или материалам комитета.
      </p>

      <div className="flex flex-wrap justify-center gap-2 max-w-2xl">
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onSendPrompt('auto', prompt)}
            className="text-[13px] px-4 py-2 bg-white hover:bg-red-50 hover:text-[#E11D48] text-gray-600 rounded-full transition-colors border border-gray-200 hover:border-[#E11D48]/30"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
