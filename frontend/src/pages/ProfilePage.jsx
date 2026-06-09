import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../store/authStore'
import { updateMe } from '../api/auth'

const CROP_ICONS = { tomato: '🍅', brinjal: '🍆', cabbage: '🥬', lemon: '🍋' }

export default function ProfilePage() {
  const { t } = useTranslation()
  const { user, updateUser } = useAuthStore()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    location: user?.location || '',
    primary_crops: user?.primary_crops?.join(', ') || '',
    farm_size_acres: user?.farm_size_acres || '',
    phone: user?.phone || '',
  })
  const [msg, setMsg] = useState('')

  const handleSave = async () => {
    const crops = form.primary_crops
      ? form.primary_crops.split(',').map(c => c.trim().toLowerCase()).filter(Boolean)
      : []
    const data = await updateMe({ ...form, primary_crops: crops, farm_size_acres: form.farm_size_acres ? Number(form.farm_size_acres) : null })
    updateUser({ ...user, ...form, primary_crops: crops })
    setEditing(false)
    setMsg('Profile updated!')
    setTimeout(() => setMsg(''), 3000)
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{t('profile.title')}</h1>

      <div className="agent-card mb-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center text-2xl">
            {user?.role === 'farmer' ? '🌾' : '🛒'}
          </div>
          <div>
            <div className="text-xl font-bold text-gray-900">{user?.username}</div>
            <div className="text-sm text-gray-500">{user?.email}</div>
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 capitalize mt-1 inline-block">
              {user?.role}
            </span>
          </div>
        </div>

        {editing ? (
          <div className="space-y-4">
            {[
              { key: 'location', label: t('profile.location'), placeholder: 'Guwahati, Assam' },
              { key: 'phone', label: 'Phone', placeholder: '+91 9876543210' },
              { key: 'primary_crops', label: t('profile.crops'), placeholder: 'tomato, brinjal, cabbage' },
              { key: 'farm_size_acres', label: t('profile.farm_size'), placeholder: '2.5', type: 'number' },
            ].map(({ key, label, placeholder, type = 'text' }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input type={type} placeholder={placeholder}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
                />
              </div>
            ))}
            <div className="flex gap-3 mt-4">
              <button onClick={handleSave} className="btn-primary">{t('profile.update')}</button>
              <button onClick={() => setEditing(false)} className="btn-secondary">{t('common.cancel')}</button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {[
              { label: t('profile.location'), value: user?.location || '—' },
              { label: 'Phone', value: user?.phone || '—' },
              { label: t('profile.farm_size'), value: user?.farm_size_acres ? `${user.farm_size_acres} acres` : '—' },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between text-sm py-2 border-b border-gray-50 last:border-0">
                <span className="text-gray-500">{label}</span>
                <span className="font-medium text-gray-900">{value}</span>
              </div>
            ))}
            {user?.primary_crops?.length > 0 && (
              <div className="pt-2">
                <p className="text-sm text-gray-500 mb-2">{t('profile.crops')}</p>
                <div className="flex flex-wrap gap-2">
                  {user.primary_crops.map(crop => (
                    <span key={crop} className="bg-green-50 text-green-700 px-3 py-1 rounded-full text-sm capitalize">
                      {CROP_ICONS[crop] || '🌿'} {crop}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <button onClick={() => setEditing(true)} className="btn-secondary mt-4 w-full">
              Edit Profile
            </button>
          </div>
        )}
      </div>
      {msg && <div className="alert-info">{msg}</div>}
    </div>
  )
}
