# ShopMirror - Decision Log

A running list of decisions made during the build: "We considered X, chose Y, because Z." This log is extracted from the shipped product and its specs. It intentionally excludes trivial implementation details.

---

- **We considered building a generic AI content or SEO tool, but chose an AI representation auditor for Shopify merchants, because the real merchant problem is not generating more copy. It is that AI shopping systems cannot reliably classify, trust, or surface products when the underlying catalog data is weak.**

- **We considered building for buyers and merchants equally, but chose merchants as the primary user, because merchants own the source data and can act on the fixes. That gave the product a clear loop: audit -> evidence -> fix plan -> verified improvement.**

- **We considered claiming direct measurement of "how ChatGPT ranks you," but chose evidence-backed simulation, channel compliance, and query matching instead, because live AI provider outputs are non-deterministic and hard to compare before vs. after. We wanted a demo we could defend, not one that depends on lucky prompts.**

- **We considered treating robots.txt as the main discoverability bottleneck, but chose Shopify Catalog eligibility as the critical path, because major AI shopping exposure for Shopify merchants flows through Shopify's catalog layer, not only through web crawling. That changed D1 from a crawler story into a catalog-readiness story.**

- **We considered using a non-empty `product_type` as the category-quality signal, but chose Shopify Standard Taxonomy mapping as the real routing check, because a free-text product type can be populated and still useless for catalog inclusion or category matching.**

- **We considered keeping checks like raw-HTML price presence and AggregateRating schema, but removed them, because one almost always passed and the other almost always failed on normal Shopify stores. We cut them because a check that does not discriminate creates noise, not insight.**

- **We considered extrapolating public-store findings to the whole store, but chose explicit scan limits and sample-bound wording, because without Admin access we only truly know what we crawled. The free tier now caps to 10 products in a deterministic order and sampled HTML/schema checks are reported as sampled evidence, not full-catalog truth.**

- **We considered letting the LLM drive more of the audit, but chose deterministic code for scoring, eligibility, channel status, query matching, fix routing, and verification, because those paths affect correctness and must be reproducible. We use the model only where language interpretation genuinely adds value.**

- **We considered free-text LLM responses, but chose structured outputs with schema validation only, because malformed model output should fail loudly instead of silently polluting the report or fix plan.**

- **We considered keeping LLMs in the query simulator and MCP-style Q&A path, but replaced those with regex and rule-based logic where inputs were predictable, because using a model for deterministic extraction added cost and hallucination risk without improving quality.**

- **We considered a broad "auto-fix everything" story, but chose a narrower "fix only what we can write back and verify" boundary, because credibility mattered more than feature count. This is why some findings stay manual or copy-paste even when an LLM could generate plausible text for them.**

- **We considered presenting schema and policy fixes as autonomous writes, but chose generated copy-paste outputs for those cases, because the current write surface cannot safely and honestly mutate every storefront concern. We would rather surface real deliverables than pretend unsupported automation happened.**

- **We considered trusting tool success as proof that a fix worked, but chose live verification against Shopify state, because a successful function return is not the same as a successful merchant-facing mutation. Titles, taxonomy, metafields, alt text, and definitions are checked against Shopify after execution.**

- **We considered inferring before/after results from which fixes ran, but chose post-fix re-audit, because judges should be able to ask "what actually changed?" and get an answer grounded in refreshed store data rather than assumptions.**

- **We considered one-way mutations, but chose backup-first writes plus rollback, because an agent that edits merchant catalog data without recovery is not trustworthy. That decision shaped the writer, verifier, and UI all at once.**

- **We considered using the storefront URL as the Admin API target, but chose canonical Admin-domain resolution first, because custom-domain stores can look valid publicly while failing silently on Admin GraphQL. The system now tries to discover and verify the real Shopify Admin domain before paid-tier reads or writes.**

- **We considered Shopify OAuth for the hackathon build, but chose pasted Admin tokens, because OAuth would consume a large amount of build time without improving the core audit and remediation logic being judged. We accepted the tradeoff and explicitly kept tokens out of persistent storage.**

- **We considered storing Admin tokens to make delayed execution easier, but chose not to persist them, because merchant credential handling mattered more than convenience. That decision forced the execute path, asset download flow, and re-ingestion logic to work with request-supplied tokens only.**

- **We considered a more production-like worker architecture and multi-turn backend approval flow, but chose a simpler FastAPI background-task model with frontend approval followed by a single execute call, because it let us ship the end-to-end product loop within the hackathon window. We accepted the tradeoff that in-flight jobs are less durable than a full queue-backed system.**

- **We considered showing only a large findings table, but chose a headline AI Readiness Score, channel-specific compliance states, competitor benchmarking, query matching, and a before/after certificate, because both merchants and judges need an immediate answer to "how bad is it, why does it matter, and did the fixes improve it?"**
