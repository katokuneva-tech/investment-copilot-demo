'use client';

import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { ChartData, ChartSeries } from '@/lib/types';

type ChartDataPoint = Record<string, string | number>;

interface NormalizedSeries extends ChartSeries {
  data_key?: string;
}

interface RichChartInnerProps {
  data: ChartData;
}

export default function RichChartInner({ data }: RichChartInnerProps) {
  const { chart_type, title, x_key, series: rawSeries, data: rawChartData } = data;

  if (!rawChartData || !rawSeries) return (
    <div className="my-3 p-3 rounded-lg border border-gray-200 bg-gray-50 text-sm text-gray-400">
      Данные графика недоступны
    </div>
  );

  // Normalize series: backend may send "data_key" instead of "key"
  const series: NormalizedSeries[] = rawSeries.map((s: ChartSeries & { data_key?: string }) => ({
    ...s,
    key: s.key || s.data_key || s.name?.toLowerCase().replace(/\s+/g, '_') || 'value',
  }));

  // Normalize chart data: parse string values to numbers, filter out non-numeric entries
  const chartData = rawChartData.map((point: ChartDataPoint) => {
    const normalized: ChartDataPoint = { [x_key]: point[x_key] };
    for (const s of series) {
      let val: string | number | undefined = point[s.key];
      if (val === undefined && s.data_key) {
        val = point[s.data_key];
      }
      if (typeof val === 'string') {
        if (val === 'н/д' || val === 'N/A' || val === '-') {
          normalized[s.key] = 0;
        } else {
          const cleaned = val.replace(/[+%\s]/g, '').replace(',', '.');
          const num = parseFloat(cleaned);
          normalized[s.key] = isNaN(num) ? 0 : num;
        }
      } else {
        normalized[s.key] = typeof val === 'number' ? val : 0;
      }
    }
    return normalized;
  });

  const ChartComponent = chart_type === 'line' ? LineChart : BarChart;

  return (
    <div className="my-3 p-4 bg-white rounded-lg border border-gray-200">
      {title && (
        <h4 className="text-sm font-semibold text-gray-700 mb-3">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <ChartComponent data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey={x_key}
            tick={{ fontSize: 12, fill: '#6B7280' }}
            axisLine={{ stroke: '#E5E7EB' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#6B7280' }}
            axisLine={{ stroke: '#E5E7EB' }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #E5E7EB',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          {series.map((s) =>
            chart_type === 'line' ? (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                stroke={s.color}
                strokeWidth={2}
                dot={{ r: 3, fill: s.color }}
              />
            ) : (
              <Bar
                key={s.key}
                dataKey={s.key}
                name={s.name}
                fill={s.color}
                radius={[4, 4, 0, 0]}
              />
            ),
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
}
