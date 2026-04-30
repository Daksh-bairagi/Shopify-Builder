import { useEffect, useRef } from 'react'
import type { BeforeAfterResponse, AgentRun } from '../api/client'
import { overallFromPillars } from '../utils/score'

interface Props {
  storeName: string
  storeDomain: string
  data: BeforeAfterResponse
  agentRun: AgentRun
}

function scoreLabel(s: number): string {
  if (s >= 80) return 'Excellent'
  if (s >= 60) return 'Good'
  if (s >= 40) return 'Needs Work'
  return 'Critical'
}

const FIX_TYPE_LABELS: Record<string, string> = {
  improve_title: 'Product titles improved',
  map_taxonomy: 'Taxonomy mapped',
  classify_product_type: 'Product types set',
  fill_metafield: 'Metafields populated',
  generate_alt_text: 'Alt text generated',
  create_metafield_definitions: 'Metafield definitions created',
  inject_schema_script: 'Schema markup injected',
  generate_schema_snippet: 'Schema snippet generated',
  suggest_policy_fix: 'Policy drafts generated',
}

function fixLabel(fixId: string): string {
  for (const [prefix, label] of Object.entries(FIX_TYPE_LABELS)) {
    if (fixId.startsWith(prefix)) return label
  }
  return fixId
}

// Themed certificate. Uses Canvas2D primitives that work everywhere
// (no `ctx.letterSpacing` — that property is poorly supported and was silently ignored on Firefox/Safari).
export default function ReadinessCertificate({ storeName, storeDomain, data, agentRun }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const beforeScore = overallFromPillars(data.original_pillars)
  const afterScore = overallFromPillars(data.current_pillars)
  const delta = afterScore - beforeScore

  const top3Fixes = agentRun.executed_fixes
    .filter(f => f.success && !f.rolled_back)
    .slice(0, 3)
    .map(f => f.display_label || fixLabel(f.fix_id))

  const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = 800
    const H = 480
    const dpr = window.devicePixelRatio || 1
    canvas.width = W * dpr
    canvas.height = H * dpr
    canvas.style.width = `${W}px`
    canvas.style.height = `${H}px`
    ctx.scale(dpr, dpr)

    // Background — match dashboard ink palette.
    ctx.fillStyle = '#0E0D12'
    ctx.fillRect(0, 0, W, H)

    // Violet top accent.
    ctx.fillStyle = '#B4A0D6'
    ctx.fillRect(0, 0, W, 4)

    // Header band.
    ctx.fillStyle = '#7E7B8C'
    ctx.font = '600 11px ui-monospace, "SF Mono", Menlo, monospace'
    ctx.textAlign = 'left'
    ctx.fillText('S H O P M I R R O R   ·   AI READINESS', 48, 50)

    ctx.strokeStyle = 'rgba(180,160,214,0.18)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(48, 64)
    ctx.lineTo(W - 48, 64)
    ctx.stroke()

    // Title.
    ctx.fillStyle = '#ECE8F5'
    ctx.font = '400 28px Georgia, "Times New Roman", serif'
    ctx.fillText('AI Readiness Certificate', 48, 108)

    ctx.fillStyle = '#B0AAB9'
    ctx.font = '400 15px ui-sans-serif, system-ui, sans-serif'
    ctx.fillText(storeName, 48, 134)
    ctx.fillStyle = '#7E7B8C'
    ctx.font = '11px ui-monospace, monospace'
    ctx.fillText(storeDomain, 48, 154)

    const drawScoreBox = (x: number, y: number, score: number, label: string, color: string) => {
      // Card background.
      ctx.fillStyle = '#181621'
      ctx.strokeStyle = 'rgba(255,255,255,0.06)'
      ctx.lineWidth = 1
      const r = 12
      ctx.beginPath()
      ctx.moveTo(x + r, y)
      ctx.lineTo(x + 160 - r, y)
      ctx.quadraticCurveTo(x + 160, y, x + 160, y + r)
      ctx.lineTo(x + 160, y + 110 - r)
      ctx.quadraticCurveTo(x + 160, y + 110, x + 160 - r, y + 110)
      ctx.lineTo(x + r, y + 110)
      ctx.quadraticCurveTo(x, y + 110, x, y + 110 - r)
      ctx.lineTo(x, y + r)
      ctx.quadraticCurveTo(x, y, x + r, y)
      ctx.closePath()
      ctx.fill()
      ctx.stroke()

      ctx.textAlign = 'center'
      ctx.fillStyle = color
      ctx.font = '700 48px Georgia, serif'
      ctx.fillText(String(score), x + 80, y + 62)

      ctx.fillStyle = '#7E7B8C'
      ctx.font = '600 10px ui-monospace, monospace'
      ctx.fillText(label.toUpperCase(), x + 80, y + 82)

      ctx.fillStyle = color
      ctx.font = '400 13px ui-sans-serif, system-ui, sans-serif'
      ctx.fillText(scoreLabel(score), x + 80, y + 100)
      ctx.textAlign = 'left'
    }

    drawScoreBox(48, 178, beforeScore, 'Before', '#D57A78')

    ctx.fillStyle = '#7E7B8C'
    ctx.font = '28px ui-sans-serif, system-ui, sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('→', 264, 240)

    ctx.fillStyle = delta >= 0 ? '#8FB89A' : '#D57A78'
    ctx.font = '700 18px ui-sans-serif, system-ui, sans-serif'
    ctx.fillText(`${delta >= 0 ? '+' : ''}${delta} pts`, 264, 268)
    ctx.textAlign = 'left'

    drawScoreBox(310, 178, afterScore, 'After', '#8FB89A')

    // Right column: stats.
    const rx = 510
    const ry = 178

    ctx.strokeStyle = 'rgba(255,255,255,0.06)'
    ctx.beginPath()
    ctx.moveTo(rx - 16, ry - 8)
    ctx.lineTo(rx - 16, ry + 122)
    ctx.stroke()

    ctx.fillStyle = '#B4A0D6'
    ctx.font = '700 36px Georgia, serif'
    ctx.fillText(String(data.checks_improved.length), rx, ry + 44)
    ctx.fillStyle = '#7E7B8C'
    ctx.font = '12px ui-sans-serif, system-ui, sans-serif'
    ctx.fillText('checks improved', rx, ry + 64)

    ctx.fillStyle = '#ECE8F5'
    ctx.font = '700 36px Georgia, serif'
    ctx.fillText(String(agentRun.fixes_applied), rx, ry + 108)
    ctx.fillStyle = '#7E7B8C'
    ctx.font = '12px ui-sans-serif, system-ui, sans-serif'
    ctx.fillText('fixes applied', rx, ry + 128)

    // Top fixes.
    const ty = 320
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'
    ctx.beginPath()
    ctx.moveTo(48, ty)
    ctx.lineTo(W - 48, ty)
    ctx.stroke()

    ctx.fillStyle = '#7E7B8C'
    ctx.font = '600 10px ui-monospace, monospace'
    ctx.fillText('TOP FIXES APPLIED', 48, ty + 22)

    if (top3Fixes.length === 0) {
      ctx.fillStyle = '#7E7B8C'
      ctx.font = '13px ui-sans-serif, system-ui, sans-serif'
      ctx.fillText('No autonomous fixes were applied — all changes are manual or copy-paste.', 48, ty + 48)
    } else {
      top3Fixes.forEach((fix, i) => {
        const fy = ty + 44 + i * 24
        ctx.fillStyle = '#B4A0D6'
        ctx.font = '13px ui-sans-serif, system-ui, sans-serif'
        ctx.fillText('✓', 48, fy)
        ctx.fillStyle = '#B0AAB9'
        ctx.font = '13px ui-sans-serif, system-ui, sans-serif'
        ctx.fillText(fix, 70, fy)
      })
    }

    // Footer.
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'
    ctx.beginPath()
    ctx.moveTo(48, H - 44)
    ctx.lineTo(W - 48, H - 44)
    ctx.stroke()
    ctx.fillStyle = '#7E7B8C'
    ctx.font = '12px ui-sans-serif, system-ui, sans-serif'
    ctx.fillText(`Certified on ${dateStr}`, 48, H - 20)
    ctx.textAlign = 'right'
    ctx.fillStyle = '#5A576A'
    ctx.fillText('shopmirror.ai', W - 48, H - 20)
    ctx.textAlign = 'left'
  }, [beforeScore, afterScore, delta, storeName, storeDomain, data, agentRun, dateStr, top3Fixes])

  const handleDownload = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    try {
      const link = document.createElement('a')
      link.download = `shopmirror-certificate-${storeDomain}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } catch {
      // toDataURL can fail when the canvas is tainted; safe to ignore in our case (no remote images).
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontFamily: 'var(--font-geist)' }}>
      <div style={{ overflowX: 'auto' }}>
        <canvas
          ref={canvasRef}
          style={{
            borderRadius: 14,
            border: '1px solid var(--ink-line)',
            maxWidth: '100%',
            height: 'auto',
          }}
        />
      </div>
      <div>
        <button
          onClick={handleDownload}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '10px 18px', borderRadius: 100,
            background: 'var(--m-violet)', color: 'white',
            border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500,
            fontFamily: 'var(--font-geist)',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Download Certificate PNG
        </button>
      </div>
    </div>
  )
}
