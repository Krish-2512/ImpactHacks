import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getNotifications, markRead, markAllRead,
  deleteNotification, deleteAllRead, connectNotificationWS,
} from '../api/notifications'

const PRIORITY_STYLE = {
  urgent: 'bg-red-100 text-red-700 border-red-200',
  high:   'bg-orange-100 text-orange-700 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  low:    'bg-gray-100 text-gray-600 border-gray-200',
}

const PRIORITY_BORDER = {
  urgent: 'border-l-4 border-l-red-500',
  high:   'border-l-4 border-l-orange-400',
  medium: 'border-l-4 border-l-yellow-400',
  low:    '',
}

export default function NotificationsPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => getNotifications(),
  })

  // WebSocket for real-time updates
  useEffect(() => {
    const cancel = connectNotificationWS((msg) => {
      if (msg.event === 'notifications_updated' || msg.event === 'new_notification') {
        qc.invalidateQueries({ queryKey: ['notifications'] })
        qc.invalidateQueries({ queryKey: ['unread-count'] })
      }
    })
    return cancel
  }, [qc])

  const readMutation     = useMutation({ mutationFn: markRead,            onSuccess: () => { qc.invalidateQueries({ queryKey: ['notifications'] }); qc.invalidateQueries({ queryKey: ['unread-count'] }) } })
  const readAllMutation  = useMutation({ mutationFn: markAllRead,         onSuccess: () => { qc.invalidateQueries({ queryKey: ['notifications'] }); qc.invalidateQueries({ queryKey: ['unread-count'] }) } })
  const deleteMutation   = useMutation({ mutationFn: deleteNotification,  onSuccess: () => { qc.invalidateQueries({ queryKey: ['notifications'] }); qc.invalidateQueries({ queryKey: ['unread-count'] }) } })
  const clearReadMutation = useMutation({ mutationFn: deleteAllRead,      onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }) })

  const unreadCount = notifications.filter(n => !n.is_read).length

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{t('notifications.title')}</h1>
          {unreadCount > 0 && (
            <span className="bg-red-100 text-red-700 text-xs font-semibold px-2.5 py-1 rounded-full">
              {unreadCount} unread
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {unreadCount > 0 && (
            <button
              onClick={() => readAllMutation.mutate()}
              disabled={readAllMutation.isPending}
              className="text-xs px-3 py-1.5 rounded-lg bg-green-50 text-green-700 hover:bg-green-100 transition-colors font-medium"
            >
              Mark all read
            </button>
          )}
          <button
            onClick={() => clearReadMutation.mutate()}
            disabled={clearReadMutation.isPending}
            className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
          >
            Clear read
          </button>
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array(4).fill(0).map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />
          ))}
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
              className={`agent-card flex items-start gap-4 ${
                !n.is_read ? 'border-green-200 bg-green-50/30' : ''
              } ${PRIORITY_BORDER[n.priority] || ''}`}
            >
              <div className="text-2xl flex-shrink-0">{n.icon || '🔔'}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="text-sm font-semibold text-gray-800 leading-snug">{n.title}</p>
                  <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full border font-medium capitalize ${PRIORITY_STYLE[n.priority] || PRIORITY_STYLE.low}`}>
                    {n.priority || 'low'}
                  </span>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">{n.body}</p>
                <div className="flex items-center gap-3 mt-2 flex-wrap">
                  <span className="text-xs text-gray-400">
                    {new Date(n.created_at).toLocaleDateString('en-IN', {
                      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                    })}
                  </span>
                  {n.type && (
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full capitalize">
                      {n.type.replace('_', ' ')}
                    </span>
                  )}
                  {n.confidence > 0 && (
                    <span className="text-xs text-gray-400">
                      {Math.round(n.confidence * 100)}% confidence
                    </span>
                  )}
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
