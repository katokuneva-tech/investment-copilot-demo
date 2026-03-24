'use client';

import React from 'react';
import { FileDown } from 'lucide-react';
import { PdfLinkData } from '@/lib/types';
import { getReportUrl } from '@/lib/api';

interface PdfDownloadProps {
  data: PdfLinkData;
}

export default function PdfDownload({ data }: PdfDownloadProps) {
  const { report_id, title, description } = data;

  const handleClick = () => {
    window.open(getReportUrl(report_id), '_blank');
  };

  return (
    <button
      onClick={handleClick}
      className="my-3 flex items-center gap-3 w-full max-w-md p-3 rounded-lg border border-gray-200 hover:border-[#E11D48]/30 hover:bg-red-50/50 transition-all text-left group"
    >
      <div className="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center shrink-0 group-hover:bg-red-100 transition-colors">
        <FileDown size={20} className="text-[#E11D48]" />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">
          {title}
        </p>
        {description && (
          <p className="text-xs text-gray-500 mt-0.5">{description}</p>
        )}
      </div>
    </button>
  );
}
