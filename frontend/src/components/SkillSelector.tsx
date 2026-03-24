'use client';

import React from 'react';
import {
  BarChart3,
  FileText,
  TrendingUp,
  GitCompare,
  Shield,
} from 'lucide-react';
import { SKILLS } from '@/lib/constants';

const ICON_MAP: Record<string, React.ElementType> = {
  BarChart3,
  FileText,
  TrendingUp,
  GitCompare,
  Shield,
};

interface SkillSelectorProps {
  onSelectSkill: (skillId: string) => void;
  onSendPrompt: (skillId: string, prompt: string) => void;
}

export default function SkillSelector({
  onSelectSkill,
  onSendPrompt,
}: SkillSelectorProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
      <h2 className="text-2xl font-semibold text-gray-800 mb-1">
        Добро пожаловать
      </h2>
      <p className="text-gray-500 mb-8 text-center max-w-md">
        Выберите инструмент для начала работы или задайте вопрос
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-3xl">
        {SKILLS.map((skill) => {
          const Icon = ICON_MAP[skill.icon] || FileText;
          return (
            <div
              key={skill.id}
              className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md hover:border-gray-300 transition-all cursor-pointer group"
              onClick={() => onSelectSkill(skill.id)}
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-9 h-9 rounded-lg bg-red-50 flex items-center justify-center group-hover:bg-red-100 transition-colors">
                  <Icon size={18} className="text-[#E11D48]" />
                </div>
                <h3 className="font-medium text-gray-800 text-sm">
                  {skill.name}
                </h3>
              </div>
              <p className="text-xs text-gray-500 mb-3 leading-relaxed">
                {skill.description}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {skill.suggestedPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSendPrompt(skill.id, prompt);
                    }}
                    className="text-[11px] px-2.5 py-1 bg-gray-50 hover:bg-red-50 hover:text-[#E11D48] text-gray-600 rounded-full transition-colors border border-gray-100"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
