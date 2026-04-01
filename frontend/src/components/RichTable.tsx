'use client';

import React from 'react';
import { TableData } from '@/lib/types';

interface RichTableProps {
  data: TableData;
}

export default function RichTable({ data }: RichTableProps) {
  const { headers, rows, caption } = data;

  if (!headers || !rows) return (
    <div className="my-3 p-3 rounded-lg border border-gray-200 bg-gray-50 text-sm text-gray-400">
      Данные таблицы недоступны
    </div>
  );

  return (
    <div className="my-3 overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50">
            {headers.map((h, i) => (
              <th
                key={i}
                className="text-left px-4 py-2.5 font-semibold text-gray-700 border-b border-gray-200 whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr
              key={ri}
              className={ri % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}
            >
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className="px-4 py-2 text-gray-600 border-b border-gray-100 whitespace-nowrap"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {caption && (
        <p className="text-xs text-gray-400 px-4 py-2 bg-gray-50 border-t border-gray-100">
          {caption}
        </p>
      )}
    </div>
  );
}
