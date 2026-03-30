'use client';

import React from 'react';
import { Shield } from 'lucide-react';

export default function PreAnalysis() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-400">
      <Shield size={48} className="mb-4 opacity-20" />
      <p className="text-sm font-medium text-gray-500">Готов к анализу</p>
      <p className="text-xs mt-1 text-center max-w-sm">
        Выберите быстрое действие слева или задайте свободный вопрос по материалам комитета
      </p>
    </div>
  );
}
