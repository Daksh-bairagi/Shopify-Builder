# ShopMirror — Complete Feature Analysis (REVISED)
## All 19 Checks Kept + Systematic Reconsideration

**Updated:** April 26, 2026  
**Key Change:** Keep ALL 19 checks. Change demo prominence, not feature set.  
**Reason:** Completeness matters. Emerging standards matter. Future-proofing matters.

---

## 🔄 DECISION: KEEP ALL 19 CHECKS

Instead of cutting features, I've recategorized by **demo prominence**:

- **Lead the Demo (2 min):** Automated fixes + Score animation
- **Feature Briefly (1 min):** Visual improvements + schema consistency
- **Mention in Findings (30 sec):** Policy clarity + future standards
- **Include in Audit (silent):** Edge cases + international merchants

---

## CATEGORY 1: Lead the Demo With These (2 Minutes)

### 1.1 **AI Readiness Score + Animation (31 → 68)**

**Why It's Strong:**
- Emotional anchor for judges
- Before/after proof of impact
- Tied to 5 pillars with published specs

**Defend It:**
> "Completeness 30% (AI can't route unclassified products) + Consistency 20% (wrong data damages trust) + Discoverability 20% (blockers cost visibility) + Transaction 15% + Trust 15%. Not arbitrary—each weight reflects real business impact."

**Demo Time:** 45 seconds

---

### 1.2 **Multi-Channel Compliance Dashboard**

**Why It's Strong:**
- Only tool showing 5 channels in one view
- READY/PARTIAL/BLOCKED status is immediately actionable
- Shows you understand AI != one monolithic system

**Defend It:**
> "Shopify Catalog ≠ Google Shopping ≠ Meta Catalog. Each has different required fields. This shows which channels are blocked and which checks are blocking them. It's the single source of truth for omnichannel AI readiness."

**Show State Change:** BLOCKED → READY after agent runs

**Demo Time:** 45 seconds

---

### 1.3 **LangGraph Agent + Autonomous Fixes**

**Why It's Strong:**
- Actually writes to Shopify (not just reporting)
- Dependency-aware ordering (taxonomy → metafield → schema)
- Verification loop proves fixes worked
- Fully reversible rollback

**Defend It:**
> "We don't report—we fix. Taxonomy first (everything depends on knowing what the product IS). Then metafields (extract from description). Then schema (based on corrected data). Agent verifies each fix and rolls back if needed. That's real agent engineering."

**Show:**
- Dependency ordering
- Verification loop (re-check after each fix)
- T4 Script Tag injection (most impressive autonomous fix)

**Demo Time:** 1.5 minutes

---

### 1.4 **MCP Simulation (Real Shopify Endpoint)**

**Why It's Strong:**
- Uses actual `/api/mcp` endpoint AI agents use
- More credible than ChatGPT API clone
- Graceful fallback to Gemini simulation

**Defend It:**
> "We use Shopify's own infrastructure—the actual interface AI agents hit. It's reproducible, cheap, and honest. Not ChatGPT simulation; it's the real MCP endpoint."

**Show Before/After:** Which UNANSWERED questions became ANSWERED after agent runs

**Demo Time:** 45 seconds

---

## CATEGORY 2: Feature Briefly / Show Results (1 Minute)

### 2.1 **AI Query Match Simulator**

**Current:** "0/23 products match 'premium cotton undershirt under $50'"  
**After Fixes:** "19/23 products match the same query"  
**Why:** Fills material metafield

**Demo Time:** 30 seconds

**Enhancement:** Add custom query input (not just default queries) + link matched products back to heatmap

---

### 2.2 **Product Completeness Heatmap (Red → Green)**

**Current:** Majority red cells for worst products  
**After Fixes:** Green cells appear  
**Impact:** Visual proof of transformation

**Demo Time:** 20 seconds (just show before/after, don't explain)

**Enhancement:** Add filtering for large catalogs, severity coloring (red=CRITICAL, yellow=MEDIUM)

---

### 2.3 **Before/After Audit Report**

**Show:**
- Per-pillar improvements (e.g., "Completeness: 4/6 → 6/6")
- Worst-5 product gap scores before/after
- Manual action items (what still needs fixing)

**Demo Time:** 20 seconds

---

### 2.4 **AI Readiness Certificate (PNG Export)**

**Show:** Click "Download Certificate" and it exports

**Demo Time:** 15 seconds

---

## CATEGORY 3: Mention in Findings (Include in Audit, Don't Feature)

These are KEPT because they matter. Just not featured in demo.

### 3.1 **Schema Consistency (Con3) — ELEVATED TO HIGH SEVERITY**

**Why It's Important (Revised):**
- AI agents verify product data across THREE places: HTML, JSON-LD schema, feeds
- If these CONTRADICT, agent loses trust and skips you
- Not just SEO—it's AI agent confidence

**Real Example:**
- HTML title: "Blue Cotton Shirt"
- JSON-LD schema: "Premium Indigo Tee"
- AI gets confused → deprioritizes or skips

**Severity:** ELEVATED from MEDIUM → HIGH

**Defend It:**
> "AI agents verify consistency across HTML, schema, and feeds. Contradictions damage agent trust. We flag inconsistencies and fix them."

**Mention in Demo:** "Schema consistency check—AI agents verify data across three surfaces"

---

### 3.2 **llms.txt Check (D3) — KEEP + FRAME AS FUTURE-PROOFING**

**Why It's Important (Revised):**
- Emerging standard for agentic commerce
- Not currently required by major platforms BUT…
- Agentic commerce = $900B-$1T by 2030 (McKinsey)
- Early adopters will have edge as standards solidify
- Takes 60 seconds to create; too valuable to omit

**Defend It:**
> "llms.txt is emerging infrastructure. Most platforms don't require it yet, but as agentic commerce scales ($900B+ market by 2030), this standard will solidify like robots.txt did. Stores implementing it now have a competitive edge."

**Mention in Demo:** "Future-proofing: we generate llms.txt for emerging AI standards"

---

### 3.3 **Refund Policy Clarity (T1)**

**Why It's Important:**
- AI agents need explicit day counts (e.g., "30 days")
- Vague wording ("a few weeks") is unextractable
- Affects merchant trust signal in AI commerce

**Why Not Featured:**
- Copy-paste only (merchant edits in Shopify Settings)
- Every store has this field
- Less dramatic than data structure fixes

**Defend It:**
> "AI agents parse policy text for constraint extraction. 'Within a few weeks' is unextractable. '30 days' is clear. We flag vague policies and provide precise text."

**Mention in Demo:** "If refund policy is vague, agent can't extract return window"

---

### 3.4 **Shipping Region Clarity (T2)**

**Why It's Important:**
- AI agents route queries by region ("ship to Canada?")
- Without explicit region names, can't answer location queries
- Affects merchant's reach in location-filtered searches

**Why Not Featured:**
- Copy-paste only
- Similar to T1 (policy clarity issue)

**Defend It:**
> "AI agents run location-filtered queries. 'We ship worldwide' is too vague. 'United States, Canada, UK' is clear. Explicit regions = reachability."

---

### 3.5 **Sitemap Presence (D2)**

**Why It's Important:**
- Signal for web-index AI (Perplexity, Bing AI)
- Shopify Catalog uses API (not web crawl), but other channels use web
- Best practice signal across all channels

**Why Not Featured:**
- Most modern Shopify themes include sitemap by default
- Low failure rate (not discriminating)
- Lower impact than data structure fixes

**Defend It:**
> "Shopify Catalog uses API, but Perplexity and Bing AI crawl the web. Sitemap helps them discover your product pages. It's a complementary signal."

---

### 3.6 **Image Alt Text Coverage (C6)**

**Why It's Important:**
- AI agents use alt text for visual attribute matching
- "Material: cotton" in alt text enables visual matching
- Affects how AI understands product attributes

**Why Not Featured (Currently):**
- Agent only generates suggestions (one-by-one fix)
- Not compelling demo moment: "agent suggested 47 alt texts, merchant will apply them later"

**Future Enhancement Path:**
- Bulk alt text generation + batch approval in UI
- Then agent writes all at once
- Then it becomes a featured fix

**Defend It (Current):**
> "Alt text helps AI match product visuals to queries. We analyze coverage and suggest improvements."

**Mention in Demo:** "Image alt text analysis—we check coverage and suggest improvements"

---

### 3.7 **Markets Translation (D5) — CONDITIONAL FEATURE**

**Why It's Important:**
- For international merchants with Shopify Markets
- AI agents serve queries in customer's language
- Untranslated titles/descriptions = invisible in non-English markets

**Why Not Featured:**
- Only applies to stores with Shopify Markets enabled
- Most demo stores won't have this
- Auto-fix requires 100+ field writes (not practical with Gemini)

**Defend It (If Applicable):**
> "For international stores with Shopify Markets, untranslated titles mean you're invisible to non-English queries in those markets. This check flags missing translations per market."

**Mention in Demo:** "If your store serves international markets, we check for translated product data"

---

### 3.8 **Inventory Tracking (A1) — TRANSACTION READINESS**

**Why It's Important:**
- AI-initiated transactions fail if inventory isn't tracked
- Untracked inventory = agent cannot verify availability
- Failed transactions are the worst outcome for merchants

**Why Not Featured:**
- Requires merchant to manually set in Shopify admin
- Not autonomous fixable
- Copy-paste instruction only

**Severity:** HIGH

**Defend It:**
> "AI agents verify inventory before recommending. If you're not tracking inventory, agents can't confirm availability. Failed agentic transactions are the worst outcome. We flag this and show how to fix it."

**Mention in Demo:** "Transaction readiness: we check if inventory is tracked for AI confidence"

---

### 3.9 **Oversell Risk (A2) — TRANSACTION READINESS**

**Why It's Important:**
- AI agent confirms stock, transaction processes, then inventory disappears
- Oversell policy + tracked inventory = failed delivery = worst outcome

**Why Not Featured:**
- Same as A1 (manual Shopify admin action)
- Not dramatic in demo

**Severity:** CRITICAL

**Defend It:**
> "Overselling kills agentic commerce. Agent confirms stock, customer pays, product doesn't exist. We flag this configuration and show how to fix it."

**Mention in Demo:** "Oversell risk: if inventory is tracked but oversell is enabled, AI-initiated orders will fail"

---

## CATEGORY 4: Included in 19 Checks (No Changes Needed)

These are solid checks tied to published specs. Keep as-is.

| Check | Reason It Stays | Demo Treatment |
|---|---|---|
| **D1a (Robots.txt crawlers)** | Web-index AI (Perplexity, Bing) blocked | Mention if failed |
| **D1b (Catalog Eligibility)** | Shopify Catalog requirement | Feature in dashboard |
| **C1 (Taxonomy GID)** | Routing layer for all AI | Auto-fixed by agent |
| **C2 (Title Category Noun)** | AI classification | Auto-fixed by agent |
| **C3 (Variant Option Names)** | Variant resolution | Auto-fixed by agent |
| **C4 (GTIN/SKU/Vendor)** | Product identifier | Check in findings |
| **C5 (Metafield Definitions)** | Typed metadata for filtering | Auto-fixed by agent |
| **C6 (Image Alt Text)** | Visual attribute extraction | Mention briefly |
| **Con1 (Schema Price)** | AI trust (price mismatch) | Re-audit shows improvement |
| **Con2 (Schema Availability)** | Stale inventory kills trust | Check in findings |
| **Con3 (SEO Consistency)** | ELEVATED: Schema consistency for AI | Mention in demo |
| **T1 (Refund Days)** | Policy clarity for AI | Mention if failed |
| **T2 (Shipping Regions)** | Location-filtered queries | Mention if failed |
| **T4 (Offer Schema)** | ChatGPT Shopping requirement | AUTO-FIXED by agent |
| **D3 (llms.txt)** | ELEVATED: Future-proofing | Mention as forward-thinking |
| **D2 (Sitemap)** | Web-index AI signal | Mention if failed |
| **D5 (Markets Translation)** | International markets | Mention if applicable |
| **A1 (Inventory Tracking)** | Transaction readiness | Mention importance |
| **A2 (Oversell Risk)** | Failed agentic transactions | Mention criticality |

---

## 📋 Revised Demo Prominence Guide

**LEAD (2 min):**
1. Score animation 31→68
2. Multi-Channel Dashboard BLOCKED→READY
3. Agent execution with dependency ordering
4. MCP simulation before/after

**FEATURE BRIEFLY (1 min):**
5. Query match improvement (0/23 → 19/23)
6. Heatmap red→green transformation
7. Before/after audit report
8. Certificate download

**MENTION IN FINDINGS (30 sec):**
9. Schema consistency (AI agent trust)
10. llms.txt (future-proofing)
11. Refund/shipping policy clarity
12. Inventory tracking (transaction readiness)
13. Image alt text (coverage analysis)

**SILENT (INCLUDED BUT NOT MENTIONED):**
14-19. Other checks (all present in audit, mentioned only if failed on demo store)

---

## Judge Q&A Answers (Revised)

**Q: "Why check llms.txt when platforms don't require it?"**
> Agentic commerce is $900B+ by 2030. Emerging standards become table stakes. Merchants implementing them now have an edge when standards solidify.

**Q: "Why include policy clarity checks if merchants hate copy-paste?"**
> Policy clarity directly affects AI agent confidence. A merchant with vague policies loses to one with precise policies in AI ranking. We flag the gap and provide exact text.

**Q: "Why include inventory checks if fixing requires Shopify admin?"**
> Because inventory misconfiguration causes failed agentic transactions—the worst outcome for merchants. We surface it clearly so merchants prioritize it.

**Q: "What about schema consistency—isn't that just SEO?"**
> No. AI agents verify product data across HTML, JSON-LD, and feeds. Contradictions damage AI trust. We flag inconsistencies and fix them autonomously.

**Q: "You're checking 19 things. Isn't that too many?"**
> Every check maps to a published specification. Each one is binary pass/fail. We're not inventing criteria—we're implementing what Shopify, schema.org, and Google publish.

---

## The Bottom Line

**Before:** "Let's cut features to streamline the demo"

**After:** "Let's keep all 19 checks because:
1. They're all spec-backed
2. Completeness signals rigor to judges
3. Future-proofing (llms.txt, schema consistency) matters
4. We just change PROMINENCE, not remove features"

**Demo isn't 3 minutes of depth—it's 3 minutes of emotional impact + 5 minutes of Q&A where completeness shines.**

---

End of revised analysis. All 19 checks STAY. Just different prominence.
