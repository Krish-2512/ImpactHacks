import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { useAutoTranslate } from '../../hooks/useAutoTranslate'
import { getUnreadCount, connectNotificationWS } from '../../api/notifications'

const LANGUAGES = [
  { code: 'en',  label: 'English',    native: 'English' },
  { code: 'hi',  label: 'Hindi',      native: 'हिंदी' },
  { code: 'as',  label: 'Assamese',   native: 'অসমীয়া' },
  { code: 'bn',  label: 'Bengali',    native: 'বাংলা' },
  { code: 'ne',  label: 'Nepali',     native: 'नेपाली' },
  { code: 'mni', label: 'Manipuri',   native: 'মণিপুরী' },
  { code: 'lus', label: 'Mizo',       native: 'Mizo ṭawng' },
]

function LanguageDropdown() {
  const { i18n } = useTranslation()
  const { isTranslating, error } = useAutoTranslate()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const current = LANGUAGES.find(l => l.code === i18n.language) || LANGUAGES[0]

  const select = (code) => {
    i18n.changeLanguage(code)
    localStorage.setItem('agrow_lang', code)
    setOpen(false)
  }

  // Close on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        title={error || undefined}
        className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors flex items-center gap-1.5 ${
          error ? 'border-red-300 text-red-600' : 'border-gray-200 hover:bg-gray-50'
        }`}
      >
        {isTranslating ? (
          <span className="w-3.5 h-3.5 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
        ) : (
          <span>🌐</span>
        )}
        {isTranslating ? 'Translating…' : current.native}
        <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {error && (
        <div className="absolute top-full right-0 mt-1 w-64 bg-red-50 border border-red-200 rounded-lg p-2 text-xs text-red-700 z-50 shadow">
          {error}
        </div>
      )}

      {open && (
        <div className="absolute right-0 mt-1 w-44 bg-white border border-gray-100 rounded-xl shadow-lg z-50 py-1 overflow-hidden">
          {LANGUAGES.map(lang => (
            <button
              key={lang.code}
              onClick={() => select(lang.code)}
              className={`w-full text-left px-4 py-2 text-sm flex items-center justify-between hover:bg-gray-50 transition-colors ${
                lang.code === i18n.language ? 'text-green-700 font-medium bg-green-50' : 'text-gray-700'
              }`}
            >
              <span>{lang.native}</span>
              <span className="text-xs text-gray-400">{lang.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

const NAV_LINKS = [
  { to: '/dashboard',     key: 'nav.dashboard' },
  { to: '/weather',       key: 'nav.weather' },
  { to: '/market',        key: 'nav.market' },
  { to: '/recommend',     key: 'nav.recommend' },
  { to: '/irrigation',    key: 'nav.irrigation' },
  { to: '/marketplace',   key: 'nav.marketplace' },
  { to: '/disease',       key: 'nav.disease' },
  { to: '/advisory',      key: 'nav.advisory' },
  { to: '/notifications', key: 'nav.notifications', badge: true },
]

export default function Navbar() {
  const { t } = useTranslation()
  const { token, user, logout } = useAuthStore()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const qc = useQueryClient()

  // Unread notification count
  const { data: countData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: getUnreadCount,
    enabled: !!token,
    refetchInterval: 30_000,   // poll every 30s as fallback
    retry: false,
  })
  const unreadCount = countData?.unread || 0

  // WebSocket for instant badge updates
  useEffect(() => {
    if (!token) return
    const cancel = connectNotificationWS((msg) => {
      if (msg.event === 'notifications_updated' || msg.event === 'new_notification') {
        qc.invalidateQueries({ queryKey: ['unread-count'] })
      }
    })
    return cancel
  }, [token, qc])

  // Update browser tab title with unread count
  useEffect(() => {
    const base = 'Agrow Intelligence'
    document.title = unreadCount > 0 ? `(${unreadCount}) ${base}` : base
  }, [unreadCount])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <nav className="bg-white/95 backdrop-blur-md border-b border-gray-100 sticky top-0 z-40" style={{boxShadow:'0 1px 0 rgba(0,0,0,0.06)'}}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 shrink-0" style={{fontFamily:"'Plus Jakarta Sans',sans-serif"}}>
            <span className="text-2xl">🌱</span>
            <span className="font-bold text-xl text-green-700 tracking-tight">Agrow</span>
            <span className="text-xs font-semibold bg-green-50 text-green-600 px-2 py-0.5 rounded-full border border-green-100">Intelligence</span>
          </Link>

          {/* Desktop nav links */}
          {token && (
            <div className="hidden lg:flex items-center gap-0.5 overflow-x-auto">
              {NAV_LINKS.map(({ to, key, badge }) => (
                <Link
                  key={to}
                  to={to}
                  className={`relative px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                    pathname === to
                      ? 'bg-green-50 text-green-700 font-semibold'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                  style={{fontFamily:"'Plus Jakarta Sans',sans-serif", fontSize:'0.82rem'}}
                >
                  {t(key)}
                  {badge && unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1 leading-none">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </Link>
              ))}
            </div>
          )}

          {/* Right side */}
          <div className="flex items-center gap-3">
            <LanguageDropdown />

            {token ? (
              <>
                <Link to="/profile" className="hidden sm:block text-sm font-medium text-gray-700 hover:text-green-700">
                  {user?.username}
                </Link>
                <button
                  onClick={handleLogout}
                  className="hidden sm:block text-sm text-gray-500 hover:text-red-600 transition-colors"
                >
                  {t('nav.logout')}
                </button>
                {/* Mobile hamburger */}
                <button
                  className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100"
                  onClick={() => setMobileOpen(o => !o)}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={mobileOpen ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'} />
                  </svg>
                </button>
              </>
            ) : (
              <>
                <Link to="/login"    className="text-sm font-medium text-gray-600 hover:text-gray-900">{t('nav.login')}</Link>
                <Link to="/register" className="btn-primary text-sm">{t('nav.register')}</Link>
              </>
            )}
          </div>
        </div>

        {/* Mobile menu */}
        {token && mobileOpen && (
          <div className="lg:hidden border-t border-gray-100 py-3 space-y-1">
            {NAV_LINKS.map(({ to, key, badge }) => (
              <Link
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  pathname === to ? 'bg-green-50 text-green-700' : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {t(key)}
                {badge && unreadCount > 0 && (
                  <span className="min-w-[20px] h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </Link>
            ))}
            <div className="border-t border-gray-100 pt-2 mt-2 flex items-center justify-between px-3">
              <span className="text-sm text-gray-700 font-medium">{user?.username}</span>
              <button onClick={handleLogout} className="text-sm text-red-500 hover:text-red-700">
                {t('nav.logout')}
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
