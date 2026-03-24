import { Skill } from './types';

export const SKILLS: Skill[] = [
  {
    id: 'portfolio_analytics',
    name: 'Портфельная аналитика',
    description: 'Анализ портфеля компаний: финансовые показатели, динамика, сравнения',
    icon: 'BarChart3',
    suggestedPrompts: [
      'Покажи обзор портфеля',
      'Кто растет быстрее всех?',
      'Какая долговая нагрузка?',
    ],
  },
  {
    id: 'investment_analysis',
    name: 'Инвестиционный анализ',
    description: 'Подготовка инвестиционных заключений и анализ проектов',
    icon: 'FileText',
    suggestedPrompts: [
      'Подготовь заключение по логистическому хабу',
      'Анализ инвестпроекта',
    ],
  },
  {
    id: 'market_research',
    name: 'Исследование рынков',
    description: 'Обзоры рынков, тренды, конкурентный анализ',
    icon: 'TrendingUp',
    suggestedPrompts: [
      'Исследуй рынок складской недвижимости',
      'Анализ рынка логистики',
    ],
  },
  {
    id: 'benchmarking',
    name: 'Бенчмаркинг',
    description: 'Сравнение компаний портфеля с публичными аналогами по мультипликаторам',
    icon: 'GitCompare',
    suggestedPrompts: [
      'Сравни компании портфеля с аналогами',
      'Бенчмаркинг по мультипликаторам',
    ],
  },
  {
    id: 'committee_advisor',
    name: 'Советник комитета',
    description: 'Поиск противоречий, оценка рисков, рекомендации по сделкам',
    icon: 'Shield',
    suggestedPrompts: [
      'Найди противоречия в материалах',
      'Каковы риски сделки?',
      'Стоит ли входить в проект?',
    ],
  },
];

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
