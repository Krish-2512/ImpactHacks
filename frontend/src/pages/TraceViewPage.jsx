import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getTrace } from '../api/intelligence'

// ── Verdict badge ──────────────────────────────────────────────────────────────
const VERDICT_STYLE = {
  pass:   'bg-green-100 text-green-700',
  flag:   'bg-yellow-100 text-yellow-700',
  reject: 'bg-red-100   text-red-700',
}

function VerdictBadge({ verdict }) {
  const cls = VERDICT_STYLE[verdict] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full uppercase ${cls}`}>
      {verdict || 'pass'}
    </span>
  )
}

// ── Duration helpers ───────────────────────────────────────────────────────────
function fmtMs(ms) {
  if (!ms && ms !== 0) return '—'
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2)}s`
}

function fmtPct(v) {
  return v != null ? `${Math.round(v * 100)}%` : '—'
}

// ── Node colour palette ────────────────────────────────────────────────────────
const NODE_COLOR = {
  memory:    { bg: 'bg-purple-50',  border: 'border-purple-200', icon: '🧠' },
  planner:   { bg: 'bg-blue-50',    border: 'border-blue-200',   icon: '🗺️' },
  weather:   { bg: 'bg-sky-50',     border: 'border-sky-200',    icon: '🌤️' },
  market:    { bg: 'bg-emerald-50', border: 'border-emerald-200',icon: '📈' },
  advisory:  { bg: 'bg-lime-50',    border: 'border-lime-200',   icon: '🌿' },
  disease:   { bg: 'bg-orange-50',  border: 'border-orange-200', icon: '🔬' },
  multimodal:{ bg: 'bg-amber-50',   border: 'border-amber-200',  icon: '🖼️' },
  schemes:   { bg: 'bg-indigo-50',  border: 'border-indigo-200', icon: '📋' },
  judge:     { bg: 'bg-red-50',     border: 'border-red-200',    icon: '⚖️' },
  supervisor:{ bg: 'bg-gray-50',    border: 'border-gray-200',   icon: '🤖' },
}

// ── Single DAG node card ───────────────────────────────────────────────────────
function NodeCard({ tt, isExpanded, onToggle }) {
  const colors = NODE_COLOR[tt.tool] || { bg: 'bg-gray-50', border: 'border-gray-200', icon: '⚙️' }
  const confColor = tt.confidence >= 0.8 ? 'text-green-600' : tt.confidence >= 0.6 ? 'text-yellow-600' : tt.confidence > 0 ? 'text-red-500' : 'text-gray-400'

  return (
    <div
      className={`rounded-xl border-2 ${colors.bg} ${colors.border} p-3 cursor-pointer select-none transition-shadow hover:shadow-md`}
      style={{ minWidth: 130 }}
      onClick={onToggle}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{colors.icon}</span>
        <span className="text-xs font-semibold text-gray-700 capitalize">{tt.tool}</span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400">{fmtMs(tt.duration_ms)}</span>
        {tt.confidence > 0 && <span className={`font-semibold ${confColor}`}>{fmtPct(tt.confidence)}</span>}
      </div>

      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-gray-200 text-xs space-y-2">
          {tt.input_summary && (
            <div>
              <span className="text-gray-500 font-medium">Input:</span>
              <p className="text-gray-700 mt-0.5 break-words">{tt.input_summary}</p>
            </div>
          )}
          {tt.output_summary && (
            <div>
              <span className="text-gray-500 font-medium">Output:</span>
              <p className="text-gray-700 mt-0.5 break-words">{tt.output_summary}</p>
            </div>
          )}
          {tt.error && (
            <div className="text-red-600 bg-red-50 px-2 py-1 rounded">
              Error: {tt.error}
            </div>
          )}
          {tt.input_tokens_est > 0 && (
            <div className="text-gray-400">
              ~{tt.input_tokens_est + (tt.output_tokens_est || 0)} tokens est.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Execution DAG ──────────────────────────────────────────────────────────────
function ExecutionDAG({ trace }) {
  const [expanded, setExpanded] = useState({})
  const toggle = (tool) => setExpanded(p => ({ ...p, [tool]: !p[tool] }))

  const tts = trace.tool_traces || []
  const ttMap = Object.fromEntries(tts.map(t => [t.tool, t]))

  // Build pipeline display order from planner_decision if available
  const selected = trace.planner_decision?.selected_tools || []
  // Tool groups: memory + planner first, then parallel selected tools, then judge + supervisor
  const parallelGroups = trace.planner_decision?.parallel_groups || [selected.filter(t => !['memory','planner','judge','supervisor'].includes(t))]

  const arrowStyle = 'text-gray-300 text-2xl font-thin mx-1'

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex items-start gap-2 min-w-max">
        {/* Memory */}
        {ttMap.memory && (
          <>
            <NodeCard tt={ttMap.memory} isExpanded={!!expanded.memory} onToggle={() => toggle('memory')} />
            <div className={arrowStyle}>→</div>
          </>
        )}

        {/* Planner */}
        {ttMap.planner && (
          <>
            <NodeCard tt={ttMap.planner} isExpanded={!!expanded.planner} onToggle={() => toggle('planner')} />
            <div className={arrowStyle}>→</div>
          </>
        )}

        {/* Parallel tool groups */}
        {parallelGroups.filter(g => g.length).map((group, gi) => (
          <div key={gi} className="flex items-start gap-2">
            <div className="flex flex-col gap-2">
              {group.map(tool => {
                const tt = ttMap[tool] || { tool, duration_ms: 0, confidence: 0 }
                return (
                  <NodeCard key={tool} tt={tt} isExpanded={!!expanded[tool]} onToggle={() => toggle(tool)} />
                )
              })}
            </div>
            <div className={`${arrowStyle} self-center`}>→</div>
          </div>
        ))}

        {/* Judge */}
        {ttMap.judge && (
          <>
            <NodeCard tt={ttMap.judge} isExpanded={!!expanded.judge} onToggle={() => toggle('judge')} />
            <div className={arrowStyle}>→</div>
          </>
        )}

        {/* Supervisor */}
        {ttMap.supervisor && (
          <NodeCard tt={ttMap.supervisor} isExpanded={!!expanded.supervisor} onToggle={() => toggle('supervisor')} />
        )}
      </div>
    </div>
  )
}

// ── Timeline bar chart ─────────────────────────────────────────────────────────
function TimelineChart({ trace }) {
  const tts = (trace.tool_traces || []).filter(t => t.duration_ms > 0)
  const total = trace.total_duration_ms || tts.reduce((s, t) => s + t.duration_ms, 0) || 1

  const TOOL_COLORS = {
    memory: '#a78bfa', planner: '#60a5fa', weather: '#38bdf8', market: '#34d399',
    advisory: '#86efac', disease: '#fb923c', multimodal: '#fbbf24', schemes: '#818cf8',
    judge: '#f87171', supervisor: '#9ca3af',
  }

  return (
    <div className="space-y-2">
      {tts.map(tt => {
        const pct = Math.max(1, (tt.duration_ms / total) * 100)
        const color = TOOL_COLORS[tt.tool] || '#9ca3af'
        const icon = NODE_COLOR[tt.tool]?.icon || '⚙️'
        return (
          <div key={tt.tool} className="flex items-center gap-3">
            <div className="w-24 text-xs text-gray-600 capitalize flex-shrink-0">
              {icon} {tt.tool}
            </div>
            <div className="flex-1 h-5 bg-gray-100 rounded overflow-hidden">
              <div
                className="h-full rounded text-white text-xs flex items-center pl-2 transition-all"
                style={{ width: `${pct}%`, backgroundColor: color, minWidth: 32 }}
              >
                {fmtMs(tt.duration_ms)}
              </div>
            </div>
          </div>
        )
      })}
      <div className="text-xs text-gray-400 text-right">Total: {fmtMs(total)}</div>
    </div>
  )
}

// ── Judge panel ────────────────────────────────────────────────────────────────
function JudgePanel({ judgeOutput }) {
  if (!judgeOutput || !judgeOutput.verdict) return null
  const { verdict, issues = [], confidence_adjustment = 0, revised_recommendations = [] } = judgeOutput
  return (
    <div className="agent-card">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-lg">⚖️</span>
        <h2 className="font-semibold text-gray-900">Judge Review</h2>
        <VerdictBadge verdict={verdict} />
        {confidence_adjustment !== 0 && (
          <span className="text-xs text-gray-500">
            Confidence adjusted by {confidence_adjustment > 0 ? '+' : ''}{(confidence_adjustment * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {issues.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Issues Found</h3>
          <div className="space-y-1">
            {issues.map((issue, i) => (
              <div key={i} className="text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg flex gap-2">
                <span>⚠️</span><span>{issue}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {revised_recommendations.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Revised Recommendations</h3>
          <div className="space-y-1">
            {revised_recommendations.map((rec, i) => (
              <div key={i} className="flex gap-2 text-sm">
                <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs flex items-center justify-center flex-shrink-0 font-medium">{i + 1}</span>
                <span className="text-gray-700">{rec}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Token usage ────────────────────────────────────────────────────────────────
function TokenUsage({ trace }) {
  const tts = trace.tool_traces || []
  const total = trace.total_tokens_estimated || 0
  if (!total && !tts.length) return null

  return (
    <div className="agent-card">
      <h2 className="font-semibold text-gray-900 mb-4">🔢 Token Usage (estimated)</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="text-center bg-gray-50 rounded-lg p-3">
          <div className="text-xl font-bold text-gray-800">{total.toLocaleString()}</div>
          <div className="text-xs text-gray-500 mt-1">Total tokens</div>
        </div>
        <div className="text-center bg-gray-50 rounded-lg p-3">
          <div className="text-xl font-bold text-gray-800">{trace.rag_sources_count ?? 0}</div>
          <div className="text-xs text-gray-500 mt-1">RAG sources</div>
        </div>
        <div className="text-center bg-gray-50 rounded-lg p-3">
          <div className="text-xl font-bold text-gray-800">{trace.memory_entries_used ?? 0}</div>
          <div className="text-xs text-gray-500 mt-1">Memory entries</div>
        </div>
        <div className="text-center bg-gray-50 rounded-lg p-3">
          <div className={`text-xl font-bold ${trace.final_confidence >= 0.8 ? 'text-green-600' : trace.final_confidence >= 0.6 ? 'text-yellow-600' : 'text-red-500'}`}>
            {fmtPct(trace.final_confidence)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Final confidence</div>
        </div>
      </div>

      {tts.some(t => t.input_tokens_est > 0) && (
        <div className="space-y-1">
          {tts.filter(t => t.input_tokens_est > 0 || t.output_tokens_est > 0).map(tt => (
            <div key={tt.tool} className="flex items-center justify-between text-xs text-gray-600">
              <span className="capitalize">{NODE_COLOR[tt.tool]?.icon || '⚙️'} {tt.tool}</span>
              <span className="text-gray-400">
                in: {tt.input_tokens_est} · out: {tt.output_tokens_est}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────
import { useState } from 'react'

export default function TraceViewPage() {
  const { cycleId } = useParams()

  const { data: trace, isLoading, error } = useQuery({
    queryKey: ['trace', cycleId],
    queryFn: () => getTrace(cycleId),
    enabled: !!cycleId,
    retry: 1,
  })

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12 text-center">
        <div className="text-4xl mb-3 animate-spin inline-block">⚙️</div>
        <p className="text-gray-500">Loading execution trace…</p>
      </div>
    )
  }

  if (error || !trace) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12 text-center">
        <div className="text-4xl mb-3">⚠️</div>
        <p className="text-gray-500 mb-4">
          {error?.response?.status === 404
            ? 'No trace found for this cycle. The trace may not have been saved yet.'
            : 'Failed to load trace.'}
        </p>
        <Link to="/dashboard" className="btn-primary inline-block">← Back to Dashboard</Link>
      </div>
    )
  }

  const statusColor = {
    completed: 'bg-green-100 text-green-700',
    partial:   'bg-yellow-100 text-yellow-700',
    failed:    'bg-red-100 text-red-700',
  }[trace.status] || 'bg-gray-100 text-gray-600'

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <Link to="/dashboard" className="text-sm text-gray-400 hover:text-gray-600 mb-1 inline-block">
            ← Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Execution Trace</h1>
          <p className="text-xs text-gray-400 font-mono mt-1">{cycleId}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className={`text-xs font-semibold px-3 py-1 rounded-full capitalize ${statusColor}`}>
            {trace.status}
          </span>
          <span className="text-xs text-gray-400">
            {trace.timestamp ? new Date(trace.timestamp).toLocaleString() : ''}
          </span>
        </div>
      </div>

      {/* Intent + planner summary */}
      {trace.intent && (
        <div className="agent-card">
          <h2 className="font-semibold text-gray-900 mb-3">🗺️ Planner Decision</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wide">Intent</span>
              <p className="font-medium text-gray-800 mt-1 capitalize">{trace.intent.replace(/_/g, ' ')}</p>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wide">Tools Selected</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {(trace.planner_decision?.selected_tools || []).map(t => (
                  <span key={t} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full capitalize">{t}</span>
                ))}
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wide">Reasoning</span>
              <p className="text-gray-600 mt-1 text-xs">{trace.planner_decision?.reasoning || '—'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Execution DAG */}
      <div className="agent-card">
        <h2 className="font-semibold text-gray-900 mb-4">🔀 Execution Graph</h2>
        <p className="text-xs text-gray-400 mb-4">Click any node to expand details.</p>
        <ExecutionDAG trace={trace} />
      </div>

      {/* Timeline */}
      <div className="agent-card">
        <h2 className="font-semibold text-gray-900 mb-4">⏱️ Timeline</h2>
        <TimelineChart trace={trace} />
      </div>

      {/* Judge panel */}
      <JudgePanel judgeOutput={trace.judge_output} />

      {/* Token usage */}
      <TokenUsage trace={trace} />
    </div>
  )
}
