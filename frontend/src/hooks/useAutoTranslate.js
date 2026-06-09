/**
 * useAutoTranslate
 *
 * When the user switches to a non-English language this hook:
 *   1. Checks localStorage for a cached translation bundle (instant).
 *   2. If not cached, sends all English strings to the backend NLLB-200
 *      endpoint (POST /translate/) and caches the result.
 *   3. Injects the translated bundle into i18next and triggers a re-render.
 *
 * NLLB-200 (facebook/nllb-200-distilled-600M) runs on the server and supports
 * Hindi, Assamese, Bengali, Nepali, Manipuri, and Mizo out of the box.
 *
 * Translation is a one-time cost per language — after caching it's instant.
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Separate axios instance — no auth header needed for /translate/ (public endpoint)
const translateClient = axios.create({ baseURL: BASE_URL, timeout: 180_000 })

const SUPPORTED_LANGS = ['hi', 'as', 'bn', 'ne', 'mni', 'lus']

// Cache key versioned so future English source changes invalidate old caches
const CACHE_KEY = (lang) => `agrow_t9n_v2_${lang}`

function flattenObj(obj, prefix = '') {
  const out = {}
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      Object.assign(out, flattenObj(v, key))
    } else {
      out[key] = String(v)
    }
  }
  return out
}

function unflattenObj(flat) {
  const out = {}
  for (const [key, val] of Object.entries(flat)) {
    const parts = key.split('.')
    let cur = out
    for (let i = 0; i < parts.length - 1; i++) {
      if (typeof cur[parts[i]] !== 'object') cur[parts[i]] = {}
      cur = cur[parts[i]]
    }
    cur[parts[parts.length - 1]] = val
  }
  return out
}

// Global set — prevents duplicate in-flight fetches across hook instances
const _pending = new Set()

export function useAutoTranslate() {
  const { i18n } = useTranslation()
  const [isTranslating, setIsTranslating] = useState(false)
  const [error, setError] = useState(null)
  // Track loaded langs so we don't re-load after bundle is injected
  const loadedRef = useRef(new Set(['en']))

  useEffect(() => {
    const lang = i18n.language

    if (!SUPPORTED_LANGS.includes(lang)) return
    if (loadedRef.current.has(lang)) return
    if (_pending.has(lang)) return

    setError(null)

    // Try localStorage cache first (instant, no network)
    const cached = localStorage.getItem(CACHE_KEY(lang))
    if (cached) {
      try {
        const bundle = JSON.parse(cached)
        i18n.addResourceBundle(lang, 'translation', bundle, true, true)
        i18n.changeLanguage(lang)         // re-trigger so components re-render
        loadedRef.current.add(lang)
        return
      } catch {
        localStorage.removeItem(CACHE_KEY(lang))
      }
    }

    // Fetch from backend NLLB-200
    _pending.add(lang)
    setIsTranslating(true)

    const enBundle  = i18n.getResourceBundle('en', 'translation')
    const flat      = flattenObj(enBundle)
    const keys      = Object.keys(flat)
    const values    = keys.map(k => flat[k])

    translateClient
      .post('/translate/', { texts: values, target_lang: lang })
      .then(({ data }) => {
        const translatedFlat = {}
        keys.forEach((k, i) => { translatedFlat[k] = data.translations[i] ?? flat[k] })
        const bundle = unflattenObj(translatedFlat)

        i18n.addResourceBundle(lang, 'translation', bundle, true, true)
        i18n.changeLanguage(lang)
        loadedRef.current.add(lang)
        localStorage.setItem(CACHE_KEY(lang), JSON.stringify(bundle))
      })
      .catch(err => {
        console.error(`[useAutoTranslate] Failed to translate to ${lang}:`, err)
        setError(`Translation to ${lang} failed — showing English. Is the backend running?`)
      })
      .finally(() => {
        _pending.delete(lang)
        setIsTranslating(false)
      })
  }, [i18n.language])

  return { isTranslating, error }
}
