import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { queryCropAdvisory } from '../api/rag'

const EXAMPLES = ['advisory.ex1', 'advisory.ex2', 'advisory.ex3']

export default function AdvisoryPage() {
  const { t } = useTranslation()
  const [query, setQuery]     = useState('')
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [history, setHistory] = useState([])

  const handleSubmit = async (q) => {
    const searchQ = q || query
    if (!searchQ.trim()) return
    setLoading(true)
    setError('')
    try {
      const data = await queryCropAdvisory(searchQ)
      const entry = { q: searchQ, answer: data.answer, sources: data.sources_used }
      setHistory(h => [entry, ...h])
      setResult(entry)
      setQuery('')
    } catch {
      setError(t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">{t('advisory.title')}</h1>
      <p className="text-gray-500 text-sm mb-6">Powered by our agricultural knowledge base</p>

      {/* Search */}
      <div className="agent-card mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            placeholder={t('advisory.placeholder')}
            className="flex-1 px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
          />
          <button
            onClick={() => handleSubmit()}
            disabled={loading || !query.trim()}
            className="btn-primary whitespace-nowrap"
          >
            {loading ? '...' : t('advisory.search')}
          </button>
        </div>

        {/* Example queries */}
        <div className="mt-4">
          <p className="text-xs text-gray-400 mb-2">{t('advisory.examples')}</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map(key => (
              <button
                key={key}
                onClick={() => handleSubmit(t(key))}
                className="text-xs bg-green-50 text-green-700 px-3 py-1.5 rounded-full hover:bg-green-100 transition-colors"
              >
                {t(key)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-8 text-gray-400">
          <div className="animate-spin text-3xl mb-2">⚙️</div>
          <p className="text-sm">{t('advisory.searching')}</p>
        </div>
      )}

      {/* Error */}
      {error && <div className="alert-urgent mb-4">{error}</div>}

      {/* Result */}
      {result && !loading && (
        <div className="agent-card">
          <div className="flex items-start gap-3 mb-4">
            <span className="text-2xl">🤖</span>
            <div className="flex-1">
              <div className="text-xs text-gray-400 mb-1">
                Your question: <span className="text-gray-600">{result.q}</span>
              </div>
              {result.sources > 0 && (
                <div className="text-xs text-green-600">📚 {result.sources} knowledge base sources used</div>
              )}
            </div>
          </div>
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap bg-gray-50 rounded-xl p-4">
            {result.answer}
          </div>
        </div>
      )}

      {/* History */}
      {history.length > 1 && (
        <div className="mt-6">
          <h2 className="text-sm font-medium text-gray-500 mb-3">Previous questions</h2>
          <div className="space-y-3">
            {history.slice(1).map((h, i) => (
              <button
                key={i}
                onClick={() => setResult(h)}
                className="w-full text-left agent-card hover:border-green-200 transition-colors text-sm"
              >
                <div className="text-gray-600 font-medium truncate">❓ {h.q}</div>
                <div className="text-gray-400 text-xs mt-1 line-clamp-2">{h.answer.substring(0, 100)}...</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
