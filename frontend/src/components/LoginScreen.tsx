'use client';

import React, { useState, useEffect } from 'react';
import { Lock, ArrowRight, KeyRound, Check } from 'lucide-react';

interface LoginScreenProps {
  onLogin: (token: string, name: string, role: string) => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Change password step
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPassword2, setNewPassword2] = useState('');
  const [changeError, setChangeError] = useState('');
  const [changeSuccess, setChangeSuccess] = useState(false);
  const [isChanging, setIsChanging] = useState(false);

  // Auto-fill from URL param ?key=xxx
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const key = params.get('key');
    if (key) {
      setPassword(key);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const handleLogin = async () => {
    if (!password.trim()) return;
    setIsLoading(true);
    setError('');

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: password.trim() }),
      });
      const data = await res.json();

      if (data.error) {
        setError('Неверный пароль');
      } else {
        localStorage.setItem('copilot_token', data.token);
        localStorage.setItem('copilot_user', data.name);
        localStorage.setItem('copilot_role', data.role);
        onLogin(data.token, data.name, data.role);
      }
    } catch {
      setError('Ошибка подключения к серверу');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (!oldPassword.trim() || !newPassword.trim()) return;
    if (newPassword !== newPassword2) {
      setChangeError('Пароли не совпадают');
      return;
    }
    if (newPassword.length < 4) {
      setChangeError('Минимум 4 символа');
      return;
    }

    setIsChanging(true);
    setChangeError('');

    try {
      const res = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_password: oldPassword.trim(), new_password: newPassword.trim() }),
      });
      const data = await res.json();

      if (data.error) {
        setChangeError(data.error);
      } else {
        setChangeSuccess(true);
        localStorage.setItem('copilot_token', data.token);
        localStorage.setItem('copilot_user', data.name);
        localStorage.setItem('copilot_role', data.role);
        setTimeout(() => onLogin(data.token, data.name, data.role), 1500);
      }
    } catch {
      setChangeError('Ошибка подключения');
    } finally {
      setIsChanging(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (showChangePassword) handleChangePassword();
      else handleLogin();
    }
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4">
            {showChangePassword ? (
              <KeyRound size={28} className="text-[#E11D48]" />
            ) : (
              <Lock size={28} className="text-[#E11D48]" />
            )}
          </div>
          <h1 className="text-xl font-semibold text-gray-800">
            AFK Investment Copilot
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            {showChangePassword ? 'Смена пароля' : 'AI-аналитик портфеля АФК Система'}
          </p>
        </div>

        {!showChangePassword ? (
          /* ── Login form ── */
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
            <label className="block text-xs font-medium text-gray-500 mb-2">
              Пароль доступа
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Введите пароль"
              autoFocus
              className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E11D48]/20 focus:border-[#E11D48]/40 transition-all"
            />

            {error && <p className="text-xs text-red-500 mt-2">{error}</p>}

            <button
              onClick={handleLogin}
              disabled={isLoading || !password.trim()}
              className="w-full mt-4 py-3 rounded-xl bg-[#E11D48] hover:bg-[#BE123C] disabled:bg-gray-200 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Войти <ArrowRight size={14} /></>
              )}
            </button>

            <button
              onClick={() => setShowChangePassword(true)}
              className="w-full mt-3 text-[11px] text-gray-400 hover:text-[#E11D48] transition-colors"
            >
              Сменить пароль
            </button>
          </div>
        ) : changeSuccess ? (
          /* ── Success ── */
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm text-center">
            <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center mx-auto mb-3">
              <Check size={24} className="text-emerald-500" />
            </div>
            <p className="text-sm font-medium text-gray-800">Пароль изменён</p>
            <p className="text-xs text-gray-400 mt-1">Входим...</p>
          </div>
        ) : (
          /* ── Change password form ── */
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
            <label className="block text-xs font-medium text-gray-500 mb-2">
              Текущий пароль
            </label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Введите текущий пароль"
              autoFocus
              className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E11D48]/20 focus:border-[#E11D48]/40 transition-all"
            />

            <label className="block text-xs font-medium text-gray-500 mb-2 mt-4">
              Новый пароль
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Придумайте новый пароль"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E11D48]/20 focus:border-[#E11D48]/40 transition-all"
            />

            <label className="block text-xs font-medium text-gray-500 mb-2 mt-4">
              Повторите новый пароль
            </label>
            <input
              type="password"
              value={newPassword2}
              onChange={(e) => setNewPassword2(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Повторите пароль"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E11D48]/20 focus:border-[#E11D48]/40 transition-all"
            />

            {changeError && <p className="text-xs text-red-500 mt-2">{changeError}</p>}

            <button
              onClick={handleChangePassword}
              disabled={isChanging || !oldPassword.trim() || !newPassword.trim() || !newPassword2.trim()}
              className="w-full mt-4 py-3 rounded-xl bg-[#E11D48] hover:bg-[#BE123C] disabled:bg-gray-200 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              {isChanging ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Сменить пароль'
              )}
            </button>

            <button
              onClick={() => { setShowChangePassword(false); setChangeError(''); }}
              className="w-full mt-3 text-[11px] text-gray-400 hover:text-[#E11D48] transition-colors"
            >
              Назад к входу
            </button>
          </div>
        )}

        <p className="text-center text-[11px] text-gray-300 mt-6">
          MWS Capital · v1.0 MVP
        </p>
      </div>
    </div>
  );
}
