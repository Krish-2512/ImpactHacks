import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { getCropPrices, getPriceForecast } from '../api/predictions'
import { getLatestReport } from '../api/agents'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

const CROP_COLORS = {
  brinjal:  '#8B5CF6',
  cabbage:  '#10B981',
  lemon:    '#F59E0B',
  tomato:   '#EF4444',
  potato:   '#6366F1',
  onion:    '#EC4899',
  ginger:   '#D97706',
  turmeric: '#F97316',
  chili:    '#DC2626',
  garlic:   '#9CA3AF',
}

const CROP_ICONS = {
  brinjal:  '🍆',
  cabbage:  '🥬',
  lemon:    '🍋',
  tomato:   '🍅',
  potato:   '🥔',
  onion:    '🧅',
  ginger:   '🫚',
  turmeric: '🌿',
  chili:    '🌶️',
  garlic:   '🧄',
}

const DECISION_CLASS = { SELL: 'status-sell', HOLD: 'status-hold', WAIT: 'status-wait' }

// Separate scale groups so cheap crops don't become invisible beside ₹11k turmeric
const VEGGIE_CROPS = ['brinjal', 'cabbage', 'tomato', 'potato', 'onion', 'chili']
const SPICE_CROPS  = ['ginger', 'turmeric', 'garlic', 'lemon']

function PriceChart({ data, crops, title, source }) {
  if (!data.length) return <div className="h-64 animate-pulse bg-gray-50 rounded-xl" />
  return (
    <div className="agent-card mb-4">
      <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-xs text-gray-400 mb-4">{source}</p>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} unit="₹" width={64} tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
          <Tooltip formatter={(v, name) => [`₹${Number(v)?.toLocaleString('en-IN')}`, name]} />
          <Legend />
          {crops.map((crop) => (
            <Area
              key={crop}
              type="monotone"
              dataKey={crop}
              stroke={CROP_COLORS[crop]}
              fill={CROP_COLORS[crop]}
              fillOpacity={0.07}
              strokeWidth={2}
              name={crop.charAt(0).toUpperCase() + crop.slice(1)}
              dot={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function MarketPage() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState('vegetables')

  const { data: pricesData, isLoading } = useQuery({
    queryKey: ['prices'],
    queryFn: getCropPrices,
    staleTime: 5 * 60 * 1000,
  })

  const { data: forecastData, isLoading: chartLoading } = useQuery({
    queryKey: ['prices-forecast'],
    queryFn: () => getPriceForecast(10),
    staleTime: 5 * 60 * 1000,
  })

  const { data: report } = useQuery({
    queryKey: ['latest-report'],
    queryFn: getLatestReport,
  })

  const prices    = pricesData?.prices || {}
  const decisions = report?.sell_hold_decisions || {}
  const chartData = forecastData?.forecast || []
  const chartSource = t('market.chart_source')

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{t('market.title')}</h1>

      {/* All 10 crop price cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 mb-8">
        {isLoading
          ? Array(10).fill(0).map((_, i) => (
              <div key={i} className="agent-card h-28 animate-pulse bg-gray-100 rounded-2xl" />
            ))
          : Object.entries(prices).map(([crop, price]) => (
              <div key={crop} className="agent-card text-center py-4">
                <div className="text-3xl mb-1">{CROP_ICONS[crop] || '🌿'}</div>
                <div className="text-lg font-bold text-gray-900">
                  ₹{Number(price)?.toLocaleString('en-IN')}
                </div>
                <div className="text-xs text-gray-500 capitalize mb-2">{crop} / quintal</div>
                {decisions[crop] && (
                  <span className={DECISION_CLASS[decisions[crop]] || 'status-hold'}>
                    {decisions[crop]}
                  </span>
                )}
              </div>
            ))
        }
      </div>

      {/* Chart tabs — split by price scale */}
      <div className="agent-card mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">{t('market.price_chart')}</h2>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('vegetables')}
              className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
                activeTab === 'vegetables'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t('market.tab_vegetables')}
            </button>
            <button
              onClick={() => setActiveTab('spices')}
              className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
                activeTab === 'spices'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t('market.tab_spices')}
            </button>
          </div>
        </div>

        <p className="text-xs text-gray-400 mb-4">{chartSource}</p>

        {chartLoading ? (
          <div className="h-60 animate-pulse bg-gray-50 rounded-xl" />
        ) : activeTab === 'vegetables' ? (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} unit="₹" width={56} />
              <Tooltip formatter={(v, name) => [`₹${Number(v)?.toLocaleString('en-IN')}`, name]} />
              <Legend />
              {VEGGIE_CROPS.filter(c => chartData[0]?.[c] !== undefined).map((crop) => (
                <Area
                  key={crop} type="monotone" dataKey={crop}
                  stroke={CROP_COLORS[crop]} fill={CROP_COLORS[crop]}
                  fillOpacity={0.07} strokeWidth={2} dot={false}
                  name={crop.charAt(0).toUpperCase() + crop.slice(1)}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} unit="₹" width={64} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
              <Tooltip formatter={(v, name) => [`₹${Number(v)?.toLocaleString('en-IN')}`, name]} />
              <Legend />
              {SPICE_CROPS.filter(c => chartData[0]?.[c] !== undefined).map((crop) => (
                <Area
                  key={crop} type="monotone" dataKey={crop}
                  stroke={CROP_COLORS[crop]} fill={CROP_COLORS[crop]}
                  fillOpacity={0.07} strokeWidth={2} dot={false}
                  name={crop.charAt(0).toUpperCase() + crop.slice(1)}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Market analysis */}
      {report?.market_analysis && (
        <div className="agent-card">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-2xl">📊</span>
            <h2 className="font-semibold text-gray-900">{t('market.market_analysis')}</h2>
          </div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed bg-gray-50 rounded-xl p-4">
            {report.market_analysis}
          </div>
        </div>
      )}
    </div>
  )
}
