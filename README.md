# KPI Intelligence-to-Action Engine

**Accenture Innovation Challenge — Round 2 | Track 3: BusinessIntelligence.ai**

A working prototype that diagnoses *why* a business KPI moved, ranks the actual drivers behind it, tells you how confident it is (and when it isn't), and turns the diagnosis into a concrete, owner-assigned action — all grounded in real retail data, with a transparent breakdown of exactly where deterministic logic ends and AI begins.

---

## 📌 The Problem

Every retail business tracks KPIs across fragmented systems with different refresh cadences, different grains, and inconsistent definitions. When a number moves, the "why" almost never lives next to the number — it's scattered across warehouse tickets, CRM notes, and field reports that nobody has time to cross-reference. And the "right" explanation for a movement depends on who's asking and what they plan to do about it.

Most analytics tools stop at "revenue dropped 18%." Ours keeps going: *which department, driven by what, how confident are we, what should you actually do, and who should do it.*

---

## 🎯 What Makes This Different

> **The LLM is never the source of quantitative truth.**

Every number in this system — every anomaly flag, every department breakdown, every contribution percentage, every confidence score — comes from deterministic statistics, SQL-style aggregation, or embedding-based retrieval. We built and instrumented a live telemetry ledger that proves this:

**100% of the diagnostic pipeline runs with zero LLM calls.**

The system can explain, with a receipt, exactly what ran as math and what (if anything) ran as AI. This isn't a limitation we're hiding — it's the core design principle, and it's exactly what the problem statement asks for.

---

## 🏗️ System Architecture

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
│  Persona Narratives     │  Same facts, reframed for Store Manager vs.
│  + Feedback + Security  │  Regional VP; overrides logged; role-based access
└────────────────────────┘
```

Every arrow above is a real, tested, working code path — not a diagram of intent.

---

## 📊 Real Data, Real Anomalies, No Hand-Waving

We didn't script fake scenarios. Every demo case is anchored to a **genuine anomaly** found by scanning 421,000+ real transaction rows.

| Data Source | What It Is | Grain | Cadence |
|---|---|---|---|
| Sales transactions | 45 stores, 81 departments, real weekly sales | store × dept × week | Weekly |
| Operations/markdown feed | Store-level markdowns, fuel price, CPI, unemployment | store × week | Weekly |
| Field reports (curated) | 79 tickets — warehouse, CRM, field reports, tagged by access level | event-level | Ad-hoc |

**5 connected KPIs**, all chained through one primary metric — not five unrelated numbers sitting side by side:

```
total_weekly_revenue (primary)
  ├── dept_revenue_share      — decomposes revenue by department
  ├── regional_revenue        — rolls revenue up by region
  ├── markdown_spend          — a driver influencing revenue
  └── holiday_lift_pct        — explains seasonal swings in revenue
```

Every KPI's formula, threshold, lineage, and access rule lives in one governed semantic contract (`kpi_contract.yaml`) — a single source of truth every downstream module reads from, so no two parts of the system can silently disagree about what "revenue" means.

---

## ✅ The 5 Mandated Scenarios — All Working, All Real

### 1️⃣ Clean Single-Cause Diagnosis
**Store 18 — real -52.9% drop ($606,984).**
A weather-driven distribution disruption. Evidence converges cleanly across warehouse, field, and customer-complaint sources.
**Confidence: HIGH (1.0)**

### 2️⃣ Multi-Factor Movement, Disentangled
**Store 27 — real -25.7% drop ($522,683).**
Three plausible causes on the table — marketing pause, staffing gap, competitor entry. The system doesn't just pick one: it explicitly evaluates and **refutes** the supply-disruption hypothesis after finding a ticket that directly contradicts it ("no stockout on record, inventory levels normal"), correctly promoting `promotional_visibility` as the real driver instead. This is the system reasoning, not pattern-matching.

### 3️⃣ Low-Confidence Abstention
**Store 17 — real -23.9% drop ($253,791).**
Retrieved evidence directly contradicts itself — one ticket implies a shortage, another's inventory audit confirms full stock. The system detects the contradiction and **halts before ever building a hypothesis**, rather than forcing a confident-sounding wrong answer.

### 4️⃣ Sparse-History / Newly-Launched KPI
**Store 3 / Dept 83** (1 week of history) is compared against 14 peer stores of the same type via cohort proxy, with an automatic confidence ceiling applied.
**Store 7 / Dept 99** (a single test-batch pilot with no valid peer group) correctly **abstains entirely** rather than forcing a comparison against nothing.

### 5️⃣ Role-Based Security
**Store 41** carries real HR-sensitive tickets tagged `restricted`. A Regional Manager in the correct region sees only standard-access evidence; the same manager in the wrong region is denied outright; HR/Legal sees everything. Enforcement happens at the data-query layer, not hidden in a UI.

---

## ⚙️ What's Deterministic vs. What's AI

| Component | Method | LLM Involved? |
|---|---|:---:|
| Materiality detection | Statistical process control + STL seasonal decomposition | ❌ No |
| Department decomposition | SQL-style contribution ranking | ❌ No |
| Evidence retrieval | BM25 + sentence-transformer embeddings, RRF fusion | ❌ No *(embedding, not generative)* |
| Contradiction detection | Rule-based opposing-phrase heuristics | ❌ No |
| Hypothesis ranking | Deterministic scoring (support − refutation + numeric weight) | ❌ No |
| Confidence scoring | Agreement / match-strength / self-consistency, weighted combination | ❌ No |
| Recommendations | Pre-approved action templates, slot-filled with real numbers | ❌ No |
| Persona narratives | Structured templating | ❌ No *(LLM-ready extension point, not yet wired)* |

> **Measured result across every investigation run: 100% of pipeline steps are deterministic, 0% involve a generative LLM call.**

This isn't a claim — it's a number the system computes about itself via a live telemetry ledger, logged with real per-step latency (sub-millisecond for reasoning steps, ~20ms warm / ~3.4s cold-start for embedding retrieval).

---

## 🛠️ Tech Stack

- **Orchestration:** LangGraph (ReAct-pattern state machine)
- **Retrieval:** ChromaDB, `sentence-transformers` (all-MiniLM-L6-v2), `rank-bm25`
- **Statistics:** `statsmodels` (STL decomposition), custom control-limit implementation
- **Data:** `pandas`, YAML-based semantic contracts
- **API layer:** FastAPI *(in progress)*
- **Language:** Python 3.12

---

## 📁 Project Structure

```
├── 1_data_foundation/        KPI semantic contract, dependency graph, sparse-history registry
├── 2_signal_layer/           Statistical materiality detection
├── 3_tools/                  SQL decomposition, contribution ranking
├── 4_rag_layer/              Hybrid retrieval, contradiction detection
├── 5_agent/                  LangGraph ReAct orchestrator, multi-hypothesis tracking
├── 6_confidence_layer/       Agreement scoring, match strength, self-consistency
├── 7_recommendation_engine/  Template-based action recommendations
├── 8_narrative_layer/        Persona-specific narratives
├── 9_feedback_loop/          Override capture, drift monitoring
├── 10_security/              Role-based access enforcement
├── 11_telemetry/             Latency logging, cost tracking, LLM/non-LLM ledger
├── 12_scenarios/             All 5 mandated demo scenarios, runnable individually or as one
└── api/                      FastAPI wrapper (in progress)
```

---

## 🚀 Running It

```powershell
# Set up environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run all 5 mandated demo scenarios end-to-end
cd 12_scenarios
python __init__.py
```

Each scenario prints the full investigation trail — materiality check, decomposition, retrieved evidence, hypothesis scoring (including refuted hypotheses), confidence tier with its component scores, the resulting recommendation, and both persona narratives.

---

## ⚠️ Known Limitations (stated honestly, not hidden)

- **Dataset-specific bindings** — the architecture generalizes, but several modules currently reference this dataset's exact column names directly rather than reading them dynamically from the KPI contract. A production version would parameterize this fully.
- **No LLM wired in yet** — narrative and reasoning steps are template-based. This was a deliberate sequencing choice — build and prove the deterministic core first — with a clear extension point (`persona_narrator.py`) ready for LLM-based prose generation without touching the underlying facts or logic.
- **STL seasonal decomposition** operates near its minimum reliable data requirement given the dataset's ~2.5-year span — flagged transparently rather than overstated.

---

## 💡 Why This Approach

Most KPI-explanation demos either **(a)** let an LLM freestyle a plausible-sounding story from a prompt, or **(b)** build a rigid rules engine that can't handle nuance. We built neither.

Every number is earned by real statistics or real retrieval. The system holds multiple hypotheses instead of collapsing to the first one. It actively looks for evidence that contradicts its own leading theory. And when the evidence genuinely doesn't support a confident answer, it says so — and tells you what would help.

That's the actual hard problem in this track, and it's the one we built for.