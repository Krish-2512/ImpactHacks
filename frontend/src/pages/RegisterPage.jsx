import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../store/authStore'
import { register } from '../api/auth'

export default function RegisterPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { login: storeLogin } = useAuthStore()
  const [form, setForm] = useState({
    username: '', email: '', password: '', role: 'farmer',
    location: '', primary_crops: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const crops = form.primary_crops
        ? form.primary_crops.split(',').map(c => c.trim().toLowerCase()).filter(Boolean)
        : []
      const data = await register({ ...form, primary_crops: crops })
      storeLogin(data.access_token, data.user)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🌱</div>
          <h1 className="text-2xl font-bold text-gray-900">{t('auth.register_title')}</h1>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('auth.username')}</label>
              <input type="text" required
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('auth.email')}</label>
              <input type="email" required
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('auth.password')}</label>
              <input type="password" required
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('auth.role')}</label>
              <div className="flex gap-3">
                {['farmer', 'buyer'].map(r => (
                  <button
                    key={r} type="button"
                    onClick={() => setForm(f => ({ ...f, role: r }))}
                    className={`flex-1 py-2.5 rounded-lg text-sm font-medium border transition-colors ${
                      form.role === r
                        ? 'bg-green-600 text-white border-green-600'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-green-400'
                    }`}
                  >
                    {r === 'farmer' ? `🌾 ${t('auth.farmer')}` : `🛒 ${t('auth.buyer')}`}
                  </button>
                ))}
              </div>
            </div>
            {form.role === 'farmer' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('auth.farm_location')}</label>
                  <input type="text" placeholder="e.g. Guwahati, Assam"
                    value={form.location}
                    onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('auth.primary_crops')}</label>
                  <input type="text" placeholder="tomato, brinjal, cabbage"
                    value={form.primary_crops}
                    onChange={e => setForm(f => ({ ...f, primary_crops: e.target.value }))}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
                  />
                </div>
              </>
            )}
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary w-full text-center">
              {loading ? t('common.loading') : t('auth.register_btn')}
            </button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-6">
            {t('auth.have_account')}{' '}
            <Link to="/login" className="text-green-600 font-medium hover:underline">{t('nav.login')}</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
