# ShopMirror — Feature Strength Matrix (REVISED)
## All 19 Checks Kept + Prominence-Based Strategy

---

## Decision Summary

**OLD:** Cut 8 features to streamline demo  
**NEW:** Keep all 19 checks. Change demo prominence based on impact + autonomy.

**Why:** Completeness signals rigor. Judges expect 19-check audit (not 11-check). Every check backed by published spec = defensible.

---

## Feature Prominence Matrix

| Feature | Severity | Auto-Fix? | Demo Prominence | Why This Prominence |
|---|---|---|---|---|
| **AI Readiness Score** | — | N/A | 🟢 **LEAD** | Emotional anchor. Judges expect this. |
| **Multi-Channel Dashboard** | — | N/A | 🟢 **LEAD** | Unique differentiator. 5 channels = competitive moat. |
| **LangGraph Agent** | — | Multi-check | 🟢 **LEAD** | Autonomous writes. Dependency ordering. Verification. |
| **MCP Simulation** | — | N/A | 🟢 **LEAD** | Real Shopify endpoint. Credible. |
| **Query Match Simulator** | — | N/A | 🟡 **FEATURE** | Shows causal link between fixes and AI matching. |
| **Heatmap** | — | N/A | 🟡 **FEATURE** | Visual proof of scale. Red→Green transformation. |
| **Before/After Report** | — | N/A | 🟡 **FEATURE** | Re-audit proves causality. |
| **Certificate** | — | N/A | 🟡 **FEATURE** | Memorable demo close. |
| **D1b (Catalog Eligibility)** | CRITICAL | Agent | 🟢 **AUTO-FIXED** | Shopify Catalog core requirement. |
| **T4 (Offer Schema)** | CRITICAL | Agent | 🟢 **AUTO-FIXED** | ChatGPT Shopping blocker. Script Tag injection impresses. |
| **C1 (Taxonomy GID)** | CRITICAL | Agent | 🟢 **AUTO-FIXED** | Routing layer. Everything depends on this. |
| **C2 (Title Category Noun)** | CRITICAL | Agent | 🟢 **AUTO-FIXED** | AI classification. Agent improves titles. |
| **C3 (Variant Options)** | HIGH | Agent | 🟢 **AUTO-FIXED** | Variant resolution. Agent names options. |
| **C5 (Metafield Definitions)** | HIGH | Agent | 🟢 **AUTO-FIXED** | Typed definitions. Agent creates + fills. |
| **A2 (Oversell Risk)** | CRITICAL | Manual | 🟡 **MENTION** | Transaction readiness. Worst outcome = failed order. |
| **A1 (Inventory Tracking)** | HIGH | Manual | 🟡 **MENTION** | Transaction readiness. AI must verify availability. |
| **Con3 (Schema Consistency)** | HIGH | Agent | 🟡 **MENTION** | **ELEVATED**: AI agents verify across 3 surfaces. Trust issue. |
| **D3 (llms.txt)** | MEDIUM | Agent | 🟡 **MENTION** | **ELEVATED**: Future-proofing. $900B market by 2030. |
| **Con1 (Schema Price)** | CRITICAL | Auto | 🟡 **RE-AUDIT** | Shown in before/after (re-audit discovers improvement). |
| **Con2 (Availability)** | CRITICAL | Auto | 🟡 **RE-AUDIT** | Shown in before/after (re-audit discovers improvement). |
| **T1 (Refund Days)** | HIGH | Manual | 🔴 **MENTION IF FAIL** | Policy clarity. Copy-paste only. Don't feature. |
| **T2 (Shipping Regions)** | HIGH | Manual | 🔴 **MENTION IF FAIL** | Location filtering. Copy-paste only. Don't feature. |
| **C4 (GTIN/SKU/Vendor)** | HIGH | Manual | 🔴 **MENTION IF FAIL** | Product identifier. Most stores have this. |
| **C6 (Alt Text Coverage)** | MEDIUM | Suggest | 🔴 **MENTION IF FAIL** | Visual matching. Suggestions only (future: bulk generation). |
| **D1a (GPTBot Blocked)** | MEDIUM | Manual | 🔴 **MENTION IF FAIL** | Web-index AI only. Most stores aren't blocking. |
| **D2 (Sitemap)** | HIGH | Manual | 🔴 **MENTION IF FAIL** | Web signal. Most stores have this. Low failure. |
| **D5 (Markets Translation)** | HIGH | Manual | 🔴 **CONDITIONAL** | International only. Most stores don't have Markets. |

---

## Judge Scoring: What They'll Evaluate

| Criteria | Your Strength | Where to Emphasize | Evidence |
|---|---|---|---|
| **Innovation** | Autonomous fixes + MCP + Multi-channel view | Agent execution + Dashboard | Script Tag injection (T4 is impressively safe) |
| **Completeness** | 19 spec-backed checks | Full findings report | Every check has citation link |
| **Defensibility** | Spec-cited (not invented) | In Q&A: open any citation | Shopify docs, schema.org, Google published standards |
| **Competitive Moat** | Product data + Shopify-native + Before/after | Demo flow + Competitive slide | OmniSEO does brand mentions (different layer) |
| **Feasibility** | 8-day build, complete pipeline | Working demo end-to-end | Agent completes 3+ fixes in <90 seconds |
| **Market Fit** | $49/month for 4M Shopify merchants | Business model slide | $0.05 cost per free analysis = sustainable |
| **Technical Depth** | LangGraph + asyncpg + Vertex AI | Code discussion if asked | Dependency ordering shows thoughtfulness |

---

## What Judges Will Ask (Be Ready)

| Question | Your Answer | Evidence |
|---|---|---|
| "Why 19 checks instead of 5?" | "Every check maps to published spec. Shopify docs, schema.org, Google published standards. Not invented criteria." | Show any check's spec citation. |
| "Why keep llms.txt if platforms don't require it?" | "Emerging standard. $900B agentic commerce market by 2030. Early adopters get edge. Takes 60 seconds to implement." | Market research + emerging standard article |
| "Isn't schema consistency just SEO?" | "No. AI agents verify across HTML, JSON-LD, and feeds. Contradictions damage AI trust. We flag and fix inconsistencies." | Show Con3 finding example |
| "Why MCP simulation instead of ChatGPT API?" | "API calls are non-deterministic, cost $1-6 each, have TOS gray areas. MCP is Shopify's real endpoint. Reproducible." | Show `/api/mcp` endpoint docs |
| "How do you know fixes worked?" | "We re-run the full 19-check audit after each fix. Before/after per-pillar proof. Not estimation—verification." | Show audit results pre/post |
| "What's your moat vs OmniSEO?" | "Different layer. They track brand mentions. We fix product data using Shopify infrastructure + autonomous fixes + verification." | Competitive positioning slide |
| "How does this scale to 500 products?" | "Bulk Operations API for ingestion. O(n) audit. LLM batches 15 products/call. Agent executes dependency-ordered, not bulk." | Show batch processing logic |
| "What if the merchant's token expires?" | "We don't store tokens. Agent runs in dry-run mode showing what would be written. Production: short-TTL encrypted token." | Explain token handling design |
| "Why confidence gating on some fixes?" | "We auto-fix when safe and confident. Taxonomy: only write if confidence=high. Policy: always draft. Schema: always write (scriptTagCreate is reversible)." | Show confidence gates in agent code |
| "How do you handle rollback?" | "Every write creates a fix_backup row (DB, not Shopify metafield). Rollback is one API call. Script Tags rollback via scriptTagDelete." | Show fix_backups schema |

---

## Red Flags to Avoid Saying

| ❌ Don't Say | ✅ Say Instead | Why |
|---|---|---|
| "We cut features that don't matter" | "We check everything specs require, then prioritize which to auto-fix" | Signals confidence, not shortcuts |
| "llms.txt is not important yet" | "llms.txt is emerging infrastructure. As markets standardize, it becomes essential." | Future-proofing angle is stronger |
| "AI only cares about data, not policies" | "AI agents verify both. Policy clarity = agent confidence." | Prevents underselling completeness |
| "Most stores pass inventory checks" | "Inventory misconfiguration causes failed agentic transactions—the worst outcome." | Emphasizes severity, not rarity |
| "Schema consistency is just SEO" | "AI agents verify data across 3 surfaces. Inconsistencies damage agent trust." | Reframes for AI commerce |
| "Copy-paste fixes aren't useful" | "We provide exact instructions for manual fixes. Better a precise instruction than vague finding." | Reframes copy-paste as value |
| "We're better than OmniSEO because…" | "We operate at a different layer—product data vs brand mentions. Complementary spaces." | Prevents sounding defensive |
| "19 checks is a lot to track" | "Every check is binary pass/fail tied to a published spec. Judges can verify any claim." | Defensibility angle |

---

## Competitive Moat (Updated)

| Angle | ShopMirror | OmniSEO | Profound | Goodie | Google Shopping | Meta Catalog |
|---|---|---|---|---|---|---|
| **Product data audit** | ✅ Yes (19 checks) | ❌ Brand mentions | ❌ Brand sentiment | ❌ Content quality | ❌ Feed only | ❌ Feed only |
| **Real AI endpoint (MCP)** | ✅ Yes (Shopify) | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Autonomous fixes** | ✅ Yes (7 fix types) | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Before/after verification** | ✅ Yes (re-audit) | ❌ No | ❌ No | ❌ No | ❌ Partial | ❌ No |
| **Multi-channel view** | ✅ Yes (5 channels) | ❌ No | ❌ No | ❌ No | ❌ 1 channel (GS) | ❌ 1 channel (Meta) |
| **Spec-cited checks** | ✅ Yes (19) | ❌ No | ❌ No | ❌ No | ✅ Yes (Google Merchant) | ✅ Yes (Meta) |
| **Merchant-facing (not B2B2C)** | ✅ Yes | ✅ Yes | ❌ Enterprise | ❌ Enterprise | ❌ Platform only | ❌ Platform only |
| **Shopify-native** | ✅ Yes (Admin API) | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |

**Your Unique Position:**
> Only tool that combines: (1) product data audit + (2) real Shopify endpoint + (3) autonomous fixes + (4) multi-channel view + (5) before/after verification + (6) merchant-facing pricing. No competitor covers all 6.

---

## Demo Breakdown: Where Your Confidence Comes From

| Demo Moment | Why It Works | Judges Will Notice |
|---|---|---|
| **Score animates 31→68** | Visceral before/after. Every metric-driven tool has a headline score. | "They understand what SaaS needs." |
| **Heatmap red→green** | Visual transformation. Communicates scale instantly. | "Clear communication of problem + solution." |
| **Agent dependency ordering** | Shows thoughtfulness. Not random automation. | "They understand product data relationships." |
| **T4 Script Tag injection** | Safe, reversible, autonomous. Most impressive fix. | "This is non-trivial engineering." |
| **Multi-Channel Dashboard** | 5 channels in one view. No competitor does this. | "They understand AI commerce isn't one thing." |
| **MCP simulation re-run** | Shows UNANSWERED→ANSWERED. Causal proof. | "Not hand-waving claims, actual verification." |
| **Before/After report** | Re-audit proves fixes worked on same 19 checks. | "Reproducible verification, not estimation." |

---

## Judge Confidence Check (Before Demo)

**Can you answer these without hesitation?**

- [ ] "Why is Completeness 30% of the score?" → Answer in your head
- [ ] "How do you know fixes actually worked?" → Answer in your head
- [ ] "Why MCP over ChatGPT API?" → Answer in your head
- [ ] "What makes you different from OmniSEO?" → Answer in your head
- [ ] "Why keep llms.txt if platforms don't require it?" → Answer in your head
- [ ] "How does schema consistency affect AI?" → Answer in your head
- [ ] "Why autonomous T4 fixes specifically?" → Answer in your head
- [ ] "How do you handle inventory tracking at scale?" → Answer in your head
- [ ] "Why 19 checks instead of 5?" → Answer in your head
- [ ] "What happens if agent confidence is low?" → Answer in your head

**If any of these hesitate you, practice the answer 5 times before demo day.**

---

## Your Edge in Q&A

Competitors will have:
- ✅ Brand mention tracking
- ✅ Content strategy advice
- ✅ SEO optimization

You will have:
- ✅ Product data audit (19 checks tied to specs)
- ✅ Real Shopify infrastructure (MCP endpoint)
- ✅ Autonomous fixes with verification
- ✅ Multi-channel compliance view
- ✅ Before/after proof

**In Q&A, own that. Don't apologize for checking "extra" things—explain why each thing matters for AI commerce.**

---

## Final Checklist Before Demo Day

### Technical (Engineer checks)
- [ ] All 19 checks run without errors
- [ ] Agent executes 3+ autonomous fixes
- [ ] Before/after audit shows improvement
- [ ] Score animates smoothly
- [ ] Heatmap color-codes correctly
- [ ] Dashboard shows state changes

### Narrative (You practice)
- [ ] Can explain score formula in 30 seconds
- [ ] Can defend MCP choice in 30 seconds
- [ ] Can explain why 19 checks in 30 seconds
- [ ] Can contrast vs OmniSEO in 30 seconds
- [ ] Can explain T4 Script Tag safety in 30 seconds
- [ ] Can explain multi-channel importance in 30 seconds

### Confidence (Your mindset)
- [ ] "We check everything specs require—judges respect that"
- [ ] "19 checks signals rigor, not bloat"
- [ ] "Every feature is defensible with spec citation"
- [ ] "Judges will ask anything; we have answers for all"
- [ ] "Demo is 3 min impact; Q&A is 5 min depth"

---

End of revised matrix. All 19 checks kept. Own it.
