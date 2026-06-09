import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { getIrrigation, getPriceAnomaly } from '../api/ml'

const CROPS = ['tomato','brinjal','cabbage','lemon','potato','onion','ginger','turmeric','chili','garlic']
const STAGES = ['seedling','vegetative','flowering','fruiting']

const CROP_ICONS = {
  tomato:'🍅', brinjal:'🍆', cabbage:'🥬', lemon:'🍋',
  potato:'🥔', onion:'🧅', ginger:'🫚', turmeric:'🌿',
  chili:'🌶️', garlic:'🧄',
}

const STAGE_DESC = {
  seedling:   'First 2–3 weeks after transplanting',
  vegetative: 'Active leaf and stem growth',
  flowering:  'Flowering / bud formation stage',
  fruiting:   'Fruit development and maturation',
}

const URGENCY_CONFIG = {
  none:   { icon:'✅', color:'text-green-700',  bg:'bg-green-50  border-green-200',  label:'No irrigation needed' },
  low:    { icon:'💧', color:'text-blue-700',   bg:'bg-blue-50   border-blue-200',   label:'Low priority' },
  medium: { icon:'⚠️', color:'text-yellow-700', bg:'bg-yellow-50 border-yellow-200', label:'Should irrigate soon' },
  high:   { icon:'🚨', color:'text-red-700',    bg:'bg-red-50    border-red-200',    label:'Irrigate today' },
}

const STATUS_COLORS = {
  normal:               'bg-gray-100  text-gray-600',
  higher_than_usual:    'bg-yellow-100 text-yellow-700',
  much_higher_than_usual:'bg-red-100   text-red-700',
  lower_than_usual:     'bg-blue-100  text-blue-700',
  much_lower_than_usual:'bg-purple-100 text-purple-700',
}

// ── Anomaly Card ──────────────────────────────────────────────────────────────
function PriceAnomalyCard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['priceAnomaly'],
    queryFn: getPriceAnomaly,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return (
    <div className="agent-card animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
      <div className="space-y-2">{[...Array(3)].map((_, i) => <div key={i} className="h-3 bg-gray-100 rounded" />)}</div>
    </div>
  )

  if (isError || !data) return null

  const cfg = data.is_anomaly ? { icon: '🔴', color: 'text-red-700', bg: 'bg-red-50 border-red-200' }
                               : { icon: '🟢', color: 'text-green-700', bg: 'bg-green-50 border-green-200' }

  return (
    <div className={`agent-card border ${cfg.bg}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2">
          {cfg.icon} Price Anomaly Detection
          <span className="text-xs font-normal text-gray-400">(Isolation Forest ML)</span>
        </h3>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
          data.alert_level === 'high' ? 'bg-red-100 text-red-700' :
          data.alert_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
          'bg-green-100 text-green-700'
        }`}>
          {data.alert_level.toUpperCase()}
        </span>
      </div>
      <p className={`text-sm font-medium mb-3 ${cfg.color}`}>{data.summary}</p>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {data.per_crop.map(c => (
          <div key={c.crop} className="text-center">
            <div className="text-lg">{CROP_ICONS[c.crop] || '🌿'}</div>
            <div className="text-xs font-medium capitalize text-gray-700">{c.crop}</div>
            <div className={`text-[10px] px-1 rounded mt-0.5 ${STATUS_COLORS[c.status] || STATUS_COLORS.normal}`}>
              {c.status.replace(/_/g, ' ')}
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-400 mt-3 text-right">Anomaly score: {data.anomaly_score} · {data.date}</p>
    </div>
  )
}

// ── Irrigation Advisor ────────────────────────────────────────────────────────
export default function IrrigationPage() {
  const [form, setForm] = useState({
    crop:            'tomato',
    growth_stage:    'vegetative',
    days_since_rain: 3,
    rain_this_week:  20,
    temperature:     28,
    humidity:        70,
  })

  const mutation = useMutation({ mutationFn: getIrrigation })

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const result = mutation.data
  const urgency = result ? (result.should_irrigate ? result.urgency : 'none') : null
  const cfg     = urgency ? URGENCY_CONFIG[urgency] : null

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Irrigation Advisor</h1>
        <p className="text-gray-500 mt-1 text-sm">
          A <strong>Decision Tree</strong> model trained on FAO crop water-requirement data
          tells you whether to irrigate and exactly how much water to apply.
        </p>
      </div>

      {/* Price Anomaly Card */}
      <PriceAnomalyCard />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Input Form */}
        <div className="agent-card space-y-5">
          <h2 className="font-semibold text-gray-800">💧 Farm Conditions</h2>

          {/* Crop */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Select Crop</label>
            <div className="grid grid-cols-5 gap-2">
              {CROPS.map(c => (
                <button
                  key={c}
                  onClick={() => set('crop', c)}
                  className={`flex flex-col items-center py-2 px-1 rounded-xl border text-xs transition-all ${
                    form.crop === c
                      ? 'border-green-500 bg-green-50 text-green-700 font-semibold'
                      : 'border-gray-200 hover:border-gray-300 text-gray-600'
                  }`}
                >
                  <span className="text-xl">{CROP_ICONS[c]}</span>
                  <span className="capitalize mt-0.5">{c}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Growth Stage */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Growth Stage</label>
            <div className="grid grid-cols-2 gap-2">
              {STAGES.map(s => (
                <button
                  key={s}
                  onClick={() => set('growth_stage', s)}
                  className={`text-left p-3 rounded-xl border transition-all ${
                    form.growth_stage === s
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className={`text-sm font-medium capitalize ${form.growth_stage === s ? 'text-green-700' : 'text-gray-700'}`}>{s}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{STAGE_DESC[s]}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Numeric Inputs */}
          {[
            { key: 'days_since_rain',  label: 'Days since last rain',  unit: 'days', min: 0, max: 20  },
            { key: 'rain_this_week',   label: 'Rainfall this week',    unit: 'mm',   min: 0, max: 150 },
            { key: 'temperature',      label: 'Current temperature',   unit: '°C',   min: 5, max: 45  },
            { key: 'humidity',         label: 'Current humidity',      unit: '%',    min: 10, max: 100 },
          ].map(({ key, label, unit, min, max }) => {
            const val = form[key]
            const pct = ((val - min) / (max - min)) * 100
            return (
              <div key={key}>
                <div className="flex justify-between mb-1">
                  <label className="text-sm font-medium text-gray-700">{label}</label>
                  <span className="text-sm font-bold text-green-700 tabular-nums">{val} {unit}</span>
                </div>
                <input
                  type="range" min={min} max={max} step={key === 'temperature' ? 0.5 : 1}
                  value={val}
                  onChange={e => set(key, parseFloat(e.target.value))}
                  className="w-full h-2 rounded-full appearance-none cursor-pointer"
                  style={{ background: `linear-gradient(to right, #16a34a ${pct}%, #e5e7eb ${pct}%)` }}
                />
              </div>
            )
          })}

          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
            className="w-full btn-primary py-3 rounded-xl font-semibold disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {mutation.isPending ? (
              <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Analyzing...</>
            ) : '🌿 Get Irrigation Advice'}
          </button>
        </div>

        {/* Result */}
        <div>
          <AnimatePresence mode="wait">
            {!result && !mutation.isPending && (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="agent-card flex flex-col items-center justify-center py-20 text-center text-gray-400">
                <div className="text-6xl mb-4">💧</div>
                <p className="font-medium">Set your conditions and click Analyze</p>
                <p className="text-sm mt-1">The model uses crop-specific water requirements from FAO guidelines</p>
              </motion.div>
            )}
            {mutation.isPending && (
              <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="agent-card flex flex-col items-center justify-center py-20">
                <div className="w-10 h-10 border-4 border-green-500 border-t-transparent rounded-full animate-spin mb-4" />
                <p className="text-gray-600">Running Decision Tree inference...</p>
              </motion.div>
            )}
            {result && cfg && (
              <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="space-y-4">

                {/* Main verdict */}
                <div className={`agent-card border-2 ${cfg.bg}`}>
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-4xl">{cfg.icon}</span>
                    <div>
                      <div className={`text-lg font-bold ${cfg.color}`}>{cfg.label}</div>
                      <div className="text-sm text-gray-500 capitalize">
                        {CROP_ICONS[form.crop]} {form.crop} · {form.growth_stage} stage
                      </div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">{result.advice}</p>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Water Need',    value: `${result.crop_water_need} mm/wk`, icon: '🌊' },
                    { label: 'Rain Deficit',  value: `${result.rain_deficit_mm} mm`,    icon: '📉' },
                    { label: 'Recommended',   value: result.recommended_mm ? `${result.recommended_mm} mm` : 'None', icon: '💧' },
                  ].map(s => (
                    <div key={s.label} className="agent-card text-center py-4">
                      <div className="text-2xl">{s.icon}</div>
                      <div className="text-lg font-bold text-gray-800 mt-1">{s.value}</div>
                      <div className="text-xs text-gray-500">{s.label}</div>
                    </div>
                  ))}
                </div>

                {/* Tips */}
                {result.should_irrigate && (
                  <div className="agent-card bg-blue-50 border border-blue-100">
                    <h4 className="font-semibold text-blue-800 text-sm mb-2">💡 Best Practices</h4>
                    <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
                      <li>Water in the early morning (5–8 AM) to reduce evaporation</li>
                      <li>Use drip irrigation for {form.crop} at {form.growth_stage} stage</li>
                      <li>Avoid waterlogging — ensure field drainage is clear</li>
                      <li>Monitor soil moisture again after 3–4 days</li>
                    </ul>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
