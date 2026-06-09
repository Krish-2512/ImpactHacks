import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { runAgentCycle, getLatestReport, getCycleStatus } from '../api/agents'
import { getWeather } from '../api/predictions'
import { getCropPrices } from '../api/predictions'
import { useAuthStore } from '../store/authStore'
import { useEffect, useRef } from 'react'

const DECISION_CLASS = { SELL: 'status-sell', HOLD: 'status-hold', WAIT: 'status-wait' }

function WeatherCard({ weather }) {
  const { t } = useTranslation()
  if (!weather || !weather.Temperature) return null
  return (
    <div className="agent-card">
      <h3 className="text-sm font-medium text-gray-500 mb-3">{t('dashboard.weather_summary')}</h3>
      <div className="flex items-end gap-1 mb-3">
        <span className="text-4xl font-bold text-gray-900">{weather.Temperature?.toFixed(1)}°</span>
        <span className="text-gray-500 pb-1">{weather.Condition}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
        <div><div className="font-medium text-gray-700">{weather.Humidity?.toFixed(0)}%</div><div>Humidity</div></div>
        <div><div className="font-medium text-gray-700">{weather.Wind_Speed?.toFixed(1)}</div><div>km/h Wind</div></div>
        <div><div className="font-medium text-gray-700">{weather.Precipitation?.toFixed(1)}mm</div><div>Rain</div></div>
      </div>
    </div>
  )
}

function PriceCard({ prices, decisions }) {
  const { t } = useTranslation()
  if (!prices) return null
  const priceData = prices.prices || prices
  return (
    <div className="agent-card">
      <h3 className="text-sm font-medium text-gray-500 mb-3">{t('dashboard.price_summary')}</h3>
      <div className="space-y-2">
        {Object.entries(priceData).map(([crop, price]) => (
          <div key={crop} className="flex items-center justify-between">
            <span className="text-sm capitalize text-gray-700">{crop}</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-900">₹{price}</span>
              {decisions?.[crop] && (
                <span className={DECISION_CLASS[decisions[crop]] || 'status-hold'}>
                  {decisions[crop]}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-400 mt-3">per quintal</p>
    </div>
  )
}

export default function DashboardPage() {
  const { t } = useTranslation()
  const user = useAuthStore(s => s.user)
  const qc = useQueryClient()
  const pollRef = useRef(null)

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['latest-report'],
    queryFn: getLatestReport,
  })
  // Weather API now returns {today, forecast} — we only need today for the dashboard card
  const { data: weather } = useQuery({
    queryKey: ['weather'],
    queryFn: getWeather,
    select: (d) => d?.today,
  })
  const { data: pricesData } = useQuery({ queryKey: ['prices'], queryFn: getCropPrices })

  const runMutation = useMutation({
    mutationFn: runAgentCycle,
    onSuccess: (data) => {
      // Poll for completion
      const cycleId = data.cycle_id
      pollRef.current = setInterval(async () => {
        const status = await getCycleStatus(cycleId)
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollRef.current)
          qc.invalidateQueries({ queryKey: ['latest-report'] })
        }
      }, 4000)
    },
  })

  useEffect(() => () => clearInterval(pollRef.current), [])

  const isRunning = runMutation.isPending

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('dashboard.title')}</h1>
          <p className="text-gray-500 text-sm mt-1">
            Welcome back, {user?.username} · {user?.location || 'Northeast India'}
          </p>
        </div>
        <button
          onClick={() => runMutation.mutate()}
          disabled={isRunning}
          className="btn-primary flex items-center gap-2"
        >
          {isRunning ? (
            <><span className="animate-spin">⚙️</span> {t('dashboard.running')}</>
          ) : (
            <><span>🤖</span> {t('dashboard.run_analysis')}</>
          )}
        </button>
      </div>

      {/* Top cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <WeatherCard weather={weather} />
        <PriceCard
          prices={pricesData}
          decisions={report?.cycle ? report.sell_hold_decisions : report?.sell_hold_decisions}
        />
      </div>

      {/* Agent Report */}
      <div className="agent-card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">{t('dashboard.latest_report')}</h2>
          {report?.status && (
            <span className={`text-xs px-2 py-1 rounded-full ${
              report.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
            }`}>
              {report.status}
            </span>
          )}
        </div>

        {reportLoading ? (
          <p className="text-gray-400 text-sm">{t('common.loading')}</p>
        ) : report?.final_report ? (
          <>
            <div className="prose prose-sm max-w-none">
              <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed bg-gray-50 rounded-xl p-4">
                {report.final_report}
              </div>
            </div>

            {report.recommendations?.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">🎯 {t('dashboard.recommendations')}</h3>
                <div className="space-y-2">
                  {report.recommendations.map((rec, i) => (
                    <div key={i} className="flex gap-3 text-sm">
                      <span className="w-5 h-5 rounded-full bg-green-100 text-green-700 text-xs flex items-center justify-center flex-shrink-0 font-medium">
                        {i + 1}
                      </span>
                      <span className="text-gray-700">{rec}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report.alerts?.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">⚠️ {t('dashboard.alerts')}</h3>
                <div className="space-y-2">
                  {report.alerts.map((alert, i) => (
                    <div key={i} className="alert-warning">{alert}</div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-12 text-gray-400">
            <div className="text-4xl mb-3">🤖</div>
            <p className="text-sm">{t('dashboard.no_report')}</p>
          </div>
        )}
      </div>
    </div>
  )
}
