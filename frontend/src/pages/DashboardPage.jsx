import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { runAgentCycle, getLatestReport, streamCycle } from '../api/agents'
import { getFarmHealth } from '../api/intelligence'
import { getWeather, getCropPrices } from '../api/predictions'
import { useAuthStore } from '../store/authStore'
import { Markdown } from '../utils/markdown'

const DECISION_CLASS = { SELL: 'status-sell', HOLD: 'status-hold', WAIT: 'status-wait' }

// Full pipeline node list matching the backend graph order
const AGENT_LABELS = {
  fetching:   { label: 'Data Fetching',   icon: '📡' },
  memory:     { label: 'Memory Retrieval',icon: '🧠' },
  planner:    { label: 'Planner',         icon: '🗺️' },
  weather:    { label: 'Weather Agent',   icon: '🌤️' },
  market:     { label: 'Market Agent',    icon: '📈' },
  advisory:   { label: 'Advisory Agent',  icon: '🌿' },
  disease:    { label: 'Disease Analysis',icon: '🔬' },
  multimodal: { label: 'Multimodal',      icon: '🖼️' },
  judge:      { label: 'Judge Review',    icon: '⚖️' },
  supervisor: { label: 'Supervisor',      icon: '🤖' },
}

const VERDICT_STYLE = {
  pass:   'bg-green-100 text-green-700',
  flag:   'bg-yellow-100 text-yellow-700',
  reject: 'bg-red-100 text-red-700',
}

// ── Weather card ───────────────────────────────────────────────────────────────
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

// ── Price card ─────────────────────────────────────────────────────────────────
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

// ── Farm health card ───────────────────────────────────────────────────────────
function FarmHealthCard({ health }) {
  if (!health) return null
  const { overall_score, grade, components } = health
  const scoreColor = overall_score >= 85 ? 'text-green-600' : overall_score >= 70 ? 'text-yellow-600' : overall_score >= 50 ? 'text-orange-500' : 'text-red-600'
  return (
    <div className="agent-card">
      <h3 className="text-sm font-medium text-gray-500 mb-3">🌾 Farm Health Score</h3>
      <div className="flex items-center gap-3 mb-4">
        <span className={`text-4xl font-bold ${scoreColor}`}>{overall_score}</span>
        <div>
          <div className="text-sm font-semibold text-gray-700">{grade}</div>
          <div className="text-xs text-gray-400">out of 100</div>
        </div>
      </div>
      <div className="space-y-2">
        {Object.entries(components || {}).map(([key, comp]) => (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-600">{comp.label}</span>
              <span className="font-medium text-gray-800">{comp.score}/{comp.max}</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all"
                style={{ width: `${(comp.score / comp.max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Agent performance card — shows timings for all pipeline nodes ──────────────
function ConfidenceCard({ confidences, timings }) {
  if (!confidences && !timings) return null
  const entries = Object.entries(AGENT_LABELS).filter(([key]) =>
    confidences?.[key] != null || timings?.[key] != null
  )
  if (!entries.length) return null

  return (
    <div className="agent-card">
      <h3 className="text-sm font-medium text-gray-500 mb-3">🎯 Agent Performance</h3>
      <div className="space-y-2">
        {entries.map(([key, meta]) => {
          const conf = confidences?.[key]
          const ms = timings?.[key]
          return (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm text-gray-600">{meta.icon} {meta.label}</span>
              <div className="flex items-center gap-2 text-xs">
                {conf != null && (
                  <span className={`font-semibold ${conf >= 0.8 ? 'text-green-600' : conf >= 0.6 ? 'text-yellow-600' : 'text-red-500'}`}>
                    {Math.round(conf * 100)}%
                  </span>
                )}
                {ms != null && (
                  <span className="text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                    {ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Live pipeline progress panel ───────────────────────────────────────────────
function AgentProgress({ events, isRunning, plannerInfo, judgeInfo }) {
  if (!isRunning && !events.length) return null

  const doneEvents = events.filter(e => e.event === 'agent_done')
  const doneCount = doneEvents.length

  return (
    <div className="agent-card mb-6">
      <h3 className="text-sm font-medium text-gray-500 mb-3">⚡ Pipeline Progress</h3>

      {/* Planner info bubble */}
      {plannerInfo && (
        <div className="mb-3 bg-blue-50 rounded-lg px-3 py-2 text-xs text-blue-800">
          <span className="font-medium">🗺️ Planner:</span>{' '}
          <span className="capitalize">{plannerInfo.intent?.replace(/_/g, ' ')}</span>
          {plannerInfo.selected_tools?.length > 0 && (
            <span className="ml-2 text-blue-600">
              → {plannerInfo.selected_tools.join(', ')}
            </span>
          )}
        </div>
      )}

      {/* Node rows — only show nodes that are either done or scheduled by planner */}
      <div className="space-y-2">
        {Object.entries(AGENT_LABELS).map(([key, meta], idx) => {
          const ev = doneEvents.find(e => e.agent === key)
          // Dim nodes the planner didn't select (unless they're done)
          const plannedTools = plannerInfo?.selected_tools || []
          const coreNodes = ['fetching', 'memory', 'planner', 'judge', 'supervisor']
          const isRelevant = coreNodes.includes(key) || plannedTools.includes(key) || !!ev
          if (!isRelevant && plannerInfo) return null

          const isActive = isRunning && !ev && doneCount > 0 &&
            Object.keys(AGENT_LABELS).indexOf(key) === doneCount

          return (
            <div key={key} className="flex items-center gap-3">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                ev ? 'bg-green-100 text-green-700' :
                isActive ? 'bg-blue-100 text-blue-600 animate-pulse' :
                'bg-gray-100 text-gray-400'
              }`}>
                {ev ? '✓' : isActive ? '…' : '·'}
              </div>
              <span className={`text-sm flex-1 ${ev ? 'text-gray-700' : isActive ? 'text-blue-600' : 'text-gray-400'}`}>
                {meta.icon} {meta.label}
              </span>
              {ev?.time_ms != null && (
                <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                  {ev.time_ms < 1000 ? `${Math.round(ev.time_ms)}ms` : `${(ev.time_ms / 1000).toFixed(1)}s`}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Judge verdict bubble (live) */}
      {judgeInfo && (
        <div className={`mt-3 rounded-lg px-3 py-2 text-xs ${VERDICT_STYLE[judgeInfo.verdict] || 'bg-gray-100 text-gray-600'}`}>
          <span className="font-medium">⚖️ Judge:</span>{' '}
          <span className="capitalize">{judgeInfo.verdict}</span>
          {judgeInfo.issues?.length > 0 && (
            <span className="ml-2">— {judgeInfo.issues[0]}</span>
          )}
        </div>
      )}
    </div>
  )
}

// ── Disease detection badge ───────────────────────────────────────────────────
function DiseaseCard({ detection }) {
  if (!detection?.image_provided || !detection?.label) return null
  const isHealthy = detection.label.toLowerCase().includes('healthy')
  return (
    <div className={`rounded-xl border p-4 ${isHealthy ? 'bg-green-50 border-green-200' : 'bg-orange-50 border-orange-200'}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">🔬</span>
        <h3 className="text-sm font-semibold text-gray-800">Disease Analysis</h3>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${isHealthy ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
          {Math.round((detection.confidence || 0) * 100)}% confidence
        </span>
      </div>
      <p className="text-sm font-medium text-gray-800 mb-2">{detection.label}</p>
      {detection.suggestions?.length > 0 && (
        <ul className="space-y-1">
          {detection.suggestions.map((s, i) => (
            <li key={i} className="text-xs text-gray-600 flex gap-2">
              <span className="text-orange-400 flex-shrink-0">•</span>{s}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Judge verdict panel (from saved report) ───────────────────────────────────
function JudgePanel({ judgeOutput }) {
  if (!judgeOutput?.verdict || judgeOutput.verdict === 'pass') return null
  const { verdict, issues = [], confidence_adjustment = 0 } = judgeOutput
  return (
    <div className={`rounded-xl border p-4 mt-4 ${verdict === 'reject' ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'}`}>
      <div className="flex items-center gap-2 mb-2">
        <span>⚖️</span>
        <h3 className="text-sm font-semibold text-gray-800">Judge Review</h3>
        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold capitalize ${VERDICT_STYLE[verdict]}`}>
          {verdict}
        </span>
        {confidence_adjustment !== 0 && (
          <span className="text-xs text-gray-500">
            ({confidence_adjustment > 0 ? '+' : ''}{Math.round(confidence_adjustment * 100)}% confidence)
          </span>
        )}
      </div>
      {issues.length > 0 && (
        <ul className="space-y-1">
          {issues.map((issue, i) => (
            <li key={i} className="text-xs text-amber-800 flex gap-2">
              <span className="flex-shrink-0">⚠️</span>{issue}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Image uploader ─────────────────────────────────────────────────────────────
function useImagePicker() {
  const [imageB64, setImageB64] = useState(null)
  const [imageName, setImageName] = useState(null)

  const pick = (file) => {
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      // Strip data URL prefix to get raw base64
      const raw = e.target.result.split(',')[1]
      setImageB64(raw)
      setImageName(file.name)
    }
    reader.readAsDataURL(file)
  }

  const clear = () => { setImageB64(null); setImageName(null) }

  return { imageB64, imageName, pick, clear }
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { t } = useTranslation()
  const user = useAuthStore(s => s.user)
  const qc = useQueryClient()

  const [streamEvents, setStreamEvents] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [lastCycleId, setLastCycleId] = useState(null)
  const [plannerInfo, setPlannerInfo] = useState(null)
  const [judgeInfo, setJudgeInfo] = useState(null)
  const cancelStreamRef = useRef(null)
  const imageInputRef = useRef(null)
  const { imageB64, imageName, pick, clear: clearImage } = useImagePicker()

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['latest-report'],
    queryFn: getLatestReport,
  })
  const { data: health } = useQuery({
    queryKey: ['farm-health'],
    queryFn: getFarmHealth,
    enabled: !!report?.confidences,
    retry: false,
  })
  const { data: weather } = useQuery({
    queryKey: ['weather'],
    queryFn: getWeather,
    select: (d) => d?.today,
  })
  const { data: pricesData } = useQuery({ queryKey: ['prices'], queryFn: getCropPrices })

  const runMutation = useMutation({
    mutationFn: () => runAgentCycle(imageB64),
    onSuccess: (data) => {
      const cycleId = data.cycle_id
      setLastCycleId(cycleId)
      setStreamEvents([])
      setPlannerInfo(null)
      setJudgeInfo(null)
      setIsStreaming(true)
      clearImage()

      cancelStreamRef.current = streamCycle(
        cycleId,
        (event) => {
          setStreamEvents(prev => [...prev, event])
          if (event.event === 'planner') setPlannerInfo(event)
          if (event.event === 'judge') setJudgeInfo(event)
        },
        () => {
          setIsStreaming(false)
          qc.invalidateQueries({ queryKey: ['latest-report'] })
          qc.invalidateQueries({ queryKey: ['farm-health'] })
          qc.invalidateQueries({ queryKey: ['notifications'] })
          qc.invalidateQueries({ queryKey: ['unread-count'] })
        },
      )
    },
  })

  // Cancel stream on unmount
  useEffect(() => () => cancelStreamRef.current?.(), [])

  const isRunning = runMutation.isPending || isStreaming
  const report_ = report?.cycle ? report : report
  const confidences = report_?.confidences
  const timings = report_?.agent_timings

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" style={{fontFamily:"'Plus Jakarta Sans',sans-serif"}}>{t('dashboard.title')}</h1>
          <p className="text-gray-500 text-sm mt-1">
            Welcome back, <span className="font-medium text-gray-700">{user?.username}</span> · {user?.location || 'Northeast India'}
          </p>
        </div>

        {/* Run controls */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Hidden file input for leaf image */}
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={e => pick(e.target.files?.[0])}
          />

          {/* Image attach button */}
          {!isRunning && (
            imageName ? (
              <div className="flex items-center gap-1 text-xs bg-orange-50 border border-orange-200 rounded-lg px-3 py-2">
                <span>🔬</span>
                <span className="text-orange-700 max-w-24 truncate">{imageName}</span>
                <button onClick={clearImage} className="text-gray-400 hover:text-gray-600 ml-1">✕</button>
              </div>
            ) : (
              <button
                onClick={() => imageInputRef.current?.click()}
                className="text-xs text-gray-500 border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-50 flex items-center gap-1"
                title="Attach a leaf image for disease analysis"
              >
                <span>📷</span> Add leaf image
              </button>
            )
          )}

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
      </div>

      {/* SSE pipeline progress */}
      <AgentProgress
        events={streamEvents}
        isRunning={isStreaming}
        plannerInfo={plannerInfo}
        judgeInfo={judgeInfo}
      />

      {/* Top cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <WeatherCard weather={weather} />
        <PriceCard prices={pricesData} decisions={report_?.sell_hold_decisions} />
      </div>

      {/* Intelligence row */}
      {(health || confidences || timings) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <FarmHealthCard health={health} />
          <ConfidenceCard confidences={confidences} timings={timings} />
        </div>
      )}

      {/* Disease detection (if image was used last cycle) */}
      {report_?.disease_detection?.image_provided && (
        <div className="mb-6">
          <DiseaseCard detection={report_.disease_detection} />
        </div>
      )}

      {/* Planner summary from saved report */}
      {report_?.planner_decision?.selected_tools?.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-gray-400">Last cycle used:</span>
          {report_.planner_decision.selected_tools.map(t => (
            <span key={t} className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full capitalize">
              {AGENT_LABELS[t]?.icon || '⚙️'} {t}
            </span>
          ))}
          {report_.intent && (
            <span className="text-gray-400 ml-1">
              · intent: <span className="italic capitalize">{report_.intent.replace(/_/g, ' ')}</span>
            </span>
          )}
        </div>
      )}

      {/* Agent Report */}
      <div className="agent-card">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h2 className="font-semibold text-gray-900">{t('dashboard.latest_report')}</h2>
          <div className="flex items-center gap-2 flex-wrap">
            {confidences?.supervisor != null && (
              <span className="text-xs text-gray-500">
                {Math.round(confidences.supervisor * 100)}% confidence
              </span>
            )}
            {report_?.status && (
              <span className={`text-xs px-2 py-1 rounded-full ${
                report_.status === 'completed' ? 'bg-green-100 text-green-700' :
                report_.status === 'partial'   ? 'bg-yellow-100 text-yellow-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {report_.status}
              </span>
            )}
            {lastCycleId && !isStreaming && (
              <Link
                to={`/trace/${lastCycleId}`}
                className="text-xs text-blue-600 hover:text-blue-800 underline underline-offset-2"
              >
                View Trace →
              </Link>
            )}
          </div>
        </div>

        {reportLoading ? (
          <p className="text-gray-400 text-sm">{t('common.loading')}</p>
        ) : report_?.final_report ? (
          <>
            <div className="bg-gray-50 rounded-xl p-4">
              <Markdown text={report_.final_report} />
            </div>

            {/* Judge verdict panel */}
            <JudgePanel judgeOutput={report_.judge_output} />

            {report_.recommendations?.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">🎯 {t('dashboard.recommendations')}</h3>
                <div className="space-y-2">
                  {report_.recommendations.map((rec, i) => (
                    <div key={i} className="flex gap-3">
                      <span className="w-5 h-5 rounded-full bg-green-100 text-green-700 text-xs flex items-center justify-center flex-shrink-0 font-semibold mt-0.5" style={{fontFamily:"'Plus Jakarta Sans',sans-serif"}}>
                        {i + 1}
                      </span>
                      <div className="flex-1"><Markdown text={rec} /></div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report_.alerts?.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">⚠️ {t('dashboard.alerts')}</h3>
                <div className="space-y-2">
                  {report_.alerts.map((alert, i) => (
                    <div key={i} className="alert-warning">
                      <Markdown text={alert} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report_.best_selling_window && (
              <div className="mt-4 text-sm text-gray-600 bg-blue-50 rounded-lg p-3">
                📅 <span className="font-medium">Best Selling Window:</span> {report_.best_selling_window}
              </div>
            )}

            {report_.rag_sources?.length > 0 && (
              <div className="mt-4">
                <h3 className="text-xs font-semibold text-gray-500 mb-2">📚 Sources ({report_.rag_sources.length})</h3>
                <div className="flex flex-wrap gap-2">
                  {report_.rag_sources.map((src, i) => (
                    <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                      {src.source || src.tag || `Source ${i + 1}`}
                    </span>
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
