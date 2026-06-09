import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'

const FEATURES = [
  { icon: '🌤️', key: 'f1', color: 'blue' },
  { icon: '📈', key: 'f2', color: 'green' },
  { icon: '🔬', key: 'f3', color: 'purple' },
  { icon: '📚', key: 'f4', color: 'orange' },
  { icon: '🤖', key: 'f5', color: 'indigo' },
  { icon: '🛒', key: 'f6', color: 'emerald' },
  { icon: '🌱', key: 'f7', color: 'green' },
  { icon: '💧', key: 'f8', color: 'blue' },
]

const COLOR_MAP = {
  blue:    'bg-blue-50 text-blue-600',
  green:   'bg-green-50 text-green-600',
  purple:  'bg-purple-50 text-purple-600',
  orange:  'bg-orange-50 text-orange-600',
  indigo:  'bg-indigo-50 text-indigo-600',
  emerald: 'bg-emerald-50 text-emerald-600',
}

// ✅ Fixed: 10 crops (not 4), 7 languages, accurate agent count
const STATS = [
  { value: '10',  label: 'Crop Types' },
  { value: '8',   label: 'ML Models' },
  { value: '38',  label: 'Disease Classes' },
  { value: '7',   label: 'Languages' },
]

const HOW_IT_WORKS = [
  {
    step: '01',
    icon: '🌦️',
    title: 'Real-Time Weather',
    desc: 'Open-Meteo API delivers accurate current conditions and 7-day forecast for your exact location in Northeast India.',
  },
  {
    step: '02',
    icon: '🧠',
    title: '5-Agent AI Pipeline',
    desc: 'Weather → Market → Advisory → Supervisor agents collaborate using LangGraph to generate your daily farm intelligence report.',
  },
  {
    step: '03',
    icon: '💡',
    title: 'Actionable Decisions',
    desc: 'Get SELL / HOLD / WAIT decisions for 10 crops, disease treatment plans, irrigation schedules and pest warnings — all in one report.',
  },
]

const CROPS = [
  { icon: '🍅', name: 'Tomato' },
  { icon: '🍆', name: 'Brinjal' },
  { icon: '🥬', name: 'Cabbage' },
  { icon: '🍋', name: 'Lemon' },
  { icon: '🥔', name: 'Potato' },
  { icon: '🧅', name: 'Onion' },
  { icon: '🫚', name: 'Ginger' },
  { icon: '🌿', name: 'Turmeric' },
  { icon: '🌶️', name: 'Chili' },
  { icon: '🧄', name: 'Garlic' },
]

const NE_STATES = ['Assam', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Tripura', 'Sikkim', 'Arunachal Pradesh']

const fade = { initial: { opacity: 0, y: 18 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true } }

export default function LandingPage() {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen">

      {/* ── Hero ── */}
      <section className="relative overflow-hidden bg-gradient-to-br from-green-900 via-green-800 to-emerald-700 text-white">
        <div className="absolute inset-0 opacity-10 pointer-events-none select-none">
          <div className="absolute top-10 left-10 text-9xl">🌾</div>
          <div className="absolute bottom-10 right-10 text-9xl">🌿</div>
          <div className="absolute top-1/2 left-1/3 text-7xl">☀️</div>
        </div>
        <div className="relative max-w-5xl mx-auto px-6 py-24 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur rounded-full px-4 py-1.5 text-sm mb-6">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              AI-Powered Precision Agriculture · Northeast India
            </div>
            <h1 className="text-5xl md:text-6xl font-bold mb-4 leading-tight">{t('landing.hero_title')}</h1>
            <p className="text-xl text-green-100 mb-3">{t('landing.hero_subtitle')}</p>
            <p className="text-base text-green-200 mb-10 max-w-2xl mx-auto">{t('landing.hero_desc')}</p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="bg-white text-green-800 font-semibold px-8 py-3.5 rounded-xl hover:bg-green-50 transition-colors shadow-lg">
                {t('landing.get_started')} →
              </Link>
              <Link to="/login" className="bg-white/10 backdrop-blur text-white font-semibold px-8 py-3.5 rounded-xl hover:bg-white/20 transition-colors border border-white/20">
                {t('nav.login')}
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Stats ── */}
      <section className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-6 py-8 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {STATS.map(s => (
            <motion.div key={s.label} {...fade}>
              <div className="text-3xl font-bold text-green-700">{s.value}</div>
              <div className="text-sm text-gray-500 mt-1">{s.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── 10 Supported Crops ── */}
      <section className="bg-gray-50 border-b">
        <div className="max-w-5xl mx-auto px-6 py-10">
          <h2 className="text-center text-sm font-semibold text-gray-400 uppercase tracking-widest mb-6">
            10 Crops Tracked with ML Price Predictions
          </h2>
          <div className="flex flex-wrap justify-center gap-3">
            {CROPS.map(c => (
              <div key={c.name} className="flex items-center gap-2 bg-white border border-gray-100 rounded-full px-4 py-2 shadow-sm text-sm font-medium text-gray-700">
                <span className="text-lg">{c.icon}</span> {c.name}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <motion.div {...fade}>
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-3">{t('landing.features_title')}</h2>
          <p className="text-center text-gray-500 mb-12">Built for smallholder farmers across {NE_STATES.join(' · ')}</p>
        </motion.div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map(({ icon, key, color }, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.07 }}
              className="agent-card group hover:shadow-md transition-shadow"
            >
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl mb-4 ${COLOR_MAP[color]}`}>
                {icon}
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{t(`landing.${key}_title`)}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{t(`landing.${key}_desc`)}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── How it Works ── */}
      <section className="bg-green-50 border-y border-green-100">
        <div className="max-w-5xl mx-auto px-6 py-20">
          <motion.div {...fade}>
            <h2 className="text-3xl font-bold text-center text-gray-900 mb-3">How it works</h2>
            <p className="text-center text-gray-500 mb-12">From raw sensor data to farm-ready decisions — in seconds</p>
          </motion.div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map((step, i) => (
              <motion.div
                key={step.step}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.12 }}
                className="text-center"
              >
                <div className="w-14 h-14 bg-green-100 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 shadow-sm">
                  {step.icon}
                </div>
                <div className="text-xs font-bold text-green-500 tracking-widest mb-2">STEP {step.step}</div>
                <h3 className="font-semibold text-gray-900 mb-2">{step.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Languages ── */}
      <section className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-6 py-12 text-center">
          <motion.div {...fade}>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Available in 7 languages</h2>
            <p className="text-gray-500 text-sm mb-8">Switch language anytime from the navigation bar</p>
            <div className="flex flex-wrap justify-center gap-3 text-sm">
              {[
                ['🇮🇳', 'English'],
                ['🇮🇳', 'हिंदी'],
                ['🇮🇳', 'অসমীয়া'],
                ['🇮🇳', 'বাংলা'],
                ['🇮🇳', 'नेपाली'],
                ['🇮🇳', 'মণিপুরী'],
                ['🇮🇳', 'Mizo ṭawng'],
              ].map(([flag, lang]) => (
                <span key={lang} className="bg-gray-50 border border-gray-100 rounded-full px-4 py-1.5 font-medium text-gray-700">
                  {flag} {lang}
                </span>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="bg-gradient-to-br from-green-700 to-emerald-600 text-white">
        <div className="max-w-3xl mx-auto px-6 py-16 text-center">
          <motion.div {...fade}>
            <h2 className="text-3xl font-bold mb-4">Ready to transform your farm?</h2>
            <p className="text-green-100 mb-8">Join farmers across Northeast India using AI for smarter, data-driven agriculture.</p>
            <Link to="/register" className="bg-white text-green-800 font-semibold inline-block px-8 py-3.5 rounded-xl hover:bg-green-50 transition-colors shadow-lg">
              Get started for free →
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-white border-t py-8 text-center text-sm text-gray-400">
        <p>🌱 Agrow Intelligence · Built for Northeast India farmers · 10 crops · 8 ML models · 7 languages · 5 AI agents</p>
        <p className="mt-1 text-xs">पूर्वोत्तर भारत के किसानों के लिए · অসমৰ কৃষকৰ বাবে · মণিপুৰৰ কৃষকসকলৰ বাবে</p>
      </footer>

    </div>
  )
}
