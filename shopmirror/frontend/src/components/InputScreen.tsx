import { useState } from 'react'
import { AnalyzeRequest } from '../api/client'

interface Props {
  onSubmit: (req: AnalyzeRequest) => void
  error: string | null
}

export default function InputScreen({ onSubmit, error }: Props) {
  const [loading, setLoading] = useState(false)
  const [showToken, setShowToken] = useState(false)
  const [storeUrl, setStoreUrl] = useState('')
  const [adminToken, setAdminToken] = useState('')
  const [merchantIntent, setMerchantIntent] = useState('')
  const [competitorUrl1, setCompetitorUrl1] = useState('')
  const [competitorUrl2, setCompetitorUrl2] = useState('')

  function normalizeUrl(raw: string): string {
    let url = raw.trim()
    url = url.replace(/^https?:\/\//, '')
    url = url.replace(/\/$/, '')
    return url
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const normalized = normalizeUrl(storeUrl)
    if (!normalized) return

    setLoading(true)

    const req: AnalyzeRequest = {
      store_url: normalized,
    }

    const token = adminToken.trim()
    if (token) req.admin_token = token

    const intent = merchantIntent.trim()
    if (intent) req.merchant_intent = intent

    const competitors: string[] = []
    if (competitorUrl1.trim()) competitors.push(competitorUrl1.trim())
    if (competitorUrl2.trim()) competitors.push(competitorUrl2.trim())
    if (competitors.length > 0) req.competitor_urls = competitors

    try {
      await onSubmit(req)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-lg bg-gray-900 rounded-2xl shadow-xl p-8">
        {/* Logo / Title */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white">ShopMirror</h1>
          <p className="text-sm text-gray-400 mt-1">AI Commerce Readiness Auditor</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          {/* Store URL — required */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Shopify Store URL
            </label>
            <input
              type="text"
              value={storeUrl}
              onChange={(e) => setStoreUrl(e.target.value)}
              placeholder="yourstore.myshopify.com"
              required
              className="w-full bg-gray-800 text-white placeholder-gray-500 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Public URL — no token needed for basic audit
            </p>
          </div>

          {/* Admin Token — optional, collapsible */}
          <div>
            {!showToken ? (
              <button
                type="button"
                onClick={() => setShowToken(true)}
                className="text-sm text-sky-400 hover:text-sky-300 transition-colors"
              >
                + Add Admin Token (unlocks full audit)
              </button>
            ) : (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Admin API Token
                </label>
                <input
                  type="password"
                  value={adminToken}
                  onChange={(e) => setAdminToken(e.target.value)}
                  placeholder="shpat_..."
                  className="w-full bg-gray-800 text-white placeholder-gray-500 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Required for taxonomy, metafields, inventory checks
                </p>
                <button
                  type="button"
                  onClick={() => { setShowToken(false); setAdminToken('') }}
                  className="text-xs text-gray-500 hover:text-gray-400 mt-1 transition-colors"
                >
                  − Remove token
                </button>
              </div>
            )}
          </div>

          {/* Merchant Intent — optional */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              What is your store about? <span className="text-gray-500">(optional)</span>
            </label>
            <textarea
              rows={2}
              value={merchantIntent}
              onChange={(e) => setMerchantIntent(e.target.value)}
              placeholder="e.g. Premium sustainable outdoor gear for serious hikers"
              className="w-full bg-gray-800 text-white placeholder-gray-500 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent resize-none"
            />
            <p className="text-xs text-gray-500 mt-1">
              Helps the AI compare intended vs actual perception
            </p>
          </div>

          {/* Competitor URLs — optional */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Competitor URLs <span className="text-gray-500">(optional, max 2)</span>
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={competitorUrl1}
                onChange={(e) => setCompetitorUrl1(e.target.value)}
                placeholder="https://competitor.myshopify.com"
                className="flex-1 bg-gray-800 text-white placeholder-gray-500 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
              />
              <input
                type="text"
                value={competitorUrl2}
                onChange={(e) => setCompetitorUrl2(e.target.value)}
                placeholder="https://competitor.myshopify.com"
                className="flex-1 bg-gray-800 text-white placeholder-gray-500 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div className="bg-red-950 border border-red-700 rounded-xl px-4 py-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !storeUrl.trim()}
            className="w-full flex items-center justify-center gap-2 bg-sky-500 hover:bg-sky-600 disabled:bg-sky-800 disabled:cursor-not-allowed text-white font-semibold rounded-xl py-3 text-sm transition-colors"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Analyzing...
              </>
            ) : (
              'Analyze Store →'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
