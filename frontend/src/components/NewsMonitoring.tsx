'use client';

import React from 'react';
import {
  Newspaper, RefreshCw, BookOpen, ExternalLink,
  TrendingUp, TrendingDown, Minus, AlertTriangle,
  BarChart3, X,
} from 'lucide-react';
import { useNews } from '@/hooks/useNews';
import { NewsArticle } from '@/lib/types';
import ReactMarkdown from 'react-markdown';

const SENTIMENT_STYLES = {
  positive: { bg: 'bg-emerald-50', text: 'text-emerald-600', label: 'Позитив', icon: TrendingUp },
  negative: { bg: 'bg-red-50', text: 'text-red-600', label: 'Негатив', icon: TrendingDown },
  neutral: { bg: 'bg-gray-50', text: 'text-gray-500', label: 'Нейтрал', icon: Minus },
};

const ALERT_LABELS: Record<string, string> = {
  ipo: 'IPO',
  management: 'Менеджмент',
  legal: 'Суд/иск',
  rating: 'Рейтинг',
  deal: 'Сделка',
  debt: 'Долг',
  regulatory: 'Регулятор',
};

function StatCard({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4 flex flex-col items-center">
      <span className={`text-2xl font-bold ${color}`}>{value}</span>
      <span className="text-xs text-gray-500 mt-1">{label}</span>
    </div>
  );
}

function SentimentBar({ name, positive, negative, neutral, total }: {
  name: string; positive: number; negative: number; neutral: number; total: number;
}) {
  const pPct = total ? Math.round((positive / total) * 100) : 0;
  const nPct = total ? Math.round((negative / total) * 100) : 0;
  const neuPct = 100 - pPct - nPct;

  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-24 text-gray-700 truncate font-medium">{name}</span>
      <div className="flex-1 flex h-4 rounded-full overflow-hidden bg-gray-100">
        {pPct > 0 && <div className="bg-emerald-400 transition-all" style={{ width: `${pPct}%` }} />}
        {neuPct > 0 && <div className="bg-gray-300 transition-all" style={{ width: `${neuPct}%` }} />}
        {nPct > 0 && <div className="bg-red-400 transition-all" style={{ width: `${nPct}%` }} />}
      </div>
      <span className="w-6 text-right text-gray-400">{total}</span>
    </div>
  );
}

function ArticleCard({ article }: { article: NewsArticle }) {
  const style = SENTIMENT_STYLES[article.sentiment] || SENTIMENT_STYLES.neutral;
  const Icon = style.icon;

  return (
    <div className="bg-white rounded-lg border border-gray-100 p-3 hover:border-gray-200 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-gray-800 hover:text-[#E11D48] transition-colors flex-1 leading-snug"
        >
          {article.title}
          <ExternalLink size={10} className="inline ml-1 opacity-40" />
        </a>
        <span className={`shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${style.bg} ${style.text}`}>
          <Icon size={10} />
          {style.label}
        </span>
      </div>

      <div className="flex items-center gap-2 mt-1.5 text-[11px] text-gray-400">
        <span>{article.source}</span>
        {article.published_approx && (
          <>
            <span>·</span>
            <span>{article.published_approx}</span>
          </>
        )}
      </div>

      {article.summary && (
        <p className="text-xs text-gray-600 mt-2 leading-relaxed">{article.summary}</p>
      )}

      {article.portfolio_impact && (
        <div className="mt-2 flex items-center gap-1.5 text-[11px] text-blue-600 bg-blue-50 rounded px-2 py-1">
          <BarChart3 size={11} />
          <span className="font-medium">{article.portfolio_impact.metric}:</span>
          <span>{article.portfolio_impact.context}</span>
        </div>
      )}

      {article.alert_type && (
        <div className="mt-2 flex items-center gap-1.5 text-[11px] text-amber-700 bg-amber-50 rounded px-2 py-1">
          <AlertTriangle size={11} />
          <span className="font-medium">{ALERT_LABELS[article.alert_type] || article.alert_type}</span>
        </div>
      )}
    </div>
  );
}

export default function NewsMonitoring() {
  const {
    groupedArticles,
    companies,
    dashboard,
    lastUpdated,
    isLoading,
    isRefreshing,
    companyFilter,
    setCompanyFilter,
    sentimentFilter,
    setSentimentFilter,
    refresh,
    digest,
    isDigestLoading,
    showDigest,
    setShowDigest,
    loadDigest,
  } = useNews();

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-100 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Newspaper size={20} className="text-[#E11D48]" />
          <h1 className="text-lg font-semibold text-gray-800">Мониторинг новостей</h1>
          {lastUpdated && (
            <span className="text-[11px] text-gray-400 ml-2">Обновлено: {lastUpdated}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => loadDigest('day')}
            disabled={isDigestLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            <BookOpen size={13} />
            Дайджест
          </button>
          <button
            onClick={refresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-[#E11D48] hover:bg-[#BE123C] rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
            {isRefreshing ? 'Обновляю...' : 'Обновить'}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <RefreshCw size={24} className="animate-spin text-[#E11D48] mx-auto mb-3" />
              <p className="text-sm text-gray-500">Загружаю новости по портфелю...</p>
              <p className="text-xs text-gray-400 mt-1">DuckDuckGo + AI-анализ</p>
            </div>
          </div>
        ) : (
          <div className="px-6 py-4 space-y-4">
            {/* Dashboard */}
            {dashboard && (
              <>
                {/* Stat Cards */}
                <div className="grid grid-cols-4 gap-3">
                  <StatCard value={dashboard.total} label="Всего" color="text-gray-800" />
                  <StatCard value={dashboard.positive} label="Позитивных" color="text-emerald-600" />
                  <StatCard value={dashboard.negative} label="Негативных" color="text-red-600" />
                  <StatCard value={dashboard.neutral} label="Нейтральных" color="text-gray-500" />
                </div>

                {/* Charts + Alerts row */}
                <div className="grid grid-cols-2 gap-3">
                  {/* Sentiment by company */}
                  <div className="bg-white rounded-xl border border-gray-100 p-4">
                    <h3 className="text-xs font-semibold text-gray-600 mb-3">Sentiment по компаниям</h3>
                    <div className="space-y-2">
                      {dashboard.sentiment_by_company.slice(0, 8).map((c) => (
                        <SentimentBar
                          key={c.slug}
                          name={c.name}
                          positive={c.positive}
                          negative={c.negative}
                          neutral={c.neutral}
                          total={c.total}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Alerts */}
                  <div className="bg-white rounded-xl border border-gray-100 p-4">
                    <h3 className="text-xs font-semibold text-gray-600 mb-3">
                      Алерты ({dashboard.alerts.length})
                    </h3>
                    {dashboard.alerts.length === 0 ? (
                      <p className="text-xs text-gray-400">Нет активных алертов</p>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {dashboard.alerts.map((alert) => (
                          <div
                            key={alert.id}
                            className={`flex items-start gap-2 text-xs p-2 rounded-lg ${
                              alert.severity === 'high' ? 'bg-red-50' : 'bg-amber-50'
                            }`}
                          >
                            <AlertTriangle
                              size={12}
                              className={`shrink-0 mt-0.5 ${
                                alert.severity === 'high' ? 'text-red-500' : 'text-amber-500'
                              }`}
                            />
                            <div>
                              <span className="font-medium text-gray-700">
                                {alert.company_name}: {ALERT_LABELS[alert.alert_type] || alert.alert_type}
                              </span>
                              <p className="text-gray-500 mt-0.5 line-clamp-2">{alert.description}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* Filters */}
            <div className="flex items-center gap-3 pt-2">
              <select
                value={companyFilter}
                onChange={(e) => setCompanyFilter(e.target.value)}
                className="text-xs border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-[#E11D48]/20"
              >
                <option value="all">Все компании</option>
                {companies.map((c) => (
                  <option key={c.slug} value={c.slug}>{c.name}</option>
                ))}
              </select>

              <div className="flex gap-1">
                {(['all', 'positive', 'neutral', 'negative'] as const).map((s) => {
                  const labels: Record<string, string> = {
                    all: 'Все',
                    positive: 'Позитив',
                    neutral: 'Нейтрал',
                    negative: 'Негатив',
                  };
                  const colors: Record<string, string> = {
                    all: sentimentFilter === 'all' ? 'bg-[#E11D48] text-white' : 'bg-gray-100 text-gray-600',
                    positive: sentimentFilter === 'positive' ? 'bg-emerald-500 text-white' : 'bg-gray-100 text-gray-600',
                    neutral: sentimentFilter === 'neutral' ? 'bg-gray-500 text-white' : 'bg-gray-100 text-gray-600',
                    negative: sentimentFilter === 'negative' ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-600',
                  };
                  return (
                    <button
                      key={s}
                      onClick={() => setSentimentFilter(s)}
                      className={`px-2.5 py-1 text-[11px] font-medium rounded-full transition-colors ${colors[s]}`}
                    >
                      {labels[s]}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* News Feed — grouped by company */}
            <div className="space-y-4 pb-8">
              {groupedArticles.length === 0 ? (
                <div className="text-center py-12 text-sm text-gray-400">
                  Нет новостей для отображения
                </div>
              ) : (
                groupedArticles.map(([slug, group]) => (
                  <div key={slug}>
                    <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                      {group.name}
                      <span className="text-[11px] font-normal text-gray-400">
                        ({group.articles.length})
                      </span>
                    </h2>
                    <div className="space-y-2">
                      {group.articles.map((article) => (
                        <ArticleCard key={article.id} article={article} />
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Digest Side Panel */}
      {showDigest && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/20" onClick={() => setShowDigest(false)} />
          <div className="relative w-full max-w-lg bg-white shadow-2xl h-full overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BookOpen size={16} className="text-[#E11D48]" />
                <h2 className="text-sm font-semibold text-gray-800">AI-дайджест</h2>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => loadDigest('day')}
                  className={`px-2.5 py-1 text-[11px] rounded-full transition-colors ${
                    digest?.period === 'day' ? 'bg-[#E11D48] text-white' : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  За день
                </button>
                <button
                  onClick={() => loadDigest('week')}
                  className={`px-2.5 py-1 text-[11px] rounded-full transition-colors ${
                    digest?.period === 'week' ? 'bg-[#E11D48] text-white' : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  За неделю
                </button>
                <button onClick={() => setShowDigest(false)} className="text-gray-400 hover:text-gray-600">
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="px-5 py-4">
              {isDigestLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-center">
                    <RefreshCw size={20} className="animate-spin text-[#E11D48] mx-auto mb-2" />
                    <p className="text-xs text-gray-500">Генерирую аналитический дайджест...</p>
                  </div>
                </div>
              ) : digest ? (
                <div className="prose prose-sm max-w-none text-gray-700">
                  <ReactMarkdown>{digest.digest}</ReactMarkdown>
                  <div className="mt-4 text-[11px] text-gray-400 border-t border-gray-100 pt-3">
                    Проанализировано новостей: {digest.article_count} · {digest.generated_at}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-400 text-center py-8">
                  Нажмите «За день» или «За неделю» для генерации
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
