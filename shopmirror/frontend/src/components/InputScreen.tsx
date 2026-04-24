import { useState } from 'react'
import { AnalyzeRequest } from '../api/client'
import { ShaderAnimation } from './ui/shader-animation'
import { Spotlight } from './ui/spotlight'

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
    'w-full bg-[#16141e] text-foreground placeholder-[#4a4560] border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/60 transition-all duration-200'

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6 py-14 relative overflow-hidden">

      {/* Shader animation — full-screen background */}
      <div className="absolute inset-0 opacity-[0.18] pointer-events-none">
        <ShaderAnimation />
      </div>
      {/* Overlay so form stays readable */}
      <div className="absolute inset-0 bg-background/65 pointer-events-none" />
      {/* Spotlight sweep */}
      <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="#a995c9" />

      <div className="relative z-10 w-full max-w-md animate-fade-in">

        {/* Logo */}
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 rounded-xl bg-primary/15 border border-primary/25 flex items-center justify-center">
            <svg className="w-5 h-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <span className="font-semibold text-lg text-foreground">
            Shop<span className="text-primary">Mirror</span>
          </span>
        </div>

        <div className="mb-8">
          <h2 className="text-2xl font-bold text-foreground">Audit your store</h2>
          <p className="text-muted-foreground text-sm mt-1.5">
            Enter your store URL to get a free AI readiness report in under 60 seconds.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Store URL */}
          <div>
            <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Shopify Store URL <span className="text-destructive">*</span>
            </label>
            <div className="relative">
              <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground">
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
            <p className="text-xs text-muted-foreground/60 mt-1.5">
              Public storefront URL — disable password protection if on a dev store
            </p>
          </div>

          {/* Admin Token */}
          <div className="bg-card border border-border rounded-xl p-4">
            {!showToken ? (
              <button
                type="button"
                onClick={() => setShowToken(true)}
                className="flex items-center gap-2 w-full cursor-pointer group"
              >
                <div className="w-7 h-7 rounded-lg bg-[#f0c88d]/10 border border-[#f0c88d]/20 flex items-center justify-center text-[#f0c88d] group-hover:bg-[#f0c88d]/20 transition-colors">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                  </svg>
                </div>
                <div className="text-left">
                  <div className="text-sm font-medium text-foreground">Add Admin Token</div>
                  <div className="text-xs text-muted-foreground">Unlocks autonomous fixes, taxonomy mapping + full audit</div>
                </div>
                <svg className="w-4 h-4 text-muted-foreground ml-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              </button>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-[#f0c88d]/10 border border-[#f0c88d]/20 flex items-center justify-center text-[#f0c88d]">
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                      </svg>
                    </div>
                    <span className="text-sm font-medium text-[#f0c88d]">Admin Token</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => { setShowToken(false); setAdminToken('') }}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer flex items-center gap-1"
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
                <p className="text-xs text-muted-foreground">
                  Shopify Admin API token — required for taxonomy, metafields and autonomous fix execution
                </p>
              </div>
            )}
          </div>

          {/* Merchant Intent */}
          <div>
            <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Brand Context <span className="text-muted-foreground/50 font-normal normal-case tracking-normal">optional</span>
            </label>
            <textarea
              rows={2}
              value={merchantIntent}
              onChange={(e) => setMerchantIntent(e.target.value)}
              placeholder="e.g. Premium sustainable outdoor gear for serious hikers"
              className={inputClass + ' resize-none'}
            />
          </div>

          {/* Competitor URLs */}
          <div>
            <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Competitor URLs <span className="text-muted-foreground/50 font-normal normal-case tracking-normal">optional, max 2</span>
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
            <div className="flex items-start gap-3 bg-destructive/8 border border-destructive/25 rounded-xl px-4 py-3">
              <svg className="w-4 h-4 text-destructive mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !storeUrl.trim()}
            className="w-full flex items-center justify-center gap-2.5 rounded-xl py-3.5 text-sm font-semibold bg-primary text-primary-foreground hover:opacity-90 active:scale-95 transition-all duration-200 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
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
        <div className="flex items-center gap-4 mt-6 pt-6 border-t border-border">
          {[
            { label: 'Token never stored' },
            { label: 'Results in ~60s' },
            { label: 'All fixes reversible' },
          ].map((b) => (
            <div key={b.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div className="w-1 h-1 rounded-full bg-primary" />
              {b.label}
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}
