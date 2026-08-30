import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useTranslation } from 'react-i18next'
import { detectDisease } from '../api/disease'

function ConfidenceBar({ value }) {
  const color = value > 80 ? 'bg-green-500' : value > 50 ? 'bg-yellow-500' : 'bg-red-400'
  return (
    <div className="w-full bg-gray-100 rounded-full h-2">
      <div className={`h-2 rounded-full ${color} transition-all`} style={{ width: `${value}%` }} />
    </div>
  )
}

export default function DiseasePage() {
  const { t } = useTranslation()
  const [preview, setPreview]   = useState(null)
  const [result, setResult]     = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  const onDrop = useCallback(async (files) => {
    const file = files[0]
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setResult(null)
    setError('')
    setLoading(true)
    try {
      const data = await detectDisease(file)
      setResult(data.result)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || `Detection failed (${err.message || 'network error'}). The model may be loading — wait 30 seconds and try again.`)
    } finally {
      setLoading(false)
    }
  }, [t])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxFiles: 1,
  })

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">{t('disease.title')}</h1>
      <p className="text-gray-500 text-sm mb-8">{t('disease.tip')}</p>

      {/* Upload zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-green-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        {preview ? (
          <img src={preview} alt="preview" className="max-h-48 mx-auto rounded-xl object-cover mb-4" />
        ) : (
          <div className="text-5xl mb-4">🍃</div>
        )}
        <p className="text-gray-500 text-sm">{t('disease.upload_prompt')}</p>
        <p className="text-xs text-gray-400 mt-2">JPG, PNG, WebP up to 10MB</p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="mt-8 text-center">
          <div className="inline-flex items-center gap-3 text-gray-600">
            <span className="animate-spin text-2xl">⚙️</span>
            <span>{t('disease.analyzing')}</span>
          </div>
          <p className="text-xs text-gray-400 mt-2">First detection loads the AI model (~20–40 sec)</p>
        </div>
      )}

      {/* Error */}
      {error && <div className="alert-urgent mt-6">{error}</div>}

      {/* Result */}
      {result && !loading && (
        <div className="mt-8 agent-card">
          <h2 className="font-semibold text-gray-900 mb-6 flex items-center gap-2">
            <span className="text-xl">{result.is_healthy ? '✅' : '⚠️'}</span>
            {t('disease.result')}
          </h2>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="text-xs text-gray-500 mb-1">{t('disease.crop')}</div>
                <div className="font-semibold text-gray-900 capitalize">{result.crop}</div>
              </div>
              <div className={`rounded-xl p-4 ${result.is_healthy ? 'bg-green-50' : 'bg-red-50'}`}>
                <div className="text-xs text-gray-500 mb-1">{t('disease.disease')}</div>
                <div className={`font-semibold capitalize ${result.is_healthy ? 'text-green-700' : 'text-red-700'}`}>
                  {result.is_healthy ? t('disease.healthy') : result.disease}
                </div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500">{t('disease.confidence')}</span>
                <span className="font-semibold">{result.confidence}%</span>
              </div>
              <ConfidenceBar value={result.confidence} />
            </div>

            {!result.is_healthy && (
              <div className={`rounded-xl p-4 ${result.severity === 'urgent' ? 'bg-red-50 border border-red-200' : 'bg-amber-50 border border-amber-200'}`}>
                <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
                  {t('disease.treatment')}
                </div>
                <p className="text-sm text-gray-700 leading-relaxed">{result.treatment}</p>
              </div>
            )}

            {result.all_predictions?.length > 1 && (
              <div>
                <div className="text-xs text-gray-500 mb-2 font-medium">Other possibilities:</div>
                <div className="space-y-1">
                  {result.all_predictions.slice(1).map((p, i) => (
                    <div key={i} className="flex justify-between text-xs text-gray-500">
                      <span className="capitalize">{p.label.replace(/_/g, ' ')}</span>
                      <span>{p.confidence}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
