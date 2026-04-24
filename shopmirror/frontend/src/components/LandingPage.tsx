import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { BentoGrid, type BentoItem } from './ui/bento-grid'
import { SplineScene } from './ui/splite'
import { Spotlight } from './ui/spotlight'
import {
  TrendingUp,
  CheckCircle,
  Globe,
  Zap,
  Eye,
  Search,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  BarChart3,
} from 'lucide-react'

interface Props {
  onGetStarted: () => void
}

const FEATURES: BentoItem[] = [
  {
    title: 'AI Readiness Score',
    meta: '0–100',
    description:
      'Get a precision score based on 19 AI commerce checks across 5 pillars: Discoverability, Completeness, Consistency, Trust, and Transaction.',
    icon: <TrendingUp className="w-4 h-4 text-[#a995c9]" />,
    status: 'Real-time',
    tags: ['5 Pillars', 'Weighted', 'Instant'],
    colSpan: 2,
    hasPersistentHover: true,
  },
  {
    title: 'Autonomous Fix Agent',
    meta: 'LangGraph',
    description:
      'AI agent applies taxonomy mapping, metafield injection, and title improvements directly to your Shopify store.',
    icon: <Zap className="w-4 h-4 text-[#f0c88d]" />,
    status: 'Beta',
    tags: ['Auto-apply', 'Rollback'],
    cta: 'Approve fixes →',
  },
  {
    title: 'Query Match Simulator',
    meta: '5 queries',
    description:
      'Test how AI shopping agents respond to real buyer queries about your products using only your structured data.',
    icon: <Search className="w-4 h-4 text-[#a0bbe3]" />,
    status: 'Included',
    tags: ['Buyer Queries', 'Gaps'],
  },
  {
    title: 'AI Perception Gap',
    meta: 'Gemini AI',
    description:
      'See exactly how LLMs perceive your store vs. how you intend to be positioned — and the specific gaps driving the difference.',
    icon: <Eye className="w-4 h-4 text-[#f2b8c6]" />,
    status: 'LLM-powered',
    tags: ['Positioning', 'Intent', 'Gaps'],
    colSpan: 2,
    cta: 'See example →',
  },
  {
    title: '5-Channel Compliance',
    meta: 'AI Channels',
    description:
      "Check your store's readiness for Shopify Catalog, Google Shopping, Meta Catalog, Perplexity, and ChatGPT Shopping.",
    icon: <Globe className="w-4 h-4 text-[#77b8a1]" />,
    status: '5 Channels',
    tags: ['Google', 'Meta', 'ChatGPT'],
  },
]

const STEPS = [
  {
    num: '01',
    icon: <Search className="w-5 h-5" />,
    title: 'Paste Your Store URL',
    desc: 'Enter your Shopify store URL. Works instantly with public data — no login needed for the free scan.',
  },
  {
    num: '02',
    icon: <BarChart3 className="w-5 h-5" />,
    title: '19 Checks Run Automatically',
    desc: 'We audit catalog data, product completeness, AI query matching, MCP simulation, and multi-channel compliance.',
  },
  {
    num: '03',
    icon: <ShieldCheck className="w-5 h-5" />,
    title: 'Get Score + Fix Plan',
    desc: 'Receive your AI readiness score, perception gap analysis, and an actionable fix plan you can approve in one click.',
  },
]

const STATS = [
  { value: '19', label: 'AI Commerce Checks' },
  { value: '5', label: 'Pillar Scores' },
  { value: '5', label: 'AI Channels' },
  { value: '<30s', label: 'Free Scan' },
]

function NavBar({ onGetStarted }: { onGetStarted: () => void }) {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-background/80 backdrop-blur-md border-b border-border' : ''
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
          </div>
          <span className="font-semibold text-foreground">
            Shop<span className="text-primary">Mirror</span>
          </span>
        </div>

        <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-foreground transition-colors">How it works</a>
        </nav>

        <button
          onClick={onGetStarted}
          className="flex items-center gap-1.5 bg-primary text-primary-foreground text-sm font-medium px-4 py-2 rounded-lg hover:opacity-90 transition-opacity cursor-pointer"
        >
          Audit My Store
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  )
}

export default function LandingPage({ onGetStarted }: Props) {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans relative overflow-x-hidden">

      {/* ── Background layer 1: CSS ambient blobs (zero WebGL cost) ─────── */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Purple blob — top right */}
        <div
          className="absolute rounded-full"
          style={{
            width: 700, height: 700,
            top: -180, right: -160,
            background: '#a995c9',
            filter: 'blur(130px)',
            opacity: 0.18,
            animation: 'blobDrift 16s ease-in-out infinite',
          }}
        />
        {/* Pink blob — bottom left */}
        <div
          className="absolute rounded-full"
          style={{
            width: 560, height: 560,
            bottom: -100, left: -120,
            background: '#f2b8c6',
            filter: 'blur(110px)',
            opacity: 0.12,
            animation: 'blobDriftB 20s ease-in-out infinite',
          }}
        />
        {/* Blue blob — center */}
        <div
          className="absolute rounded-full"
          style={{
            width: 420, height: 420,
            top: '35%', left: '25%',
            background: '#a0bbe3',
            filter: 'blur(100px)',
            opacity: 0.08,
            animation: 'blobDriftC 24s ease-in-out infinite',
          }}
        />
      </div>

      {/* ── Background layer 2: Spotlight sweep (cheap SVG) ──────────── */}
      <div className="fixed inset-0 z-[1] pointer-events-none overflow-hidden">
        <Spotlight className="-top-40 left-0 md:left-40 md:-top-20" fill="#a995c9" />
      </div>

      {/* ── Navigation ────────────────────────────────────────────────── */}
      <NavBar onGetStarted={onGetStarted} />

      {/* ── All page content sits above backgrounds ───────────────────── */}
      <div className="relative z-10">

        {/* Hero — robot lives here as absolute, not fixed ────────────── */}
        {/* absolute means it only renders while hero is in the viewport   */}
        <section className="relative min-h-[88vh] pt-36 pb-20 px-6 overflow-hidden flex items-center">

          {/* Robot — narrower, anchored to hero section */}
          <div
            className="absolute right-[-2%] top-0 bottom-0 w-[38vw] pointer-events-none opacity-60 hidden lg:block"
          >
            <SplineScene
              scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
              className="w-full h-full"
            />
          </div>

          <div className="max-w-2xl mx-auto lg:mx-0 lg:pl-16 xl:pl-24">

            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full bg-primary/10 text-primary border border-primary/20 mb-8"
            >
              <Sparkles className="w-3 h-3" />
              Kasparro Agentic Commerce Hackathon · Track 5
            </motion.div>

            {/* Headline */}
            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-foreground leading-[1.1] mb-6"
            >
              Your products are
              <br />
              <span className="text-primary">invisible to AI</span>
              <br />
              shopping agents.
            </motion.h1>

            {/* Subheading */}
            <motion.p
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-lg text-muted-foreground max-w-xl mb-10 leading-relaxed"
            >
              ShopMirror audits your Shopify store against 19 AI commerce checks,
              shows you exactly what AI agents can and cannot determine about your products,
              and fixes it autonomously.
            </motion.p>

            {/* CTA buttons */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="flex flex-col sm:flex-row gap-3 mb-14"
            >
              <button
                onClick={onGetStarted}
                className="flex items-center justify-center gap-2 bg-primary text-primary-foreground font-semibold text-base px-7 py-3.5 rounded-xl hover:opacity-90 active:scale-95 transition-all cursor-pointer"
                style={{ boxShadow: '0 0 24px rgba(169,149,201,0.35)' }}
              >
                Audit My Store — Free
                <ArrowRight className="w-4 h-4" />
              </button>
              <a
                href="#how-it-works"
                className="flex items-center justify-center gap-2 bg-card/70 backdrop-blur-sm border border-border text-foreground font-medium text-base px-7 py-3.5 rounded-xl hover:border-primary/40 hover:bg-primary/5 transition-all cursor-pointer"
              >
                See how it works
              </a>
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.45 }}
              className="flex flex-wrap gap-8"
            >
              {STATS.map((s) => (
                <div key={s.label}>
                  <div className="text-2xl font-bold text-foreground font-code">{s.value}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{s.label}</div>
                </div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* Score preview card ──────────────────────────────────────────── */}
        <section className="px-6 pb-20">
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.55 }}
            className="max-w-xl mx-auto lg:mx-0 lg:ml-16 xl:ml-24"
          >
            <div className="bg-card/80 backdrop-blur-sm border border-border rounded-2xl p-6">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#77b8a1]" />
                  <span className="text-sm text-muted-foreground font-code">example-store.myshopify.com</span>
                </div>
                <span className="text-xs font-medium px-2 py-1 rounded-full bg-primary/10 text-primary border border-primary/20 font-code">
                  Full Audit
                </span>
              </div>

              <div className="flex items-center gap-8">
                <div className="text-center shrink-0">
                  <div className="text-6xl font-bold text-foreground font-code leading-none">54</div>
                  <div className="text-xs text-[#f0c88d] font-code mt-1">Needs Work</div>
                  <div className="text-xs text-muted-foreground mt-1">AI Readiness Score</div>
                </div>
                <div className="flex-1 space-y-2.5">
                  {[
                    { name: 'Discoverability', score: 72, color: '#a995c9' },
                    { name: 'Completeness',    score: 38, color: '#e57373' },
                    { name: 'Consistency',     score: 61, color: '#a995c9' },
                    { name: 'Trust & Policies',score: 45, color: '#f0c88d' },
                    { name: 'Transaction',     score: 55, color: '#a0bbe3' },
                  ].map((p) => (
                    <div key={p.name} className="flex items-center gap-3">
                      <div className="text-xs text-muted-foreground w-28 shrink-0">{p.name}</div>
                      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${p.score}%`, backgroundColor: p.color }} />
                      </div>
                      <div className="text-xs font-code text-foreground w-6 text-right">{p.score}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-border flex flex-wrap gap-2">
                {[
                  { label: 'Shopify', status: 'READY',   color: 'text-[#77b8a1] bg-[#77b8a1]/10 border-[#77b8a1]/20' },
                  { label: 'Google',  status: 'PARTIAL', color: 'text-[#f0c88d] bg-[#f0c88d]/10 border-[#f0c88d]/20' },
                  { label: 'Meta',    status: 'BLOCKED', color: 'text-[#e57373] bg-[#e57373]/10 border-[#e57373]/20' },
                  { label: 'ChatGPT', status: 'PARTIAL', color: 'text-[#f0c88d] bg-[#f0c88d]/10 border-[#f0c88d]/20' },
                  { label: 'Perplexity', status: 'READY', color: 'text-[#77b8a1] bg-[#77b8a1]/10 border-[#77b8a1]/20' },
                ].map((ch) => (
                  <span key={ch.label} className={`text-xs px-2.5 py-1 rounded-full border font-medium ${ch.color}`}>
                    {ch.label} · {ch.status}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        </section>

        {/* Features BentoGrid ──────────────────────────────────────────── */}
        <section id="features" className="px-6 py-20">
          <div className="max-w-6xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="text-center mb-12"
            >
              <div className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full bg-card/80 backdrop-blur-sm text-muted-foreground border border-border mb-4">
                <CheckCircle className="w-3 h-3 text-primary" />
                Full Audit Suite
              </div>
              <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                Every angle of AI commerce visibility
              </h2>
              <p className="text-muted-foreground max-w-xl mx-auto">
                ShopMirror covers the full stack — from structured data completeness to how AI agents
                actually answer buyer questions about your store.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.1 }}
            >
              <BentoGrid items={FEATURES} />
            </motion.div>
          </div>
        </section>

        {/* How It Works ────────────────────────────────────────────────── */}
        <section id="how-it-works" className="px-6 py-20">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="text-center mb-14"
            >
              <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                From URL to fix plan in 3 steps
              </h2>
              <p className="text-muted-foreground max-w-lg mx-auto">
                No complex setup. No agency required. Paste your URL and let ShopMirror do the work.
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {STEPS.map((step, i) => (
                <motion.div
                  key={step.num}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.12 }}
                  className="relative bg-card/80 backdrop-blur-sm border border-border rounded-2xl p-6 hover:border-primary/30 transition-colors group"
                >
                  {i < STEPS.length - 1 && (
                    <div className="hidden md:block absolute top-10 -right-3 w-6 h-px bg-border z-10" />
                  )}
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary group-hover:bg-primary/20 transition-colors">
                      {step.icon}
                    </div>
                    <span className="font-code text-2xl font-bold text-primary/40">{step.num}</span>
                  </div>
                  <h3 className="font-semibold text-foreground mb-2">{step.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA ───────────────────────────────────────────────────── */}
        <section className="px-6 py-24">
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="max-w-2xl mx-auto text-center"
          >
            <div className="relative bg-card/80 backdrop-blur-sm border border-primary/20 rounded-3xl px-8 py-14 overflow-hidden">
              <div
                className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 rounded-full blur-[60px] pointer-events-none"
                style={{ background: 'rgba(169,149,201,0.15)' }}
              />
              <div className="relative">
                <div className="w-12 h-12 rounded-2xl bg-primary/15 border border-primary/20 flex items-center justify-center mx-auto mb-6">
                  <Sparkles className="w-6 h-6 text-primary" />
                </div>
                <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                  Ready to win AI commerce?
                </h2>
                <p className="text-muted-foreground mb-8 max-w-md mx-auto">
                  Free public scan in under 30 seconds. Add your Admin Token for the full audit,
                  autonomous fixes, and your AI readiness certificate.
                </p>
                <button
                  onClick={onGetStarted}
                  className="inline-flex items-center gap-2 bg-primary text-primary-foreground font-semibold text-base px-8 py-4 rounded-xl hover:opacity-90 active:scale-95 transition-all cursor-pointer"
                  style={{ boxShadow: '0 0 24px rgba(169,149,201,0.35)' }}
                >
                  Audit My Store — Free
                  <ArrowRight className="w-4 h-4" />
                </button>
                <p className="text-xs text-muted-foreground mt-4">
                  No account needed · Public scan in 30s · Admin token optional
                </p>
              </div>
            </div>
          </motion.div>
        </section>

        {/* Footer ──────────────────────────────────────────────────────── */}
        <footer className="border-t border-border px-6 py-8">
          <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-md bg-primary/20 border border-primary/30 flex items-center justify-center">
                <Sparkles className="w-2.5 h-2.5 text-primary" />
              </div>
              <span className="text-sm font-medium text-foreground">Shop<span className="text-primary">Mirror</span></span>
            </div>
            <p className="text-xs text-muted-foreground text-center">
              Kasparro Agentic Commerce Hackathon · Track 5 · AI Representation Optimizer for Shopify
            </p>
            <button onClick={onGetStarted} className="text-xs text-primary hover:underline cursor-pointer">
              Start free audit →
            </button>
          </div>
        </footer>

      </div>{/* end z-10 content wrapper */}
    </div>
  )
}
