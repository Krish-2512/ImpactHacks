import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { recommendCrop } from '../api/ml'

const CROP_ICONS = {
  tomato: '🍅', brinjal: '🍆', cabbage: '🥬', lemon: '🍋',
  potato: '🥔', onion: '🧅', ginger: '🫚', turmeric: '🌿',
  chili: '🌶️', garlic: '🧄',
}

const FIELDS = [
  { key: 'N',           label: 'Nitrogen (N)',       unit: 'kg/ha',   min: 0,    max: 200,  step: 1,   default: 70,    tip: 'Amount of nitrogen in soil' },
  { key: 'P',           label: 'Phosphorous (P)',    unit: 'kg/ha',   min: 0,    max: 150,  step: 1,   default: 50,    tip: 'Phosphorous content for root growth' },
  { key: 'K',           label: 'Potassium (K)',      unit: 'kg/ha',   min: 0,    max: 200,  step: 1,   default: 70,    tip: 'Potassium for disease resistance' },
  { key: 'temperature', label: 'Temperature',        unit: '°C',      min: 5,    max: 45,   step: 0.5, default: 26,    tip: 'Average daily temperature' },
  { key: 'humidity',    label: 'Humidity',           unit: '%',       min: 10,   max: 100,  step: 1,   default: 70,    tip: 'Relative humidity' },
  { key: 'pH',          label: 'Soil pH',            unit: '',        min: 3.5,  max: 9.5,  step: 0.1, default: 6.5,   tip: '7 is neutral; most crops prefer 6–7' },
  { key: 'rainfall',    label: 'Annual Rainfall',    unit: 'mm',      min: 50,   max: 4000, step: 10,  default: 1200,  tip: 'Total yearly rainfall in your area' },
]

function Slider({ field, value, onChange }) {
  const pct = ((value - field.min) / (field.max - field.min)) * 100
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-baseline">
        <label className="text-sm font-medium text-gray-700">{field.label}</label>
        <span className="text-sm font-bold text-green-700 tabular-nums">
          {value}{field.unit}
        </span>
      </div>
      <p className="text-xs text-gray-400">{field.tip}</p>
      <div className="relative">
        <input
          type="range"
          min={field.min} max={field.max} step={field.step}
          value={value}
          onChange={e => onChange(field.key, parseFloat(e.target.value))}
          className="w-full h-2 rounded-full appearance-none cursor-pointer"
          style={{
            background: `linear-gradient(to right, #16a34a ${pct}%, #e5e7eb ${pct}%)`,
          }}
        />
        <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
          <span>{field.min}{field.unit}</span>
          <span>{field.max}{field.unit}</span>
        </div>
      </div>
    </div>
  )
}

function ConfidenceBar({ value, color }) {
  return (
    <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className={`h-2 rounded-full ${color}`}
      />
    </div>
  )
}

const SUITABILITY_COLORS = {
  Excellent: { bar: 'bg-green-500',  badge: 'bg-green-100 text-green-800' },
  Good:      { bar: 'bg-blue-500',   badge: 'bg-blue-100  text-blue-800' },
  Moderate:  { bar: 'bg-yellow-500', badge: 'bg-yellow-100 text-yellow-800' },
}

const FEATURE_LABELS = {
  N:           'Nitrogen',
  P:           'Phosphorous',
  K:           'Potassium',
  temperature: 'Temperature',
  humidity:    'Humidity',
  pH:          'Soil pH',
  rainfall:    'Rainfall',
}

// SHAP force-plot bar: shows positive (green) and negative (red) contributions
function ShapBar({ feature, value, maxAbs }) {
  const pct = Math.min(100, (Math.abs(value) / maxAbs) * 100)
  const isPositive = value >= 0
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-24 text-right text-gray-600 shrink-0">{FEATURE_LABELS[feature] || feature}</span>
      <div className="flex-1 flex items-center h-5 relative">
        {/* Divider line in center */}
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-300" />
        {isPositive ? (
          <div className="flex w-full">
            <div className="w-1/2" />
            <div
              className="h-5 bg-green-500 rounded-r transition-all"
              style={{ width: `${pct / 2}%` }}
            />
          </div>
        ) : (
          <div className="flex w-full justify-end">
            <div
              className="h-5 bg-red-400 rounded-l transition-all"
              style={{ width: `${pct / 2}%`, marginLeft: 'auto', marginRight: '50%' }}
            />
          </div>
        )}
      </div>
      <span className={`w-14 tabular-nums font-medium shrink-0 ${isPositive ? 'text-green-700' : 'text-red-600'}`}>
        {isPositive ? '+' : ''}{(value * 100).toFixed(2)}%
      </span>
    </div>
  )
}

function ShapExplanation({ shap }) {
  if (!shap || shap.error) return null
  const entries = Object.entries(shap.contributions)
  const maxAbs = Math.max(...entries.map(([, v]) => Math.abs(v)), 0.001)
  return (
    <div className="agent-card">
      <h3 className="font-semibold text-gray-800 mb-1">🔬 Why This Crop? (SHAP Explanation)</h3>
      <p className="text-xs text-gray-400 mb-4">
        Explainable AI — each bar shows how much a feature <span className="text-green-600 font-medium">pushed toward</span> or{' '}
        <span className="text-red-500 font-medium">pulled away from</span>{' '}
        <span className="font-semibold capitalize">{shap.crop}</span> (base: {(shap.base_value * 100).toFixed(1)}% avg)
      </p>
      <div className="space-y-2">
        {entries.map(([feat, val]) => (
          <ShapBar key={feat} feature={feat} value={val} maxAbs={maxAbs} />
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-gray-100 flex justify-between text-xs text-gray-500">
        <span>Predicted probability for <span className="font-semibold capitalize">{shap.crop}</span></span>
        <span className="font-bold text-green-700">{shap.predicted_probability}%</span>
      </div>
    </div>
  )
}

export default function CropRecommenderPage() {
  const defaults = Object.fromEntries(FIELDS.map(f => [f.key, f.default]))
  const [values, setValues] = useState(defaults)

  const mutation = useMutation({ mutationFn: recommendCrop })

  const handleChange = (key, val) => setValues(prev => ({ ...prev, [key]: val }))

  const handleSubmit = () => mutation.mutate(values)

  const result = mutation.data

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Crop Recommender</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Enter your soil and climate conditions. A <strong>Random Forest</strong> model trained on
          ICAR agronomic data will recommend the best crops for your farm.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

        {/* Input Panel */}
        <div className="agent-card space-y-6">
          <h2 className="font-semibold text-gray-800 flex items-center gap-2">
            🌱 Soil & Climate Parameters
          </h2>
          {FIELDS.map(f => (
            <Slider key={f.key} field={f} value={values[f.key]} onChange={handleChange} />
          ))}
          <button
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="w-full btn-primary py-3 rounded-xl font-semibold disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {mutation.isPending ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              '🤖 Get AI Crop Recommendation'
            )}
          </button>
          {mutation.isError && (
            <p className="text-red-600 text-sm text-center">
              {mutation.error?.response?.data?.detail || 'Recommendation failed. Please try again.'}
            </p>
          )}
        </div>

        {/* Results Panel */}
        <div className="space-y-4">
          <AnimatePresence mode="wait">
            {!result && !mutation.isPending && (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="agent-card h-full flex flex-col items-center justify-center text-center py-16 text-gray-400"
              >
                <div className="text-6xl mb-4">🌾</div>
                <p className="font-medium">Adjust the sliders and click Recommend</p>
                <p className="text-sm mt-1">The model analyzes 7 parameters across 10 Northeast India crops</p>
              </motion.div>
            )}

            {mutation.isPending && (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="agent-card h-full flex flex-col items-center justify-center py-16 text-center"
              >
                <div className="w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-gray-600 font-medium">Running Random Forest inference...</p>
                <p className="text-xs text-gray-400 mt-1">200 decision trees voting</p>
              </motion.div>
            )}

            {result && (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {/* Top Recommendations */}
                <div className="agent-card">
                  <h3 className="font-semibold text-gray-800 mb-4">🏆 Top Crop Recommendations</h3>
                  <div className="space-y-4">
                    {result.recommendations.map((rec, i) => {
                      const colors = SUITABILITY_COLORS[rec.suitability] || SUITABILITY_COLORS.Moderate
                      return (
                        <div key={rec.crop} className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-2xl">{CROP_ICONS[rec.crop] || '🌿'}</span>
                              <div>
                                <span className="font-semibold text-gray-800 capitalize">{rec.crop}</span>
                                {i === 0 && (
                                  <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                                    Best Match
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors.badge}`}>
                                {rec.suitability}
                              </span>
                              <span className="text-sm font-bold text-gray-700 tabular-nums">
                                {rec.confidence}%
                              </span>
                            </div>
                          </div>
                          <ConfidenceBar value={rec.confidence} color={colors.bar} />
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Feature Importance */}
                <div className="agent-card">
                  <h3 className="font-semibold text-gray-800 mb-3">📊 What Matters Most</h3>
                  <p className="text-xs text-gray-400 mb-3">
                    How much each factor influenced this recommendation (Random Forest feature importance)
                  </p>
                  <div className="space-y-2.5">
                    {Object.entries(result.feature_importance)
                      .sort((a, b) => b[1] - a[1])
                      .map(([feat, imp]) => (
                        <div key={feat} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-gray-600">{FEATURE_LABELS[feat] || feat}</span>
                            <span className="font-medium text-gray-700">{imp}%</span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-1.5">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${imp}%` }}
                              transition={{ duration: 0.5 }}
                              className="h-1.5 bg-indigo-400 rounded-full"
                            />
                          </div>
                        </div>
                      ))}
                  </div>
                </div>

                {/* SHAP Explanation */}
                <ShapExplanation shap={result.shap_explanation} />

                <p className="text-xs text-gray-400 text-center">{result.note}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
