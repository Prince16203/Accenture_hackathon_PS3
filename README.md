# KPI Intelligence-to-Action Engine

**Accenture Innovation Challenge — Round 2 | Track 3: BusinessIntelligence.ai**
**Team ZEUS**

A working prototype that diagnoses *why* a business KPI moved, ranks the actual drivers behind it, tells you how confident it is (and when it isn't), and turns the diagnosis into a concrete, owner-assigned action — reframed for whoever's asking, grounded in real retail data, with a live, self-computed breakdown of exactly where deterministic logic ends and AI begins.

---

## The Problem

Every retail business tracks KPIs across fragmented systems — different refresh cadences, different grains, inconsistent definitions. When a number moves, the "why" almost never lives next to the number. It's scattered across warehouse tickets, CRM notes, and field reports that nobody has time to cross-reference. And the right explanation for a movement depends on who's asking and what they plan to do about it.

Most analytics tools stop at "revenue dropped 18%." Ours keeps going: which department, driven by what, how confident are we, what should you actually do, and who should do it.

---

## What Makes This Different

**The LLM is never the source of quantitative truth.**

Every number here — every anomaly flag, every department breakdown, every contribution percentage, every confidence score — comes from deterministic statistics, SQL-style aggregation, or embedding-based retrieval. We instrumented a live telemetry ledger that proves this, rather than asking anyone to take our word for it: the diagnostic core of this system runs with zero generative AI calls, end to end.

A single language model call exists in the entire pipeline — narrative phrasing, applied only after every fact has already been decided. It is constrained by a strict system prompt to never add, alter, or invent anything it wasn't explicitly given, and it falls back automatically to a plain templated version of the same facts if it's ever unavailable. We tested that fallback live, against a genuine API billing interruption during development, and the system kept working without a pause.

This isn't a limitation we're hiding. It's the design principle the problem statement is explicitly asking for.

---

## System Architecture

```
Real Data (structured + unstructured)
        │
        ▼
┌────────────────────────┐
│  Signal Detection       │  Statistical process control + seasonal decomposition
│  (pure statistics)      │  → is this movement even real, or just noise/seasonality?
└───────────┬─────────────┘
            ▼
┌────────────────────────┐
│  SQL Decomposition      │  Department-level contribution ranking
│  (deterministic)        │  → WHERE numerically is this coming from?
└───────────┬─────────────┘
            ▼
┌────────────────────────┐
│  Hybrid RAG Retrieval   │  BM25 + dense embeddings, fused via RRF
│  (semantic search)      │  → WHAT human-reported context explains this?
└───────────┬─────────────┘
            ▼
┌────────────────────────┐
│  Agent Orchestration    │  LangGraph ReAct loop — proposes, tests, verifies,
│  (state machine)        │  holds MULTIPLE competing hypotheses in parallel
└───────────┬─────────────┘
            ▼
┌────────────────────────┐
│  Confidence Scoring     │  Agreement + match strength + self-consistency
│  (calibrated, honest)   │  → HIGH / MEDIUM / LOW / ABSTAIN, never fake certainty
└───────────┬─────────────┘
            ▼
┌────────────────────────┐
│  Recommendations        │  Template-based: driver → lever → action →
│  (structured, safe)     │  impact → owner → confidence → monitoring plan
└───────────┬─────────────┘
            ▼
┌────────────────────────┐
│  Persona Narratives     │  LLM phrases the facts above for Store Manager
│  (LLM, fact-constrained)│  vs. Regional VP — never decides them
└───────────┬─────────────┘
            ▼
┌────────────────────────┐
│  Feedback + Security    │  Overrides logged and monitored for drift;
│  + Telemetry            │  role-based access enforced at the query layer
└────────────────────────┘
```

Every box above is a real, tested, working code path — not a diagram of intent. The system is also reachable three ways: a Python API you can call directly, a REST API with interactive docs, and a reference web interface — all backed by the exact same pipeline.

---

## Real Data, Real Anomalies, No Hand-Waving

We didn't script fake scenarios. Every demo case is anchored to a genuine anomaly found by scanning 421,000+ real transaction rows.

| Data Source | What It Is | Grain | Cadence |
|---|---|---|---|
| Sales transactions | 45 stores, 81 departments, real weekly sales | store × dept × week | Weekly |
| Operations/markdown feed | Store-level markdowns, fuel price, CPI, unemployment | store × week | Weekly |
| Field reports (curated) | 79 tickets — warehouse, CRM, field reports, tagged by access level | event-level | Ad-hoc |

**Five connected KPIs**, chained through one primary metric — not five unrelated numbers sitting side by side:

```
total_weekly_revenue (primary)
  ├── dept_revenue_share      — decomposes revenue by department
  ├── regional_revenue        — rolls revenue up by region
  ├── markdown_spend          — a driver influencing revenue
  └── holiday_lift_pct        — explains seasonal swings in revenue
```

Every KPI's formula, threshold, lineage, and access rule lives in one governed semantic contract (`kpi_contract.yaml`) — a single source of truth every downstream module reads from, so no two parts of the system can silently disagree about what "revenue" means.

---

## The 5 Mandated Scenarios — All Working, All Real

**1. Clean Single-Cause Diagnosis**
Store 18 — real -52.9% drop ($606,984). A weather-driven distribution disruption. Evidence converges cleanly across warehouse, field, and customer-complaint sources. **Confidence: HIGH (1.0)**

**2. Multi-Factor Movement, Disentangled**
Store 27 — real -25.7% drop ($522,683). Three plausible causes on the table — marketing pause, staffing gap, competitor entry. The system doesn't just pick one: it explicitly evaluates and *refutes* the supply-disruption hypothesis after finding a ticket that directly contradicts it ("no stockout on record, inventory levels normal"), correctly promoting reduced promotional visibility as the real driver instead. This is reasoning, not pattern-matching.

**3. Low-Confidence Abstention**
Store 17 — real -23.9% drop ($253,791). Retrieved evidence directly contradicts itself — one ticket implies a shortage, another's inventory audit confirms full stock. The system detects the contradiction and halts *before* ever building a hypothesis, rather than forcing a confident-sounding wrong answer.

**4. Sparse-History / Newly-Launched KPI**
Store 3 / Dept 83 (one week of history) is compared against 14 peer stores of the same type via cohort proxy, with an automatic confidence ceiling applied. Store 7 / Dept 99 (a single test-batch pilot with no valid peer group) correctly abstains entirely rather than forcing a comparison against nothing.

**5. Role-Based Security**
Store 41 carries real HR-sensitive tickets tagged `restricted`. A regional manager in the correct region sees only standard-access evidence; the same manager in the wrong region is denied outright, before any data is touched; HR and Legal see everything. Enforcement happens at the data-query layer, not hidden in a UI toggle.

---

## What's Deterministic vs. What's AI

| Component | Method | LLM Involved? |
|---|---|:---:|
| Materiality detection | Statistical process control + STL seasonal decomposition | No |
| Department decomposition | SQL-style contribution ranking | No |
| Evidence retrieval | BM25 + sentence-transformer embeddings, RRF fusion | No — embedding, not generative |
| Contradiction detection | Rule-based opposing-phrase heuristics | No |
| Hypothesis ranking | Deterministic scoring (support − refutation + numeric weight) | No |
| Confidence scoring | Agreement / match-strength / self-consistency, weighted combination | No |
| Recommendations | Pre-approved action templates, slot-filled with real numbers | No |
| Persona narratives | LLM phrasing of already-decided facts | **Yes — the one exception** |

> **Measured result across every investigation run: the diagnostic core is 100% deterministic. One LLM call exists in the entire system — narrative synthesis — and it is fact-constrained and gracefully degrades to a template on any failure.**

This isn't a claim on a slide — it's a number the system computes about itself via a live telemetry ledger, logged with real per-step latency (sub-millisecond for reasoning steps, roughly 20ms warm and up to 3.4 seconds cold-start for embedding retrieval).

---

## How to Interact With It

The same pipeline is reachable three ways, all producing identical results:

**1. Direct Python** — run any of the five scenario scripts individually, or all five in sequence, and read the full investigation trail printed to your terminal.

**2. REST API** — a FastAPI service exposing `/api/investigate`, a role-scoped `/api/investigate/secure`, feedback capture, and telemetry endpoints, with interactive documentation at `/docs`.

**3. Reference UI** — a case-file style investigation console that calls the API live and renders the trail, hypothesis cards (visually distinguishing supported from refuted), the confidence verdict, the recommendation, and both persona narratives.

Nothing in the UI or API is scripted or pre-computed — every result you see there is generated by the same pipeline you can also run from the terminal.

---

## Tech Stack

- **Orchestration:** LangGraph (ReAct-pattern state machine)
- **Retrieval:** ChromaDB, `sentence-transformers` (all-MiniLM-L6-v2), `rank-bm25`
- **Statistics:** `statsmodels` (STL decomposition), custom control-limit implementation
- **LLM:** Anthropic Claude — narrative synthesis only, with automatic template fallback
- **API:** FastAPI, with full interactive documentation
- **Data:** `pandas`, YAML-governed semantic contracts
- **Language:** Python 3.12

---

## Project Structure

```
├── 1_data_foundation/        KPI semantic contract, dependency graph, sparse-history registry
├── 2_signal_layer/           Statistical materiality detection
├── 3_tools/                  SQL decomposition, contribution ranking
├── 4_rag_layer/              Hybrid retrieval, contradiction detection
├── 5_agent/                  LangGraph ReAct orchestrator, multi-hypothesis tracking
├── 6_confidence_layer/       Agreement scoring, match strength, self-consistency
├── 7_recommendation_engine/  Template-based action recommendations
├── 8_narrative_layer/        Persona-specific narratives — LLM synthesis + fallback
├── 9_feedback_loop/          Override capture, drift monitoring
├── 10_security/              Role-based access enforcement
├── 11_telemetry/             Latency logging, cost tracking, LLM/non-LLM ledger
├── 12_scenarios/             All 5 mandated demo scenarios, runnable individually or as one
├── api/                      FastAPI wrapper — investigate, secure, feedback, telemetry
├── ui/                       Reference investigation console (single-file, no build step)
└── docs/                     Business proposal, architecture diagram
```

---

## Running It

**Set up the environment:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Run all 5 mandated demo scenarios end-to-end, in the terminal:**

```powershell
cd 12_scenarios
python __init__.py
```

Each scenario prints the full investigation trail — materiality check, decomposition, retrieved evidence, hypothesis scoring (including refuted hypotheses), confidence tier with its component scores, the resulting recommendation, and both persona narratives.

**Or run the API and reference UI:**

```powershell
cd api
python main.py
```

Then open `ui/index.html` in a browser — it connects to the running API automatically.

**Optional — enable live LLM narratives:**

Add an `ANTHROPIC_API_KEY` to a `.env` file at the project root. Without one, the system runs exactly the same, using deterministic template narratives instead.

---

## Known Limitations (stated honestly, not hidden)

- **Dataset-specific bindings.** The architecture generalizes, but several modules currently reference this dataset's exact column names directly rather than reading them dynamically from the KPI contract. Parameterizing this fully is the clearest next step toward a dataset-agnostic deployment.
- **No formal causal inference or forecasting yet.** The multi-hypothesis reasoning tests and eliminates candidate causes against evidence, which is meaningful causal *reasoning* in practice, but it is not a formal causal-inference model with counterfactuals, and there is no predictive/forecasting component.
- **No free-text intent parsing.** The system takes structured input (store, department, week) rather than a natural-language question. Adding an LLM-based intent-parsing layer in front of the existing pipeline is a natural, comparatively low-risk next step.
- **STL seasonal decomposition** operates near its minimum reliable data requirement given the dataset's roughly 2.5-year span — flagged transparently rather than overstated.

---

## Why This Approach

Most KPI-explanation tools either let a language model freestyle a plausible-sounding story from a prompt, or build a rigid rules engine that can't handle nuance. We built neither.

Every number here is earned by real statistics or real retrieval. The system holds multiple hypotheses instead of collapsing to the first one. It actively looks for evidence that contradicts its own leading theory, and downgrades that theory when it finds it. And when the evidence genuinely doesn't support a confident answer, it says so, cheaply, before generating one — and tells you what would help.

That's the actual hard problem in this track, and it's the one we built for.