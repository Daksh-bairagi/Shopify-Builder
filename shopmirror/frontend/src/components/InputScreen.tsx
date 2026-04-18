import { useState } from 'react'
import { AnalyzeRequest } from '../api/client'

interface Props {
  onSubmit: (req: AnalyzeRequest) => void
  error: string | null
}

const STATS = [
  { value: '19', label: 'AI checks run' },
  { value: '5', label: 'channels audited' },
  { value: '0–100', label: 'readiness score' },
]

const FEATURES = [
  {
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
    title: 'AI Readiness Score',
    desc: 'Weighted 0–100 score across 5 pillars: discoverability, completeness, consistency, trust, and transaction.',
  },
  {
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
    title: 'Multi-Channel Compliance',
    desc: 'Instant READY / PARTIAL / BLOCKED status for Shopify Catalog, Google Shopping, Meta, Perplexity, and ChatGPT.',
  },
  {
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
    ),
    title: 'Autonomous Fixes',
    desc: 'With an admin token, the AI agent rewrites titles, maps taxonomy, injects schema, and fills metafields automatically.',
  },
]

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
    const req: AnalyzeRequest = { store_url: normalized }
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

  const inputClass =
    'w-full bg-[#0A0E27] text-white placeholder-[#2D3A5E] border border-[#1E2545] rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/60 transition-all duration-200'

  return (
    <div className="min-h-screen bg-[#0A0E27] flex items-stretch">

      {/* ── Left panel: value proposition ─────────────────────────────── */}
      <div className="hidden lg:flex flex-col justify-between w-[52%] px-16 py-14 relative overflow-hidden">

        {/* Aurora background blobs */}
        <div className="pointer-events-none absolute inset-0">
          <div
            className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full opacity-20"
            style={{ background: 'radial-gradient(circle, #3B82F6 0%, transparent 70%)' }}
          />
          <div
            className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full opacity-10"
            style={{ background: 'radial-gradient(circle, #F59E0B 0%, transparent 70%)' }}
          />
        </div>

        {/* Logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <span className="font-code text-lg font-bold text-white">
              Shop<span className="text-blue-400">Mirror</span>
            </span>
          </div>
        </div>

        {/* Main copy */}
        <div className="relative z-10 space-y-8">
          <div>
            <h1 className="font-code text-4xl font-bold text-white leading-tight">
              Is your store
              <br />
              <span
                className="text-transparent bg-clip-text"
                style={{ backgroundImage: 'linear-gradient(90deg, #F59E0B, #FBBF24)' }}
              >
                invisible to AI?
              </span>
            </h1>
            <p className="mt-4 text-[#6B7DB3] text-base leading-relaxed max-w-md">
              ShopMirror audits your Shopify store against 19 AI shopping platform requirements
              and shows you exactly why ChatGPT, Perplexity, and Google Shopping miss your products.
            </p>
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-6">
            {STATS.map((s) => (
              <div key={s.label}>
                <div className="font-code text-2xl font-bold text-white">{s.value}</div>
                <div className="text-xs text-[#4B5A8A] mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Feature cards */}
          <div className="space-y-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="flex items-start gap-4 bg-[#141830] border border-[#1E2545] rounded-xl p-4"
              >
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 shrink-0 mt-0.5">
                  {f.icon}
                </div>
                <div>
                  <div className="text-white text-sm font-semibold">{f.title}</div>
                  <div className="text-[#4B5A8A] text-xs mt-1 leading-relaxed">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10">
          <p className="text-xs text-[#2D3A5E] font-code">
            Kasparro Agentic Commerce Hackathon — Track 5
          </p>
        </div>
      </div>

      {/* ── Right panel: form ──────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col justify-center px-8 sm:px-12 lg:px-16 py-14 lg:border-l lg:border-[#1E2545]">

        {/* Mobile logo */}
        <div className="flex items-center gap-3 mb-10 lg:hidden">
          <div className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
            <svg className="w-4 h-4 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <span className="font-code text-base font-bold text-white">
            Shop<span className="text-blue-400">Mirror</span>
          </span>
        </div>

        <div className="w-full max-w-md mx-auto lg:mx-0 animate-fade-in">
          <div className="mb-8">
            <h2 className="font-code text-2xl font-bold text-white">Audit your store</h2>
            <p className="text-[#6B7DB3] text-sm mt-1.5">
              Enter your store URL to get a free AI readiness report in under 60 seconds.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">

            {/* Store URL */}
            <div>
              <label className="block text-xs font-semibold text-[#6B7DB3] uppercase tracking-wider mb-2">
                Shopify Store URL <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#4B5A8A]">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
                  </svg>
                </div>
                <input
                  type="text"
                  value={storeUrl}
                  onChange={(e) => setStoreUrl(e.target.value)}
                  placeholder="yourstore.myshopify.com"
                  required
                  className={inputClass + ' pl-10'}
                />
              </div>
              <p className="text-xs text-[#2D3A5E] mt-1.5">
                Public storefront URL — disable password protection if on a dev store
              </p>
            </div>

            {/* Admin Token */}
            <div className="bg-[#141830] border border-[#1E2545] rounded-xl p-4">
              {!showToken ? (
                <button
                  type="button"
                  onClick={() => setShowToken(true)}
                  className="flex items-center gap-2 w-full cursor-pointer group"
                >
                  <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 group-hover:bg-amber-500/20 transition-colors">
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                    </svg>
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-medium text-white">Add Admin Token</div>
                    <div className="text-xs text-[#4B5A8A]">Unlocks autonomous fixes, taxonomy mapping + full audit</div>
                  </div>
                  <svg className="w-4 h-4 text-[#4B5A8A] ml-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                </button>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                        </svg>
                      </div>
                      <span className="text-sm font-medium text-amber-400">Admin Token</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => { setShowToken(false); setAdminToken('') }}
                      className="text-xs text-[#4B5A8A] hover:text-[#6B7DB3] transition-colors cursor-pointer flex items-center gap-1"
                    >
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12h-15" />
                      </svg>
                      Remove
                    </button>
                  </div>
                  <input
                    type="password"
                    value={adminToken}
                    onChange={(e) => setAdminToken(e.target.value)}
                    placeholder="shpat_..."
                    className={inputClass}
                    autoFocus
                  />
                  <p className="text-xs text-[#4B5A8A]">
                    Shopify Admin API token — required for taxonomy, metafields, inventory and autonomous fix execution
                  </p>
                </div>
              )}
            </div>

            {/* Merchant Intent */}
            <div>
              <label className="block text-xs font-semibold text-[#6B7DB3] uppercase tracking-wider mb-2">
                Brand Context <span className="text-[#2D3A5E] font-normal normal-case tracking-normal">optional</span>
              </label>
              <textarea
                rows={2}
                value={merchantIntent}
                onChange={(e) => setMerchantIntent(e.target.value)}
                placeholder="e.g. Premium sustainable outdoor gear for serious hikers"
                className={inputClass + ' resize-none'}
              />
              <p className="text-xs text-[#2D3A5E] mt-1.5">
                Helps the AI compare intended vs actual perception
              </p>
            </div>

            {/* Competitor URLs */}
            <div>
              <label className="block text-xs font-semibold text-[#6B7DB3] uppercase tracking-wider mb-2">
                Competitor URLs <span className="text-[#2D3A5E] font-normal normal-case tracking-normal">optional, max 2</span>
              </label>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  value={competitorUrl1}
                  onChange={(e) => setCompetitorUrl1(e.target.value)}
                  placeholder="competitor.myshopify.com"
                  className={inputClass}
                />
                <input
                  type="text"
                  value={competitorUrl2}
                  onChange={(e) => setCompetitorUrl2(e.target.value)}
                  placeholder="competitor.myshopify.com"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-start gap-3 bg-red-500/8 border border-red-500/25 rounded-xl px-4 py-3">
                <svg className="w-4 h-4 text-red-400 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !storeUrl.trim()}
              className="w-full flex items-center justify-center gap-2.5 rounded-xl py-3.5 text-sm font-semibold transition-all duration-200 cursor-pointer disabled:cursor-not-allowed"
              style={{
                background: loading || !storeUrl.trim()
                  ? 'rgba(59,130,246,0.2)'
                  : 'linear-gradient(135deg, #2563EB, #3B82F6)',
                color: loading || !storeUrl.trim() ? 'rgba(147,197,253,0.4)' : '#fff',
                boxShadow: loading || !storeUrl.trim() ? 'none' : '0 4px 24px rgba(59,130,246,0.35)',
              }}
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  Analyzing store...
                </>
              ) : (
                <>
                  Run AI Audit
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                </>
              )}
            </button>

          </form>

          {/* Trust badges */}
          <div className="flex items-center gap-4 mt-6 pt-6 border-t border-[#1E2545]">
            {[
              { icon: '🔒', label: 'Token never stored' },
              { icon: '⚡', label: 'Results in ~60s' },
              { icon: '↩', label: 'All fixes reversible' },
            ].map((b) => (
              <div key={b.label} className="flex items-center gap-1.5 text-xs text-[#4B5A8A]">
                <span className="text-sm">{b.icon}</span>
                {b.label}
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  )
}
