# ShopMirror Demo Priority Checklist (REVISED)
## All 19 Checks Kept — Prominence Strategy

**Key Change:** Don't cut features. Change demo prominence.  
**Why:** Completeness signals rigor. Judges respect thoroughness.

---

## 🟢 MUST SHOW (3 Minutes Total)

These drive emotional impact + show technical mastery.

### Minute 1: Problem + Score
- [ ] **AI Readiness Score appears (red, ~31/100)**
  - Lead with this. Judges love before/after metrics.
  - Frame: "Weighted across 5 pillars tied to published specs, not arbitrary."

### Minute 1.5: What's Wrong
- [ ] **Heatmap shows majority red cells (products × required fields)**
  - Visual: "50-product store with 6 red columns = big problem"
  - Worst products at top

### Minute 1.5: What AI Actually Sees
- [ ] **MCP Simulation: 6+ UNANSWERED questions**
  - Real Shopify `/api/mcp` endpoint
  - "Here's what ChatGPT, Copilot, and Gemini see when querying your store"

### Minute 1.5: Show It Matters
- [ ] **Query Match Simulator: 0/23 products match category query**
  - "When someone asks AI for this product, zero of yours match"
  - Root cause: "Missing material metafield blocks 18 products"

### Minute 2: Channel Readiness
- [ ] **Multi-Channel Compliance Dashboard: 4 BLOCKED, 1 PARTIAL**
  - Shopify Catalog BLOCKED
  - Google Shopping PARTIAL
  - "Here's exactly what's blocking each channel"

### Minute 2.5: Agent Fixes It
- [ ] **LangGraph Agent executes 3+ fixes with dependency ordering**
  - Planner: "Taxonomy first. Everything depends on knowing what the product IS."
  - Executor: Shows T4 Script Tag injection (most impressive autonomous fix)
  - Verifier: "After each fix, we re-check. If it fails, we retry."

### Minute 2.5: Proof of Impact
- [ ] **Before/After transformation (all at once)**
  - Score animates: 31 → 68
  - Heatmap turns green
  - Query match jumps: 0/23 → 19/23
  - Dashboard updates: BLOCKED → READY
  - MCP re-run shows 3 previously UNANSWERED now ANSWERED

### Minute 3: Takeaway
- [ ] **AI Readiness Certificate**
  - Download PNG
  - "This is what $49/month buys a Shopify merchant"

---

## 🟡 MENTION BRIEFLY (In Findings, Not Demo Flow)

Judges see these in the report, not as major demo moments.

### Schema Consistency (Con3) — ELEVATED IMPORTANCE
- [ ] Show in findings: "Schema price, availability, title consistency across HTML and JSON-LD"
- [ ] Frame: "AI agents verify data across three surfaces. Inconsistencies damage trust."
- [ ] Mention in Q&A if asked about data quality

### llms.txt Check (D3) — FUTURE-PROOFING
- [ ] Show in findings: "llms.txt present for AI agent guidance"
- [ ] Frame: "Emerging standard. As agentic commerce scales ($900B market by 2030), this becomes table stakes."
- [ ] Mention in Q&A if asked about standards compliance

### Refund Policy (T1) + Shipping Regions (T2)
- [ ] Show in findings IF they fail on demo store
- [ ] DON'T feature them in agent execution (copy-paste only, boring)
- [ ] Frame: "Policy clarity affects AI agent confidence"
- [ ] Mention in Q&A: "We check for explicit days, not vague language"

### Image Alt Text (C6)
- [ ] Show coverage % in heatmap
- [ ] Mention in findings: "Alt text helps AI match visuals to queries"
- [ ] DON'T run agent on this (weak autonomous fix currently)
- [ ] Note in Q&A: "Future enhancement: bulk alt text generation + batch approval"

### Inventory Tracking (A1) + Oversell Risk (A2)
- [ ] Show in findings: "Inventory tracked on all variants"
- [ ] Frame: "Transaction readiness: AI-initiated transactions fail if inventory is wrong"
- [ ] Mention in Q&A: "Most critical for failed agentic transactions"

### Sitemap (D2) + Robots.txt (D1a)
- [ ] Show in findings IF they fail
- [ ] DON'T mention unless failed (most stores have sitemap by default)
- [ ] Frame: "Web-index AI signal (Perplexity, Bing). Shopify Catalog uses API, not web crawl."

### Markets Translation (D5)
- [ ] Show in findings: "Per-market translation coverage"
- [ ] Frame ONLY if demo store has Shopify Markets enabled
- [ ] Otherwise: "Only relevant for international stores with Shopify Markets"

### All Other Checks (C1, C2, C3, C4, C5, Con1, Con2, T4, D1b)
- [ ] Present in full audit
- [ ] Mentioned automatically when agent fixes them
- [ ] Don't need special callout (agent execution shows improvement naturally)

---

## 🔴 DON'T MENTION (Unless They Fail)

These checks are included in the audit but don't deserve airtime in demo unless the dev store specifically fails them.

| Check | Reason |
|---|---|
| **D1a (GPTBot blocked)** | Most Shopify stores aren't blocking AI crawlers. Only mention if yours is. |
| **D2 (Sitemap)** | 99% of Shopify stores have sitemap. Only mention if missing. |
| **D3 (llms.txt)** | Mention as future-proofing, not blocker. See "Mention Briefly" section. |
| **T1/T2 (Policies)** | Mentioned in "Mention Briefly"—don't feature in agent loop. |

---

## ⏱️ Revised 3-Minute Script

| Time | What | Duration | Demo Elements |
|---|---|---|---|
| 0:00-0:20 | Problem: AI commerce is now. Data isn't ready. | 20s | Problem slide |
| 0:20-0:40 | Paste URL → Analyze | 20s | Input screen, progress bar |
| 0:40-0:55 | **Score + Heatmap + MCP** | 15s | 31/100 red badge + red heatmap + UNANSWERED ×6 |
| 0:55-1:10 | **Query Match** | 15s | "0/23 products match → missing material blocks 18" |
| 1:10-1:25 | **Multi-Channel Dashboard** | 15s | "4 channels blocked, 1 partial. Shopify Catalog BLOCKED." |
| 1:25-1:45 | **Agent Execution** | 20s | "Taxonomy first. Agent executes 3 fixes with dependency ordering." |
| 1:45-2:10 | **All Transforms At Once** | 25s | Score 31→68, heatmap green, query 0/23→19/23, dashboard READY, MCP ANSWERED ×3 |
| 2:10-2:30 | **Before/After Report** | 20s | "Completeness 4/6→6/6. Worst products improved. Here's what still needs manual action." |
| 2:30-3:00 | **Certificate** | 30s | Click download. PNG appears. "This is what merchants pay for." |

**Backup cuts (if running over):**
- Remove competitor comparison (can discuss in Q&A)
- Skip "manually apply schema snippet" section (just show pre-generated snippet exists)
- Skip MCP re-run detail (judges will assume you fixed it)
- Skip rollback demo (mention it exists in Q&A)

---

## Pre-Demo Checklist (Updated)

### Backend Verification
- [ ] Ingestion completes in <30 seconds
- [ ] All 19 checks run without errors
- [ ] AI Readiness Score calculates correctly (should be 25-35 on broken store)
- [ ] Multi-Channel Dashboard shows at least 2 BLOCKED statuses
- [ ] Heatmap renders with majority red cells
- [ ] Query match simulator shows 0-5 matches on default query
- [ ] MCP simulation returns at least 6 UNANSWERED responses
- [ ] Competitor search returns 3+ verified Shopify stores
- [ ] Schema consistency check (Con3) detects at least 1 mismatch
- [ ] llms.txt check (D3) shows llms.txt absent
- [ ] All 19 checks appear in audit findings

### Agent Verification
- [ ] LangGraph graph initializes without errors
- [ ] Dependency ordering correct: taxonomy → metafield → schema
- [ ] Agent executes at least 3 fixes autonomously
- [ ] Verification loop runs after each fix
- [ ] T4 Script Tag injection works (shows script_tag_id in fix_backups)
- [ ] All autonomous fixes complete in <90 seconds
- [ ] Before/after audit shows score improvement
- [ ] Query match simulator re-runs after agent
- [ ] Multi-Channel Dashboard updates (shows READY states now)
- [ ] MCP re-run shows ANSWERED responses

### Frontend Verification
- [ ] Score animation is smooth 31→68
- [ ] ProgressScreen shows realistic step-by-step progress
- [ ] Dashboard renders all sections without errors
- [ ] Heatmap loads with color-coded cells
- [ ] MultiChannelDashboard shows state changes (BLOCKED→READY)
- [ ] MCPSimulation shows before/after question pairs
- [ ] QueryMatchSimulator shows default queries with match counts
- [ ] AgentActivity shows live feed of agent steps
- [ ] BeforeAfterReport renders with pillar improvements
- [ ] Certificate exports as PNG without errors

### Dev Store Setup
- [ ] 15-20 products across 2-3 categories
- [ ] Intentional breakage applied:
  - [ ] Brand-name-only titles (no category noun) → C2 fails
  - [ ] Empty product_type fields → C1 fails
  - [ ] No metafields (material, care_instructions) → C5 fails
  - [ ] Unnamed variant options (Option1/Option2) on 3+ products → C3 fails
  - [ ] Schema price mismatches on 2+ pages → Con1 fails
  - [ ] PerplexityBot blocked in robots.txt → D1a fails
  - [ ] No OfferShippingDetails or MerchantReturnPolicy in schema → T4 fails
  - [ ] One or two products with oversell risk enabled → A2 fails
  - [ ] Missing llms.txt at root → D3 fails
  - [ ] Schema availability stale (out of sync with inventory) → Con2 fails
- [ ] Admin token ready (pasted in, not hardcoded)
- [ ] Merchant intent filled: "Premium sustainable sleep accessories"
- [ ] Verify store loads in <5 seconds

### Network & Connectivity
- [ ] Shopify API endpoints responding (<500ms)
- [ ] Google Cloud Vertex AI credentials configured
- [ ] Database connection pool working (test query)
- [ ] MCP endpoint reachable (test health check)
- [ ] Competitor search API responding (DDGS or SerpAPI)

---

## Judge Q&A Prep (With New Thinking)

**Q: "Why keep 19 checks instead of cutting to 10?"**
> Every check maps to a published specification. We're not inventing criteria. Judges respect thoroughness—especially when it's defensible.

**Q: "Isn't llms.txt irrelevant since platforms don't require it?"**
> Agentic commerce is $900B+ by 2030. This is an emerging standard. Merchants implementing it now have an edge when standards solidify. It takes 60 seconds to create; leaving it out is leaving value on the table.

**Q: "Why check schema consistency if most stores pass it?"**
> AI agents verify data across HTML, JSON-LD, and feeds. Contradictions damage agent trust. Con3 isn't a failing check—it's a trust check. Show the ones that fail and how we fix them.

**Q: "If T1/T2 (policies) are copy-paste only, why show them?"**
> Policy clarity directly affects AI agent confidence. A merchant with vague policies loses to one with precise policies in AI ranking. We highlight the gap but don't feature the copy-paste in demo—it's in findings and Q&A.

**Q: "What about inventory and oversell risk? Don't merchants ignore those?"**
> Inventory misconfiguration causes failed agentic transactions—the worst outcome. AI confirms stock, customer pays, product doesn't exist. We surface it clearly and provide exact instructions.

**Q: "Is 3 minutes enough to show all this?"**
> The demo shows emotional impact (score animation, heatmap transformation) in 3 minutes. The findings report shows completeness. Q&A addresses depth. Judges will ask about any feature; we're prepared to defend all 19.

---

## Red Flags to Avoid (Revised)

❌ **Don't say:** "We cut checks that don't matter" → Say: "We check everything published specs require, then prioritize which to auto-fix"

❌ **Don't say:** "llms.txt is not important yet" → Say: "llms.txt is emerging infrastructure. As markets standardize, it becomes essential."

❌ **Don't say:** "AI only cares about data structure, not policies" → Say: "AI agents verify both. Policy clarity = agent confidence."

❌ **Don't say:** "Most stores don't fail inventory checks" → Say: "Inventory tracking is critical for transaction readiness. When it fails, it fails hard (failed agentic transactions)."

---

## New Confidence Statements

**Before doing demo, believe these:**

1. "19 checks backed by published specs means we're not inventing criteria—we're implementing standards"
2. "Keeping all checks signals rigor. Judges respect thoroughness that's defensible."
3. "llms.txt and schema consistency aren't fringe features—they're future-proofing for a $900B market"
4. "We don't hide complexity; we change prominence. Demo shows dramatic impact; findings show completeness."
5. "Every feature in the report has a one-liner defense. Judges can ask anything and we have an answer."

---

## If Something Breaks

| Scenario | Fallback |
|---|---|
| Agent takes >90 sec | "Let me show you a pre-recorded run. Agent completed 3 fixes in 75 seconds." |
| Score animation janky | "Score improved 31→68. Completeness 4/6→6/6. Consistency 2/3→3/3." |
| Query match broken | "Query matching shows how many products match customer queries before/after fixes." |
| MCP unavailable | "MCP is down, but fallback Gemini simulation shows the same 10 questions." |
| Heatmap rendering issues | Show raw findings table instead. "These are the 5 worst products and their specific gaps." |
| One agent fix fails | "Agent retried and deferred to manual action. We're conservative about auto-fixes." |

---

## Demo Flow (Print This and Follow It)

**0:00-0:20** → Problem slide  
**0:20-0:40** → Input + Analyze  
**0:40-0:55** → *Show: Score (red 31) + Heatmap (red) + MCP (UNANSWERED ×6)*  
**0:55-1:10** → *Show: Query Match (0/23)*  
**1:10-1:25** → *Show: Multi-Channel (4 BLOCKED)*  
**1:25-1:45** → *Show: Agent dependency ordering + T4 injection*  
**1:45-2:10** → *All transforms: Score 31→68, Heatmap green, Query 0/23→19/23, Dashboard READY, MCP ANSWERED*  
**2:10-2:30** → *Show: Before/After report*  
**2:30-3:00** → *Show: Certificate download*  

**Q&A (5 min):** Be ready with defensive answers for all 19 checks.

---

End of revised checklist. All 19 checks kept. Prominence changed, not features removed.
