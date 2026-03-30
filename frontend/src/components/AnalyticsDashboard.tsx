'use client';

import React, { useState, useEffect } from 'react';
import { BarChart3, Clock, Users, AlertTriangle, RefreshCw } from 'lucide-react';
import { API_BASE_URL } from '@/lib/constants';

interface DashboardData {
  total_requests: number;
  last_24h: number;
  avg_response_ms: number;
  error_count: number;
  by_skill: Array<{ skill_id: string; count: number; avg_ms: number }>;
  by_user: Array<{ user_name: string; count: number; last_seen: string }>;
  recent: Array<{
    timestamp: string; user_name: string; skill_id: string;
    message: string; response_time_ms: number; provider: string; status: string;
  }>;
  hourly: Array<{ hour: string; count: number }>;
}

function StatCard({ icon: Icon, label, value, sub, color = 'text-gray-800' }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className="text-gray-400" />
        <span className="text-[11px] font-medium text-gray-400 uppercase">{label}</span>
      </div>
      <p className={`text-2xl font-semibold ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function AnalyticsDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('copilot_token');
      const res = await fetch(`${API_BASE_URL}/api/analytics/dashboard`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        setData(await res.json());
      }
    } catch (e) {
      console.error('Analytics fetch failed:', e);
    }
    setIsLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div className="flex-1 flex flex-col h-screen bg-[#F9FAFB]">
      {/* Header */}
      <div className="px-6 py-3 border-b border-gray-200 bg-white flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
            <BarChart3 size={16} className="text-[#E11D48]" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-gray-800">Аналитика</h1>
            <p className="text-xs text-gray-400">Мониторинг запросов и качества</p>
          </div>
        </div>
        <button onClick={fetchData} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-gray-500 hover:bg-gray-100 transition-colors">
          <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
          Обновить
        </button>
      </div>

      {isLoading && !data ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-gray-300 border-t-[#E11D48] rounded-full animate-spin" />
        </div>
      ) : data ? (
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="max-w-5xl space-y-6">
            {/* Stats cards */}
            <div className="grid grid-cols-4 gap-4">
              <StatCard icon={BarChart3} label="Всего запросов" value={data.total_requests} sub={`${data.last_24h} за 24ч`} />
              <StatCard icon={Clock} label="Ср. время ответа" value={`${(data.avg_response_ms / 1000).toFixed(1)}с`} sub={`${data.avg_response_ms}мс`} />
              <StatCard icon={Users} label="Пользователей" value={data.by_user.length} />
              <StatCard icon={AlertTriangle} label="Ошибки" value={data.error_count} color={data.error_count > 0 ? 'text-red-500' : 'text-emerald-500'} />
            </div>

            {/* By skill */}
            <div className="bg-white rounded-xl border border-gray-100 p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">По скиллам</h3>
              <div className="space-y-2">
                {data.by_skill.map(s => (
                  <div key={s.skill_id} className="flex items-center gap-3">
                    <span className="text-xs text-gray-600 w-40 truncate">{s.skill_id}</span>
                    <div className="flex-1 h-5 bg-gray-50 rounded-full overflow-hidden">
                      <div className="h-full bg-[#E11D48]/20 rounded-full" style={{ width: `${Math.min(100, (s.count / Math.max(1, data.total_requests)) * 100)}%` }} />
                    </div>
                    <span className="text-xs text-gray-500 w-16 text-right">{s.count} req</span>
                    <span className="text-[10px] text-gray-400 w-16 text-right">{(s.avg_ms / 1000).toFixed(1)}с</span>
                  </div>
                ))}
              </div>
            </div>

            {/* By user */}
            <div className="bg-white rounded-xl border border-gray-100 p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">По пользователям</h3>
              <div className="space-y-2">
                {data.by_user.map(u => (
                  <div key={u.user_name} className="flex items-center gap-3 text-xs">
                    <span className="text-gray-600 w-32 truncate font-medium">{u.user_name}</span>
                    <span className="text-gray-400">{u.count} запросов</span>
                    <span className="text-gray-300 ml-auto">{new Date(u.last_seen).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent requests */}
            <div className="bg-white rounded-xl border border-gray-100 p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Последние запросы</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2 px-2 text-gray-400 font-medium">Время</th>
                      <th className="text-left py-2 px-2 text-gray-400 font-medium">Пользователь</th>
                      <th className="text-left py-2 px-2 text-gray-400 font-medium">Скилл</th>
                      <th className="text-left py-2 px-2 text-gray-400 font-medium">Запрос</th>
                      <th className="text-right py-2 px-2 text-gray-400 font-medium">Время</th>
                      <th className="text-left py-2 px-2 text-gray-400 font-medium">Модель</th>
                      <th className="text-left py-2 px-2 text-gray-400 font-medium">Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent.map((r, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-2 px-2 text-gray-400 whitespace-nowrap">
                          {new Date(r.timestamp).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="py-2 px-2 text-gray-600">{r.user_name}</td>
                        <td className="py-2 px-2 text-gray-500">{r.skill_id}</td>
                        <td className="py-2 px-2 text-gray-700 max-w-[200px] truncate">{r.message}</td>
                        <td className="py-2 px-2 text-gray-500 text-right">{(r.response_time_ms / 1000).toFixed(1)}с</td>
                        <td className="py-2 px-2">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${r.provider === 'claude' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'}`}>
                            {r.provider || '—'}
                          </span>
                        </td>
                        <td className="py-2 px-2">
                          <span className={`w-1.5 h-1.5 rounded-full inline-block ${r.status === 'ok' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          Не удалось загрузить аналитику
        </div>
      )}
    </div>
  );
}
