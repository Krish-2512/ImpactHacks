import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'

// ── Data ──────────────────────────────────────────────────────────────────────
const STATS = [
  { value: '10',   label: 'Crops tracked',    sub: 'SARIMAX + XGBoost' },
  { value: '8',    label: 'ML models',         sub: 'SHAP explained' },
  { value: '38',   label: 'Disease classes',   sub: 'MobileNetV2' },
  { value: '7',    label: 'Languages',          sub: 'Real-time translation' },
]

const CROPS = [
  { icon: '🍅', name: 'Tomato',   status: 'SELL', price: '₹7,226' },
  { icon: '🍆', name: 'Brinjal',  status: 'SELL', price: '₹4,032' },
  { icon: '🥬', name: 'Cabbage',  status: 'HOLD', price: '₹10,808' },
  { icon: '🍋', name: 'Lemon',    status: 'WAIT', price: '₹1,156' },
  { icon: '🥔', name: 'Potato',   status: 'HOLD', price: '₹1,483' },
  { icon: '🧅', name: 'Onion',    status: 'HOLD', price: '₹1,680' },
  { icon: '🫚', name: 'Ginger',   status: 'HOLD', price: '₹10,678' },
  { icon: '🌿', name: 'Turmeric', status: 'HOLD', price: '₹12,508' },
  { icon: '🌶️', name: 'Chili',   status: 'SELL', price: '₹7,119' },
  { icon: '🧄', name: 'Garlic',   status: 'HOLD', price: '₹4,622' },
]

const STATUS_COLOR = {
  SELL: { bg: '#dcfce7', text: '#15803d' },
  HOLD: { bg: '#fef9c3', text: '#854d0e' },
  WAIT: { bg: '#dbeafe', text: '#1d4ed8' },
}

const FEATURES = [
  {
    icon: '🤖',
    color: '#1a6b3c',
    bg: '#f0fdf4',
    title: 'Multi-Agent AI Pipeline',
    desc: 'LangGraph orchestrates 9 specialized agents — planner, weather, market, advisory, judge — running in parallel for your daily farm intelligence report.',
  },
  {
    icon: '📈',
    color: '#1d4ed8',
    bg: '#eff6ff',
    title: 'AI Crop Price Predictions',
    desc: 'SARIMAX time-series + XGBoost models predict next-week prices for 10 crops. SELL / HOLD / WAIT decisions with SHAP explainability.',
  },
  {
    icon: '🔬',
    color: '#7c3aed',
    bg: '#f5f3ff',
    title: 'Leaf Disease Detection',
    desc: 'Upload a leaf photo. MobileNetV2 classifies 38 plant diseases in under 2 seconds and immediately cross-references treatment from the RAG knowledge base.',
  },
  {
    icon: '📚',
    color: '#b45309',
    bg: '#fffbeb',
    title: 'Hybrid RAG Advisory',
    desc: 'BM25 + dense vector fusion with Reciprocal Rank Fusion retrieves the most relevant agronomic knowledge from ICAR guides for Northeast India crops.',
  },
  {
    icon: '🧠',
    color: '#0e7490',
    bg: '#ecfeff',
    title: 'Semantic Farm Memory',
    desc: 'Every cycle writes a memory embedding to Qdrant. Future cycles retrieve what actually happened on your farm months ago — not just recent entries.',
  },
  {
    icon: '🌤️',
    color: '#0369a1',
    bg: '#f0f9ff',
    title: 'Live Weather + Alerts',
    desc: 'Open-Meteo real-time API delivers hyperlocal conditions. Weather risk crosses with market timing to surface pest warnings and irrigation schedules.',
  },
]

const PIPELINE = [
  { icon: '📡', label: 'Fetch' },
  { icon: '🧠', label: 'Memory' },
  { icon: '🗺️', label: 'Planner' },
  { icon: '🌤️', label: 'Weather' },
  { icon: '📈', label: 'Market' },
  { icon: '🌿', label: 'Advisory' },
  { icon: '⚖️', label: 'Judge' },
  { icon: '🤖', label: 'Report' },
]

const NE_STATES = ['Assam', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Tripura', 'Sikkim', 'Arunachal Pradesh']

const fade = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true },
  transition: { duration: 0.5, delay },
})

// ── Shared section header ─────────────────────────────────────────────────────
function SectionHead({ eyebrow, title, sub }) {
  return (
    <motion.div {...fade()} className="text-center mb-14">
      {eyebrow && (
        <p className="text-xs font-bold tracking-[0.18em] uppercase text-green-600 mb-3">
          {eyebrow}
        </p>
      )}
      <h2 style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.03em', color: '#0f172a', marginBottom: '0.5rem' }}>
        {title}
      </h2>
      {sub && <p style={{ color: '#64748b', fontSize: '1rem', maxWidth: 520, margin: '0 auto' }}>{sub}</p>}
    </motion.div>
  )
}

// ── Live price ticker strip ───────────────────────────────────────────────────
function PriceTicker() {
  const repeated = [...CROPS, ...CROPS]
  return (
    <div style={{ overflow: 'hidden', background: 'rgba(255,255,255,0.08)', borderTop: '1px solid rgba(255,255,255,0.12)', borderBottom: '1px solid rgba(255,255,255,0.12)', padding: '10px 0' }}>
      <motion.div
        style={{ display: 'flex', gap: 32, width: 'max-content' }}
        animate={{ x: ['0%', '-50%'] }}
        transition={{ duration: 30, ease: 'linear', repeat: Infinity }}
      >
        {repeated.map((c, i) => {
          const s = STATUS_COLOR[c.status]
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap' }}>
              <span style={{ fontSize: 16 }}>{c.icon}</span>
              <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13, fontWeight: 500 }}>{c.name}</span>
              <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.6)' }}>{c.price}</span>
              <span style={{ background: s.bg, color: s.text, fontSize: 10, fontWeight: 700, padding: '1px 7px', borderRadius: 99, fontFamily: "'Plus Jakarta Sans', sans-serif", letterSpacing: '0.03em' }}>
                {c.status}
              </span>
            </div>
          )
        })}
      </motion.div>
    </div>
  )
}

// ── Agent pipeline viz ────────────────────────────────────────────────────────
function PipelineViz() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 0, marginTop: 8 }}>
      {PIPELINE.map((node, i) => (
        <motion.div
          key={node.label}
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.06 }}
          style={{ display: 'flex', alignItems: 'center' }}
        >
          <div style={{
            background: '#fff',
            border: '1.5px solid #e2e8f0',
            borderRadius: 12,
            padding: '8px 12px',
            textAlign: 'center',
            minWidth: 60,
            boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          }}>
            <div style={{ fontSize: 18 }}>{node.icon}</div>
            <div style={{ fontSize: 10, color: '#64748b', fontWeight: 600, marginTop: 2, fontFamily: "'Plus Jakarta Sans', sans-serif", letterSpacing: '0.02em' }}>
              {node.label}
            </div>
          </div>
          {i < PIPELINE.length - 1 && (
            <div style={{ color: '#94a3b8', fontSize: 14, margin: '0 2px', marginTop: -4 }}>→</div>
          )}
        </motion.div>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function LandingPage() {
  const { t } = useTranslation()

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc' }}>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section style={{
        background: 'linear-gradient(135deg, #052e16 0%, #14532d 45%, #166534 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Subtle dot grid */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.07,
          backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)',
          backgroundSize: '28px 28px',
          pointerEvents: 'none',
        }} />

        {/* Glow blobs */}
        <div style={{ position: 'absolute', top: '-20%', right: '-10%', width: 600, height: 600, borderRadius: '50%', background: 'radial-gradient(circle, rgba(74,222,128,0.12) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: '-10%', left: '-5%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%)', pointerEvents: 'none' }} />

        {/* Content */}
        <div style={{ maxWidth: 900, margin: '0 auto', padding: '80px 24px 60px', textAlign: 'center', position: 'relative' }}>
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.65 }}>

            {/* Eyebrow badge */}
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(8px)',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: 99, padding: '6px 16px', marginBottom: 28,
              fontSize: 13, color: 'rgba(255,255,255,0.9)', fontWeight: 500,
            }}>
              <span style={{ width: 7, height: 7, background: '#4ade80', borderRadius: '50%', display: 'inline-block', animation: 'pulse 2s infinite' }} />
              AI-Powered Precision Agriculture · Northeast India
            </div>

            {/* Headline */}
            <h1 style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontSize: 'clamp(2.6rem, 5.5vw, 4.2rem)',
              fontWeight: 800,
              lineHeight: 1.1,
              letterSpacing: '-0.04em',
              color: '#fff',
              marginBottom: 20,
            }}>
              {t('landing.hero_title')}
            </h1>

            {/* Subtitle */}
            <p style={{ fontSize: '1.1rem', color: 'rgba(255,255,255,0.72)', lineHeight: 1.65, maxWidth: 560, margin: '0 auto 36px', fontWeight: 400 }}>
              {t('landing.hero_desc')}
            </p>

            {/* CTAs */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center', marginBottom: 48 }}>
              <Link to="/register" style={{
                background: '#fff', color: '#15803d', fontWeight: 700, fontSize: '0.95rem',
                padding: '13px 28px', borderRadius: 12, textDecoration: 'none',
                boxShadow: '0 4px 16px rgba(0,0,0,0.18)',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                transition: 'transform 0.15s, box-shadow 0.15s',
                display: 'inline-flex', alignItems: 'center', gap: 6,
              }}>
                {t('landing.get_started')} →
              </Link>
              <Link to="/login" style={{
                background: 'rgba(255,255,255,0.1)', color: '#fff', fontWeight: 600, fontSize: '0.95rem',
                padding: '13px 28px', borderRadius: 12, textDecoration: 'none',
                border: '1px solid rgba(255,255,255,0.2)', backdropFilter: 'blur(8px)',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}>
                {t('nav.login')}
              </Link>
            </div>

            {/* Pipeline strip */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
            >
              <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', letterSpacing: '0.15em', fontWeight: 600, textTransform: 'uppercase', marginBottom: 12 }}>
                9-Node AI Pipeline
              </p>
              <PipelineViz />
            </motion.div>
          </motion.div>
        </div>

        {/* Scrolling price ticker */}
        <PriceTicker />
      </section>

      {/* ── Stats ─────────────────────────────────────────────────────────── */}
      <section style={{ background: '#fff', borderBottom: '1px solid #e8edf2' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 24px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 24, textAlign: 'center' }}>
          {STATS.map((s, i) => (
            <motion.div key={s.label} {...fade(i * 0.08)}>
              <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '2.4rem', fontWeight: 800, color: '#15803d', letterSpacing: '-0.04em', lineHeight: 1 }}>
                {s.value}
              </div>
              <div style={{ fontSize: '0.9rem', color: '#374151', fontWeight: 600, marginTop: 6 }}>{s.label}</div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: 2 }}>{s.sub}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────────────────────── */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '80px 24px' }}>
        <SectionHead
          eyebrow="What it does"
          title={t('landing.features_title')}
          sub={`Built for smallholder farmers across ${NE_STATES.slice(0, 4).join(', ')} and beyond`}
        />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              {...fade(i * 0.06)}
              style={{
                background: '#fff',
                border: '1px solid #e8edf2',
                borderRadius: 16,
                padding: '28px 28px 24px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)',
                transition: 'transform 0.2s, box-shadow 0.2s',
                cursor: 'default',
              }}
              whileHover={{ y: -3, boxShadow: '0 6px 24px rgba(0,0,0,0.09)' }}
            >
              <div style={{
                width: 48, height: 48, borderRadius: 14,
                background: f.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 22, marginBottom: 16,
              }}>
                {f.icon}
              </div>
              <h3 style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontSize: '1rem', fontWeight: 700,
                color: '#0f172a', marginBottom: 8, letterSpacing: '-0.01em',
              }}>
                {f.title}
              </h3>
              <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.65, margin: 0 }}>
                {f.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Supported Crops ───────────────────────────────────────────────── */}
      <section style={{ background: '#f0fdf4', borderTop: '1px solid #dcfce7', borderBottom: '1px solid #dcfce7', padding: '48px 24px' }}>
        <div style={{ maxWidth: 860, margin: '0 auto', textAlign: 'center' }}>
          <p style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.18em', color: '#16a34a', textTransform: 'uppercase', marginBottom: 20 }}>
            10 Crops · SARIMAX + XGBoost Price Models
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10 }}>
            {CROPS.map(c => {
              const s = STATUS_COLOR[c.status]
              return (
                <motion.div
                  key={c.name}
                  {...fade()}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    background: '#fff', border: '1px solid #dcfce7',
                    borderRadius: 99, padding: '8px 16px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                  }}
                >
                  <span style={{ fontSize: 18 }}>{c.icon}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#1e293b', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>{c.name}</span>
                  <span style={{ fontSize: 12, color: '#64748b' }}>{c.price}</span>
                  <span style={{ background: s.bg, color: s.text, fontSize: 9, fontWeight: 700, padding: '1px 7px', borderRadius: 99, fontFamily: "'Plus Jakarta Sans', sans-serif", letterSpacing: '0.04em' }}>
                    {c.status}
                  </span>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── How It Works ──────────────────────────────────────────────────── */}
      <section style={{ maxWidth: 900, margin: '0 auto', padding: '80px 24px' }}>
        <SectionHead
          eyebrow="How it works"
          title="From farm data to decisions in seconds"
          sub="Raw sensor signals, live market feeds, and your farm's history — synthesised by 9 AI agents"
        />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 32, position: 'relative' }}>
          {[
            { step: '01', icon: '🌦️', title: 'Live Data Collection', desc: 'Open-Meteo weather API + ML market predictions for 10 crops. Your farm profile sets the context.' },
            { step: '02', icon: '🤖', title: '9-Agent AI Pipeline', desc: 'Planner selects tools. Agents run in parallel. Judge validates. Supervisor synthesises the final report.' },
            { step: '03', icon: '💡', title: 'Actionable Intelligence', desc: 'SELL / HOLD / WAIT decisions, pest warnings, irrigation schedules, and government scheme matches — all in one report.' },
          ].map((s, i) => (
            <motion.div key={s.step} {...fade(i * 0.12)} style={{ textAlign: 'center' }}>
              <div style={{
                width: 60, height: 60, borderRadius: 18,
                background: '#f0fdf4', border: '2px solid #bbf7d0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 28, margin: '0 auto 16px',
                boxShadow: '0 2px 8px rgba(22,163,74,0.1)',
              }}>
                {s.icon}
              </div>
              <div style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.16em', color: '#16a34a', textTransform: 'uppercase', marginBottom: 8, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Step {s.step}
              </div>
              <h3 style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '1rem', fontWeight: 700, color: '#0f172a', marginBottom: 8, letterSpacing: '-0.01em' }}>
                {s.title}
              </h3>
              <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.65, margin: 0 }}>{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Languages ─────────────────────────────────────────────────────── */}
      <section style={{ background: '#fff', borderTop: '1px solid #e8edf2', borderBottom: '1px solid #e8edf2', padding: '48px 24px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center' }}>
          <motion.div {...fade()}>
            <p style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.18em', color: '#6366f1', textTransform: 'uppercase', marginBottom: 10 }}>
              Multilingual
            </p>
            <h2 style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '1.6rem', fontWeight: 800, color: '#0f172a', letterSpacing: '-0.03em', marginBottom: 6 }}>
              Available in 7 languages
            </h2>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: 24 }}>Switch anytime from the navigation bar</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10 }}>
              {[
                ['🇮🇳', 'English'],
                ['🇮🇳', 'हिंदी'],
                ['🇮🇳', 'অসমীয়া'],
                ['🇮🇳', 'বাংলা'],
                ['🇮🇳', 'नेपाली'],
                ['🇮🇳', 'মণিপুরী'],
                ['🇮🇳', 'Mizo ṭawng'],
              ].map(([flag, lang]) => (
                <span key={lang} style={{
                  background: '#f8fafc', border: '1px solid #e2e8f0',
                  borderRadius: 99, padding: '7px 18px',
                  fontSize: '0.875rem', fontWeight: 500, color: '#374151',
                }}>
                  {flag} {lang}
                </span>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────────────────────── */}
      <section style={{
        background: 'linear-gradient(135deg, #052e16 0%, #166534 100%)',
        padding: '72px 24px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', inset: 0, opacity: 0.06, backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)', backgroundSize: '24px 24px', pointerEvents: 'none' }} />
        <motion.div {...fade()} style={{ position: 'relative' }}>
          <h2 style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: 'clamp(1.8rem, 4vw, 2.6rem)',
            fontWeight: 800, color: '#fff', letterSpacing: '-0.03em', marginBottom: 14,
          }}>
            Ready to transform your farm?
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.65)', marginBottom: 32, fontSize: '1rem', maxWidth: 440, margin: '0 auto 32px' }}>
            Join farmers across Northeast India using AI for smarter, data-driven agriculture.
          </p>
          <Link to="/register" style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: '#fff', color: '#15803d', fontWeight: 700, fontSize: '0.95rem',
            padding: '14px 32px', borderRadius: 12, textDecoration: 'none',
            boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            letterSpacing: '-0.01em',
          }}>
            Get started for free →
          </Link>
        </motion.div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer style={{ background: '#fff', borderTop: '1px solid #e8edf2', padding: '28px 24px', textAlign: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 18 }}>🌱</span>
          <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: '0.95rem', color: '#166534' }}>Agrow Intelligence</span>
        </div>
        <p style={{ color: '#94a3b8', fontSize: '0.8rem', margin: 0 }}>
          Built for Northeast India farmers · 10 crops · 8 ML models · 9 AI agents · 7 languages
        </p>
        <p style={{ color: '#cbd5e1', fontSize: '0.75rem', marginTop: 4 }}>
          पूर्वोत्तर भारत के किसानों के लिए · অসমৰ কৃষকৰ বাবে · মণিপুৰৰ কৃষকসকলৰ বাবে
        </p>
      </footer>

    </div>
  )
}
