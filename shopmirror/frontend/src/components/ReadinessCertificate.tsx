import { useEffect, useRef } from 'react'
import type { BeforeAfterResponse, AgentRun } from '../api/client'

interface Props {
  storeName: string
  storeDomain: string
  data: BeforeAfterResponse
  agentRun: AgentRun
}

function calcOverall(pillars: Record<string, { score: number }>): number {
  const WEIGHTS: Record<string, number> = {
    Discoverability: 0.20,
    Completeness: 0.30,
    Consistency: 0.20,
    Trust_Policies: 0.15,
    Transaction: 0.15,
  }
  let total = 0
  for (const [pillar, w] of Object.entries(WEIGHTS)) {
    const p = pillars[pillar]
    if (p) total += p.score * w
  }
  return Math.round(total * 100)
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

export default function ReadinessCertificate({ storeName, storeDomain, data, agentRun }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const beforeScore = calcOverall(data.original_pillars)
  const afterScore = calcOverall(data.current_pillars)
  const delta = afterScore - beforeScore

  const top3Fixes = agentRun.executed_fixes
    .filter(f => f.success)
    .slice(0, 3)
    .map(f => fixLabel(f.fix_id))

  const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = 800
    const H = 480
    canvas.width = W
    canvas.height = H

    // Background
    ctx.fillStyle = '#0A0E27'
    ctx.fillRect(0, 0, W, H)

    // Blue top bar
    ctx.fillStyle = '#3B82F6'
    ctx.fillRect(0, 0, W, 6)

    // Header
    ctx.fillStyle = '#6B7DB3'
    ctx.font = '13px monospace'
    ctx.letterSpacing = '3px'
    ctx.fillText('SHOPMIRROR', 48, 52)
    ctx.letterSpacing = '0px'

    ctx.fillStyle = '#1E2545'
    ctx.fillRect(48, 62, W - 96, 1)

    // Title
    ctx.fillStyle = '#FFFFFF'
    ctx.font = 'bold 28px sans-serif'
    ctx.fillText('AI Readiness Certificate', 48, 108)

    ctx.fillStyle = '#6B7DB3'
    ctx.font = '15px sans-serif'
    ctx.fillText(storeName, 48, 134)
    ctx.fillStyle = '#2D3A5E'
    ctx.font = '13px monospace'
    ctx.fillText(storeDomain, 48, 154)

    // Score boxes
    const drawScoreBox = (x: number, y: number, score: number, label: string, color: string) => {
      ctx.fillStyle = '#0F1535'
      ctx.strokeStyle = '#1E2545'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.roundRect(x, y, 160, 110, 12)
      ctx.fill()
      ctx.stroke()

      ctx.fillStyle = color
      ctx.font = 'bold 48px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(String(score), x + 80, y + 62)

      ctx.fillStyle = '#6B7DB3'
      ctx.font = '11px monospace'
      ctx.fillText(label.toUpperCase(), x + 80, y + 82)

      ctx.fillStyle = color
      ctx.font = '13px sans-serif'
      ctx.fillText(scoreLabel(score), x + 80, y + 100)
      ctx.textAlign = 'left'
    }

    drawScoreBox(48, 178, beforeScore, 'Before', '#F87171')

    // Arrow + delta
    ctx.fillStyle = '#6B7DB3'
    ctx.font = '28px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('→', 264, 240)

    ctx.fillStyle = delta >= 0 ? '#60A5FA' : '#F87171'
    ctx.font = 'bold 18px sans-serif'
    ctx.fillText(`${delta >= 0 ? '+' : ''}${delta} pts`, 264, 268)
    ctx.textAlign = 'left'

    drawScoreBox(310, 178, afterScore, 'After', '#60A5FA')

    // Right column: stats
    const rx = 510
    const ry = 178

    ctx.fillStyle = '#1E2545'
    ctx.fillRect(rx - 16, ry - 8, 1, 130)

    ctx.fillStyle = '#60A5FA'
    ctx.font = 'bold 36px sans-serif'
    ctx.fillText(String(data.checks_improved.length), rx, ry + 44)
    ctx.fillStyle = '#6B7DB3'
    ctx.font = '12px sans-serif'
    ctx.fillText('checks improved', rx, ry + 64)

    ctx.fillStyle = '#FFFFFF'
    ctx.font = 'bold 36px sans-serif'
    ctx.fillText(String(agentRun.fixes_applied), rx, ry + 108)
    ctx.fillStyle = '#6B7DB3'
    ctx.font = '12px sans-serif'
    ctx.fillText('fixes applied', rx, ry + 128)

    // Top fixes
    const ty = 320
    ctx.fillStyle = '#1E2545'
    ctx.fillRect(48, ty, W - 96, 1)

    ctx.fillStyle = '#4B5A8A'
    ctx.font = '11px monospace'
    ctx.letterSpacing = '2px'
    ctx.fillText('TOP FIXES APPLIED', 48, ty + 22)
    ctx.letterSpacing = '0px'

    top3Fixes.forEach((fix, i) => {
      const fy = ty + 44 + i * 24
      ctx.fillStyle = '#3B82F6'
      ctx.font = '13px sans-serif'
      ctx.fillText('✓', 48, fy)
      ctx.fillStyle = '#A8B4D8'
      ctx.font = '13px sans-serif'
      ctx.fillText(fix, 70, fy)
    })

    // Footer
    ctx.fillStyle = '#1E2545'
    ctx.fillRect(48, H - 44, W - 96, 1)
    ctx.fillStyle = '#2D3A5E'
    ctx.font = '12px sans-serif'
    ctx.fillText(`Certified on ${dateStr}`, 48, H - 20)
    ctx.textAlign = 'right'
    ctx.fillStyle = '#1E2545'
    ctx.fillText('shopmirror.ai', W - 48, H - 20)
    ctx.textAlign = 'left'
  }, [beforeScore, afterScore, delta, storeName, storeDomain, data, agentRun, dateStr, top3Fixes])

  const handleDownload = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const link = document.createElement('a')
    link.download = `shopmirror-certificate-${storeDomain}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <canvas
          ref={canvasRef}
          className="rounded-xl border border-[#1E2545] w-full max-w-2xl"
          style={{ imageRendering: 'auto' }}
        />
      </div>
      <button
        onClick={handleDownload}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        Download Certificate PNG
      </button>
    </div>
  )
}
