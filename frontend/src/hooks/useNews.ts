'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  fetchNewsFeed,
  fetchNewsDashboard,
  fetchNewsCompanies,
  refreshNews as apiRefreshNews,
  fetchNewsDigest,
} from '@/lib/api';
import { NewsArticle, NewsCompany, NewsDashboard, NewsDigest } from '@/lib/types';

export function useNews() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [companies, setCompanies] = useState<NewsCompany[]>([]);
  const [dashboard, setDashboard] = useState<NewsDashboard | null>(null);
  const [lastUpdated, setLastUpdated] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Digest
  const [digest, setDigest] = useState<NewsDigest | null>(null);
  const [isDigestLoading, setIsDigestLoading] = useState(false);
  const [showDigest, setShowDigest] = useState(false);

  // Filters (client-side)
  const [companyFilter, setCompanyFilter] = useState('all');
  const [sentimentFilter, setSentimentFilter] = useState('all');

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Load companies first (instant, static list)
      const companiesData = await fetchNewsCompanies();
      setCompanies(companiesData);

      // Then load feed + dashboard (may trigger DuckDuckGo + LLM on first call)
      const [feedResult, dashResult] = await Promise.allSettled([
        fetchNewsFeed(),
        fetchNewsDashboard(),
      ]);

      if (feedResult.status === 'fulfilled') {
        setArticles(feedResult.value.articles || []);
        setLastUpdated(feedResult.value.last_updated || '');
      }
      if (dashResult.status === 'fulfilled') {
        setDashboard(dashResult.value);
      }
    } catch (err) {
      console.error('[useNews] Load error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const data = await apiRefreshNews();
      setArticles(data.articles || []);
      setLastUpdated(data.last_updated || '');
      // Reload dashboard
      const dashData = await fetchNewsDashboard();
      setDashboard(dashData);
    } catch (err) {
      console.error('[useNews] Refresh error:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  const loadDigest = useCallback(async (period: 'day' | 'week') => {
    setIsDigestLoading(true);
    setShowDigest(true);
    try {
      const data = await fetchNewsDigest(period);
      setDigest(data);
    } catch (err) {
      console.error('[useNews] Digest error:', err);
    } finally {
      setIsDigestLoading(false);
    }
  }, []);

  // Client-side filtering
  const filteredArticles = useMemo(() => {
    return articles.filter((a) => {
      if (companyFilter !== 'all' && a.company_slug !== companyFilter) return false;
      if (sentimentFilter !== 'all' && a.sentiment !== sentimentFilter) return false;
      return true;
    });
  }, [articles, companyFilter, sentimentFilter]);

  // Group articles by company
  const groupedArticles = useMemo(() => {
    const groups: Record<string, { name: string; articles: NewsArticle[] }> = {};
    for (const a of filteredArticles) {
      if (!groups[a.company_slug]) {
        groups[a.company_slug] = { name: a.company_name, articles: [] };
      }
      groups[a.company_slug].articles.push(a);
    }
    // Sort by article count descending
    return Object.entries(groups).sort((a, b) => b[1].articles.length - a[1].articles.length);
  }, [filteredArticles]);

  // Load on mount
  useEffect(() => {
    loadData();
  }, [loadData]);

  return {
    articles: filteredArticles,
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
  };
}
