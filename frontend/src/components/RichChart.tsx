'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { ChartData } from '@/lib/types';

const RichChartInner = dynamic(() => import('./RichChartInner'), {
  ssr: false,
  loading: () => (
    <div className="h-64 w-full flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
      <span className="text-sm text-gray-400">Загрузка графика...</span>
    </div>
  ),
});

interface RichChartProps {
  data: ChartData;
}

export default function RichChart({ data }: RichChartProps) {
  return <RichChartInner data={data} />;
}
