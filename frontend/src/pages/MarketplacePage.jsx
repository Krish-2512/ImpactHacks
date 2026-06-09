import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProducts, createProduct, purchaseProduct } from '../api/market'
import { useAuthStore } from '../store/authStore'

function ProductCard({ product, onBuy, isFarmer }) {
  const { t } = useTranslation()
  const [qty, setQty]   = useState(1)
  const [show, setShow] = useState(false)
  const [msg, setMsg]   = useState('')

  const buy = async () => {
    try {
      const res = await onBuy(product._id, qty)
      setMsg(`✅ Purchased! Total: ₹${res.total_amount}`)
      setShow(false)
    } catch (e) {
      setMsg(`❌ ${e.response?.data?.detail || 'Failed'}`)
    }
  }

  return (
    <div className="agent-card">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900 capitalize">{product.name}</h3>
          <p className="text-xs text-gray-500">🌾 {product.farmer_name} · {product.location}</p>
        </div>
        <div className="text-right">
          <div className="font-bold text-green-700">₹{product.price_per_unit}</div>
          <div className="text-xs text-gray-400">per {product.unit}</div>
        </div>
      </div>
      <div className="text-sm text-gray-600 mb-4">
        {t('marketplace.available')}: <span className="font-medium">{product.quantity_available} {product.unit}</span>
      </div>
      {product.description && <p className="text-xs text-gray-400 mb-4">{product.description}</p>}

      {!isFarmer && (
        show ? (
          <div className="flex gap-2">
            <input
              type="number" min={1} max={product.quantity_available}
              value={qty} onChange={e => setQty(Number(e.target.value))}
              className="w-20 px-3 py-2 border rounded-lg text-sm"
            />
            <button onClick={buy} className="btn-primary text-sm flex-1">{t('marketplace.purchase')}</button>
            <button onClick={() => setShow(false)} className="btn-secondary text-sm">✕</button>
          </div>
        ) : (
          <button onClick={() => setShow(true)} className="btn-primary w-full text-sm">
            {t('marketplace.buy')}
          </button>
        )
      )}
      {msg && <p className="text-xs mt-2 text-center">{msg}</p>}
    </div>
  )
}

export default function MarketplacePage() {
  const { t } = useTranslation()
  const user = useAuthStore(s => s.user)
  const isFarmer = user?.role === 'farmer'
  const qc = useQueryClient()

  const { data: products = [], isLoading } = useQuery({ queryKey: ['products'], queryFn: getProducts })

  const [form, setForm] = useState({ name: '', price_per_unit: '', unit: 'kg', quantity_available: '', description: '' })
  const [showForm, setShowForm] = useState(false)

  const createMutation = useMutation({
    mutationFn: createProduct,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['products'] }); setShowForm(false); setForm({ name: '', price_per_unit: '', unit: 'kg', quantity_available: '', description: '' }) },
  })

  const handleBuy = (id, qty) => purchaseProduct(id, qty).then(res => { qc.invalidateQueries({ queryKey: ['products'] }); return res })

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('marketplace.title')}</h1>
        {isFarmer && (
          <button onClick={() => setShowForm(v => !v)} className="btn-primary">
            {showForm ? t('common.cancel') : `+ ${t('marketplace.add_product')}`}
          </button>
        )}
      </div>

      {/* Add product form */}
      {showForm && isFarmer && (
        <div className="agent-card mb-8">
          <h2 className="font-semibold text-gray-900 mb-4">{t('marketplace.add_product')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { key: 'name', label: 'Product Name', type: 'text', placeholder: 'e.g. Tomato' },
              { key: 'price_per_unit', label: 'Price per Unit (₹)', type: 'number', placeholder: '50' },
              { key: 'quantity_available', label: 'Quantity Available', type: 'number', placeholder: '100' },
            ].map(({ key, label, type, placeholder }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input type={type} placeholder={placeholder}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
                />
              </div>
            ))}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('marketplace.unit')}</label>
              <select
                value={form.unit}
                onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
              >
                {['kg', 'quintal', 'dozen', 'piece', 'litre'].map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
            <input type="text" placeholder="Fresh harvest, organic..."
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm"
            />
          </div>
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => createMutation.mutate(form)}
              disabled={createMutation.isPending}
              className="btn-primary"
            >
              {createMutation.isPending ? t('common.loading') : t('common.save')}
            </button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">{t('common.cancel')}</button>
          </div>
        </div>
      )}

      {/* Product grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {Array(6).fill(0).map((_, i) => (
            <div key={i} className="h-44 bg-gray-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : products.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-5xl mb-3">🛒</div>
          <p>No products listed yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {products.map(p => (
            <ProductCard key={p._id} product={p} onBuy={handleBuy} isFarmer={isFarmer} />
          ))}
        </div>
      )}
    </div>
  )
}
