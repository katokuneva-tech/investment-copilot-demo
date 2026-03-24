'use client';

import React from 'react';
import { FileText } from 'lucide-react';
import { SourceData } from '@/lib/types';

interface SourceCitationProps {
  sources: SourceData[];
}

export default function SourceCitation({ sources }: SourceCitationProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="my-3">
      <p className="text-xs font-medium text-gray-500 mb-2">Источники:</p>
      <div className="flex flex-wrap gap-2">
        {sources.map((source, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1.5 bg-gray-100 text-gray-600 rounded-full px-3 py-1 text-xs"
          >
            <FileText size={12} className="text-gray-400" />
            {source.title}
          </span>
        ))}
      </div>
    </div>
  );
}
