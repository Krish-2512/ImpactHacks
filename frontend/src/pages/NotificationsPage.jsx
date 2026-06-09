import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getNotifications, markRead, deleteNotification } from '../api/notifications'

const TYPE_ICON = { weather: '🌤️', price_alert: '📈', agent_report: '🤖', disease: '🔬', system: '⚙️' }
const SEV_CLASS = { urgent: 'alert-urgent', warning: 'alert-warning', info: 'alert-info' }

export default function NotificationsPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: getNotifications,
  })

  const readMutation   = useMutation({ mutationFn: markRead,             onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }) })
  const deleteMutation = useMutation({ mutationFn: deleteNotification,   onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }) })

  const unreadCount = notifications.filter(n => !n.is_read).length

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('notifications.title')}</h1>
        {unreadCount > 0 && (
          <span className="bg-red-100 text-red-700 text-xs font-semibold px-2.5 py-1 rounded-full">
            {unreadCount} unread
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array(4).fill(0).map((_, i) => <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-5xl mb-3">🔔</div>
          <p>{t('notifications.no_notifications')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map(n => (
            <div
              key={n._id}
              className={`agent-card flex items-start gap-4 ${!n.is_read ? 'border-green-200 bg-green-50/30' : ''}`}
            >
              <div className="text-2xl flex-shrink-0">{TYPE_ICON[n.notification_type] || '🔔'}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-700 leading-relaxed">{n.message}</p>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-xs text-gray-400">
                    {new Date(n.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${
                    n.severity === 'urgent' ? 'bg-red-100 text-red-700' :
                    n.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{n.notification_type?.replace('_', ' ')}</span>
                </div>
              </div>
              <div className="flex flex-col gap-1.5 flex-shrink-0">
                {!n.is_read && (
                  <button
                    onClick={() => readMutation.mutate(n._id)}
                    className="text-xs text-green-600 hover:underline whitespace-nowrap"
                  >
                    {t('notifications.mark_read')}
                  </button>
                )}
                <button
                  onClick={() => deleteMutation.mutate(n._id)}
                  className="text-xs text-red-400 hover:underline"
                >
                  {t('notifications.delete')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
