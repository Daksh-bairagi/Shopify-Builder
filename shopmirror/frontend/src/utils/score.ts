// Single source of truth for score math used across the dashboard so
// hero, pillar bars, and before/after deltas can never disagree.

import type { PillarScore } from '../api/client'

export const PILLAR_WEIGHTS: Record<string, number> = {
  Discoverability: 0.20,
  Completeness:    0.30,
  Consistency:     0.20,
  Trust_Policies:  0.15,
  Transaction:     0.15,
}

/** Normalize a score that may be 0–1 (fraction) or 0–100 (percent) to a 0–100 integer. */
export function normalizeScore(raw: number | null | undefined): number {
  if (raw == null || Number.isNaN(raw)) return 0
  const v = raw <= 1 ? raw * 100 : raw
  return Math.max(0, Math.min(100, Math.round(v)))
}

export function pillarPercent(p: PillarScore | undefined | null): number {
  if (!p) return 0
  return normalizeScore(p.score)
}

/** Compute a weighted overall score from pillar scores. Always returns 0–100. */
export function overallFromPillars(pillars: Record<string, PillarScore>): number {
  let total = 0
  let weightUsed = 0
  for (const [name, w] of Object.entries(PILLAR_WEIGHTS)) {
    const p = pillars[name]
    if (!p) continue
    const pct = pillarPercent(p) / 100
    total += pct * w
    weightUsed += w
  }
  if (weightUsed === 0) return 0
  // Re-normalize against weight actually applied so missing pillars don't drag the score to 0.
  return Math.round((total / weightUsed) * 100)
}

export function scoreBand(score: number) {
  if (score >= 80) return { label: 'Excellent', c: 'var(--m-good)',  cp: 'var(--m-good-p)' }
  if (score >= 60) return { label: 'Solid',     c: 'var(--m-info)',  cp: 'var(--m-info-p)' }
  if (score >= 40) return { label: 'Needs work',c: 'var(--m-warn)',  cp: 'var(--m-warn-p)' }
  return            { label: 'Critical',  c: 'var(--m-bad)',   cp: 'var(--m-bad-p)'  }
}
