import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { getWeather } from '../api/predictions'
import { getLatestReport } from '../api/agents'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

const CONDITION_ICON = (condition = '') => {
  const c = condition.toLowerCase()
  if (c.includes('rain') || c.includes('storm')) return '🌧️'
  if (c.includes('cloud') || c.includes('overcast')) return '⛅'
  if (c.includes('fog') || c.includes('mist')) return '🌫️'
  if (c.includes('snow')) return '❄️'
  return '☀️'
}

function WeatherMetric({ label, value, unit, icon, color }) {
  return (
    <div className="agent-card text-center">
      <div className="text-3xl mb-2">{icon}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}{unit}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  )
}

export default function WeatherPage() {
  const { t } = useTranslation()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['weather'],
    queryFn: getWeather,
    staleTime: 5 * 60 * 1000,
  })

  const { data: report } = useQuery({
    queryKey: ['latest-report'],
    queryFn: getLatestReport,
  })

  if (isLoading) return (
    <div className="max-w-5xl mx-auto px-6 py-16 text-center text-gray-400">
      <div className="text-4xl mb-3 animate-spin">⚙️</div>
      <p>{t('weather.loading')}</p>
    </div>
  )

  if (isError) return (
    <div className="max-w-5xl mx-auto px-6 py-16 text-center text-red-400">
      <div className="text-4xl mb-3">⚠️</div>
      <p>{t('common.error')}</p>
    </div>
  )

  const today = data?.today || {}
  const forecast = data?.forecast || []

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{t('weather.title')}</h1>

      {/* Condition banner */}
      <div className="bg-gradient-to-r from-blue-600 to-sky-500 text-white rounded-2xl p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-5xl font-bold">{today.Temperature?.toFixed(1)}°C</div>
            <div className="text-blue-100 text-lg mt-1">{today.Condition}</div>
            <div className="text-blue-200 text-sm mt-1">{t('weather.today_forecast')} · Northeast India</div>
          </div>
          <div className="text-7xl opacity-50">{CONDITION_ICON(today.Condition)}</div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <WeatherMetric label={t('weather.temperature')}   value={today.Temperature?.toFixed(1)}  unit="°C"   icon="🌡️" color="text-orange-600" />
        <WeatherMetric label={t('weather.humidity')}      value={today.Humidity?.toFixed(0)}     unit="%"    icon="💧" color="text-blue-600" />
        <WeatherMetric label={t('weather.wind_speed')}    value={today.Wind_Speed?.toFixed(1)}   unit=" km/h" icon="💨" color="text-gray-600" />
        <WeatherMetric label={t('weather.precipitation')} value={today.Precipitation?.toFixed(1)} unit="mm"  icon="🌧️" color="text-indigo-600" />
      </div>

      {/* 7-day forecast chart — real API data, no hardcoded values */}
      {forecast.length > 0 && (
        <div className="agent-card mb-6">
          <h2 className="font-semibold text-gray-900 mb-1">{t('weather.forecast_chart')}</h2>
          <p className="text-xs text-gray-400 mb-4">{t('weather.forecast_source')}</p>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={forecast}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis yAxisId="temp" orientation="left"  tick={{ fontSize: 12 }} unit="°" domain={['auto', 'auto']} />
              <YAxis yAxisId="hum"  orientation="right" tick={{ fontSize: 12 }} unit="%" domain={[0, 100]} />
              <Tooltip
                formatter={(v, name) =>
                  name === 'Temp (°C)' ? `${v?.toFixed(1)}°C` : `${v?.toFixed(0)}%`
                }
              />
              <Legend />
              <Line yAxisId="temp" type="monotone" dataKey="Temperature" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} name="Temp (°C)" />
              <Line yAxisId="hum"  type="monotone" dataKey="Humidity"    stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} name="Humidity (%)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 7-day daily cards */}
      {forecast.length > 0 && (
        <div className="grid grid-cols-7 gap-2 mb-6">
          {forecast.map((day) => (
            <div key={day.date} className="agent-card text-center py-3 px-1">
              <div className="text-xs font-medium text-gray-500 mb-1">{day.label}</div>
              <div className="text-lg mb-1">{CONDITION_ICON(day.Condition)}</div>
              {day.temp_max != null ? (
                <>
                  <div className="text-sm font-bold text-red-500">{day.temp_max?.toFixed(0)}°</div>
                  <div className="text-xs text-blue-400">{day.temp_min?.toFixed(0)}°</div>
                </>
              ) : (
                <div className="text-sm font-bold text-gray-900">{day.Temperature?.toFixed(0)}°</div>
              )}
              <div className="text-xs text-blue-500">{day.Humidity?.toFixed(0)}%</div>
            </div>
          ))}
        </div>
      )}

      {/* AI interpretation */}
      {report?.weather_interpretation && (
        <div className="agent-card">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-2xl">🤖</span>
            <h2 className="font-semibold text-gray-900">{t('weather.ai_advice')}</h2>
          </div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed bg-gray-50 rounded-xl p-4">
            {report.weather_interpretation}
          </div>
        </div>
      )}
    </div>
  )
}
