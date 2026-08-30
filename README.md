<div align="center">

# ⚙️ KPI Intelligence-to-Action Engine

### *Diagnoses why a KPI moved. Ranks the real drivers. Knows when it isn't sure.*

**Accenture Innovation Challenge — Round 2 · Track 3: BusinessIntelligence.ai**
**Team ZEUS**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C?style=flat-square)](https://www.langchain.com/langgraph)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Status](https://img.shields.io/badge/Status-Working%20Prototype-4ADE80?style=flat-square)]()
[![Determinism](https://img.shields.io/badge/Diagnostic%20Core-100%25%20Deterministic-A100FF?style=flat-square)]()

</div>

<br>

> A working prototype that diagnoses **why** a business KPI moved, ranks the actual drivers behind it, tells you **how confident it is** — and when it isn't — and turns the diagnosis into a concrete, owner-assigned action. Reframed for whoever's asking. Grounded in real retail data. With a live, self-computed breakdown of exactly where deterministic logic ends and AI begins.

<br>

## 📋 Contents

- [The Problem](#-the-problem)
- [What Makes This Different](#-what-makes-this-different)
- [System Architecture](#-system-architecture)
- [Real Data, No Hand-Waving](#-real-data-real-anomalies-no-hand-waving)
- [The 5 Mandated Scenarios](#-the-5-mandated-scenarios--all-working-all-real)
- [Deterministic vs. AI](#-whats-deterministic-vs-what-runs-through-ai)
- [How to Interact With It](#-how-to-interact-with-it)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Running It](#-running-it)
- [Known Limitations](#-known-limitations)
- [Why This Approach](#-why-this-approach)

<br>

---

## 🎯 The Problem

Every retail business tracks KPIs across fragmented systems — different refresh cadences, different grains, inconsistent definitions. When a number moves, the *why* almost never lives next to the number. It's scattered across warehouse tickets, CRM notes, and field reports that nobody has time to cross-reference. And the right explanation for a movement depends on who's asking and what they plan to do about it.

Most analytics tools stop at *"revenue dropped 18%."*

**Ours keeps going:** which department, driven by what, how confident are we, what should you actually do, and who should do it.

<br>

---

## 🔑 What Makes This Different

<table>
<tr>
<td width="70%">

### The LLM is never the source of quantitative truth.

Every number here — every anomaly flag, every department breakdown, every contribution percentage, every confidence score — comes from deterministic statistics, SQL-style aggregation, or embedding-based retrieval. We instrumented a **live telemetry ledger** that proves this, rather than asking anyone to take our word for it: the diagnostic core of this system runs with **zero generative AI calls**, end to end.

A single language model call exists in the entire pipeline — narrative phrasing, applied only *after* every fact has already been decided. It is constrained by a strict system prompt to never add, alter, or invent anything it wasn't explicitly given, and it falls back automatically to a plain templated version of the same facts if it's ever unavailable.

We tested that fallback **live**, against a genuine API billing interruption during development — the system kept working without a pause.

</td>
<td width="30%" valign="top">

**At a glance**

| | |
|---|---|
| 🧮 Deterministic core | **100%** |
| 🤖 LLM calls in pipeline | **1** (narrative only) |
| 📊 Real transaction rows | **421,570** |
| 🏬 Stores / Departments | **45 / 81** |
| ✅ Mandated scenarios | **5 / 5** |
| 🔗 Connected KPIs | **5** |

</td>
</tr>
</table>

> This isn't a limitation we're hiding. **It's the design principle the problem statement is explicitly asking for.**

<br>

---

## 🏗️ System Architecture

```
                    Real Data (structured + unstructured)
                                    │
                                    ▼
                 ┌──────────────────────────────────┐
                 │   📡 Signal Detection              │   Statistical process control +
                 │   pure statistics                  │   seasonal decomposition
                 └──────────────────┬─────────────────┘
                                    ▼
                 ┌──────────────────────────────────┐
                 │   🗄️ SQL Decomposition             │   Department-level
                 │   deterministic                    │   contribution ranking
                 └──────────────────┬─────────────────┘
                                    ▼
                 ┌──────────────────────────────────┐
                 │   🔍 Hybrid RAG Retrieval          │   BM25 + dense embeddings,
                 │   semantic search                  │   fused via RRF
                 └──────────────────┬─────────────────┘
                                    ▼
                 ┌──────────────────────────────────┐
                 │   🤖 Agent Orchestration           │   LangGraph ReAct loop —
                 │   state machine                    │   holds multiple hypotheses
                 └──────────────────┬─────────────────┘
                                    ▼
                 ┌──────────────────────────────────┐
                 │   🎯 Confidence Scoring            │   Agreement + match strength
                 │   calibrated, honest               │   + self-consistency
                 └──────────────────┬─────────────────┘
                                    ▼
                 ┌──────────────────────────────────┐
                 │   ✅ Recommendations               │   driver → lever → action →
                 │   structured, safe                 │   impact → owner → monitoring
                 └──────────────────┬─────────────────┘
                                    ▼
                 ┌──────────────────────────────────┐
                 │   💬 Persona Narratives            │   LLM phrases the facts above —
                 │   LLM, fact-constrained            │   never decides them
                 └──────────────────┬─────────────────┘
                                    ▼
                 ┌──────────────────────────────────┐
                 │   🔐 Feedback + Security           │   Overrides logged & monitored;
                 │   + Telemetry                      │   role-based access enforced
                 └──────────────────────────────────┘
```

Every box above is a real, tested, working code path — **not a diagram of intent.** The system is reachable three ways: direct Python, a REST API with interactive docs, and a reference web interface — all backed by the exact same pipeline.

<br>

---

## 📊 Real Data, Real Anomalies, No Hand-Waving

We didn't script fake scenarios. Every demo case is anchored to a genuine anomaly found by scanning **421,000+ real transaction rows**.

| Data Source | What It Is | Grain | Cadence |
|:---|:---|:---:|:---:|
| **Sales transactions** | 45 stores, 81 departments, real weekly sales | store × dept × week | Weekly |
| **Operations/markdown feed** | Store-level markdowns, fuel price, CPI, unemployment | store × week | Weekly |
| **Field reports** *(curated)* | 79 tickets — warehouse, CRM, field reports, access-tagged | event-level | Ad-hoc |

**Five connected KPIs**, chained through one primary metric — not five unrelated numbers sitting side by side:

```
total_weekly_revenue  (primary)
  │
  ├── dept_revenue_share     →  decomposes revenue by department
  ├── regional_revenue       →  rolls revenue up by region
  ├── markdown_spend         →  a driver influencing revenue
  └── holiday_lift_pct       →  explains seasonal swings in revenue
```

Every KPI's formula, threshold, lineage, and access rule lives in one governed semantic contract (`kpi_contract.yaml`) — a single source of truth every downstream module reads from, so no two parts of the system can silently disagree about what *"revenue"* means.

<br>

---

## ✅ The 5 Mandated Scenarios — All Working, All Real

<table>
<tr><td width="8%" align="center"><b>1</b></td><td width="92%">

**Clean Single-Cause Diagnosis**
Store 18 — real **-52.9% drop ($606,984)**. A weather-driven distribution disruption. Evidence converges cleanly across warehouse, field, and customer-complaint sources.
`Confidence: HIGH (1.0)`

</td></tr>
<tr><td align="center"><b>2</b></td><td>

**Multi-Factor Movement, Disentangled**
Store 27 — real **-25.7% drop ($522,683)**. Three plausible causes on the table — marketing pause, staffing gap, competitor entry. The system doesn't just pick one: it explicitly evaluates and **refutes** the supply-disruption hypothesis after finding a ticket that directly contradicts it *("no stockout on record, inventory levels normal")*, correctly promoting reduced promotional visibility as the real driver instead. **This is reasoning, not pattern-matching.**

</td></tr>
<tr><td align="center"><b>3</b></td><td>

**Low-Confidence Abstention**
Store 17 — real **-23.9% drop ($253,791)**. Retrieved evidence directly contradicts itself — one ticket implies a shortage, another's inventory audit confirms full stock. The system detects the contradiction and **halts before ever building a hypothesis**, rather than forcing a confident-sounding wrong answer.

</td></tr>
<tr><td align="center"><b>4</b></td><td>

**Sparse-History / Newly-Launched KPI**
Store 3 / Dept 83 *(one week of history)* is compared against 14 peer stores of the same type via cohort proxy, with an automatic confidence ceiling applied. Store 7 / Dept 99 *(a single test-batch pilot, no valid peer group)* correctly **abstains entirely** rather than forcing a comparison against nothing.

</td></tr>
<tr><td align="center"><b>5</b></td><td>

**Role-Based Security**
Store 41 carries real HR-sensitive tickets tagged `restricted`. A regional manager in the correct region sees only standard-access evidence; the same manager in the wrong region is **denied outright**, before any data is touched; HR and Legal see everything. Enforcement happens at the data-query layer, not hidden in a UI toggle.

</td></tr>
</table>

<br>

---

## ⚖️ What's Deterministic vs. What Runs Through AI

| Component | Method | LLM Involved? |
|:---|:---|:---:|
| Materiality detection | Statistical process control + STL seasonal decomposition | ❌ |
| Department decomposition | SQL-style contribution ranking | ❌ |
| Evidence retrieval | BM25 + sentence-transformer embeddings, RRF fusion | ❌ *(embedding, not generative)* |
| Contradiction detection | Rule-based opposing-phrase heuristics | ❌ |
| Hypothesis ranking | Deterministic scoring *(support − refutation + numeric weight)* | ❌ |
| Confidence scoring | Agreement / match-strength / self-consistency, weighted | ❌ |
| Recommendations | Pre-approved action templates, slot-filled with real numbers | ❌ |
| **Persona narratives** | LLM phrasing of already-decided facts | ✅ **the one exception** |

> **Measured result across every investigation run:** the diagnostic core is **100% deterministic**. One LLM call exists in the entire system — narrative synthesis — and it is fact-constrained, with a validated graceful fallback to a template on any failure.

This isn't a claim on a slide — it's a number the system computes about itself via a live telemetry ledger, logged with real per-step latency *(sub-millisecond for reasoning steps, ~20ms warm / up to 3.4s cold-start for embedding retrieval)*.

<br>

---

## 🖥️ How to Interact With It

The same pipeline is reachable **three ways**, all producing identical results:

| | |
|---|---|
| **🐍 Direct Python** | Run any of the five scenario scripts individually, or all five in sequence, and read the full investigation trail printed to your terminal. |
| **🌐 REST API** | A FastAPI service exposing `/api/investigate`, a role-scoped `/api/investigate/secure`, feedback capture, and telemetry endpoints — interactive docs at `/docs`. |
| **🖱️ Reference UI** | A case-file style investigation console that calls the API live and renders the trail, hypothesis cards *(supported vs. refuted)*, the confidence verdict, the recommendation, and both persona narratives. |

Nothing in the UI or API is scripted or pre-computed — every result you see there is generated by the same pipeline you can also run from the terminal.

<br>

---

## 🛠️ Tech Stack

<table>
<tr>
<td><b>Orchestration</b></td><td>LangGraph (ReAct-pattern state machine)</td>
</tr>
<tr>
<td><b>Retrieval</b></td><td>ChromaDB, <code>sentence-transformers</code> (all-MiniLM-L6-v2), <code>rank-bm25</code></td>
</tr>
<tr>
<td><b>Statistics</b></td><td><code>statsmodels</code> (STL decomposition), custom control-limit implementation</td>
</tr>
<tr>
<td><b>LLM</b></td><td>Anthropic Claude — narrative synthesis only, automatic template fallback</td>
</tr>
<tr>
<td><b>API</b></td><td>FastAPI, full interactive documentation</td>
</tr>
<tr>
<td><b>Data</b></td><td><code>pandas</code>, YAML-governed semantic contracts</td>
</tr>
<tr>
<td><b>Language</b></td><td>Python 3.12</td>
</tr>
</table>

<br>

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
├── 8_narrative_layer/        Persona-specific narratives — LLM synthesis + fallback
├── 9_feedback_loop/          Override capture, drift monitoring
├── 10_security/              Role-based access enforcement
├── 11_telemetry/             Latency logging, cost tracking, LLM/non-LLM ledger
├── 12_scenarios/             All 5 mandated demo scenarios, runnable individually or as one
├── api/                      FastAPI wrapper — investigate, secure, feedback, telemetry
├── ui/                       Reference investigation console (single-file, no build step)
└── docs/                     Business proposal, architecture diagram
```

<br>

---

## 🚀 Running It

**1. Set up the environment**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**2. Run all 5 mandated demo scenarios end-to-end, in the terminal**

```powershell
cd 12_scenarios
python __init__.py
```

Each scenario prints the full investigation trail — materiality check, decomposition, retrieved evidence, hypothesis scoring *(including refuted hypotheses)*, confidence tier with its component scores, the resulting recommendation, and both persona narratives.

**3. Or run the API and reference UI**

```powershell
cd api
python main.py
```

Then open `ui/index.html` in a browser — it connects to the running API automatically.

**Optional — enable live LLM narratives**

Add an `ANTHROPIC_API_KEY` to a `.env` file at the project root. Without one, the system runs exactly the same, using deterministic template narratives instead.

<br>

---

## ⚠️ Known Limitations


| Limitation | Detail |
|---|---|
| **Dataset-specific bindings** | The architecture generalizes, but few modules currently reference this dataset's exact column names directly rather than reading them dynamically from the KPI contract. Parameterizing this fully is the clearest next step toward a dataset-agnostic deployment. |
| **No formal causal inference or forecasting yet** | The multi-hypothesis reasoning tests and eliminates candidate causes against evidence — meaningful causal *reasoning* in practice — but it is not a formal causal-inference model with counterfactuals, and there is no predictive component. |
| **No free-text intent parsing** | The system takes structured input (store, department, week) rather than a natural-language question. An LLM-based intent-parsing layer in front of the existing pipeline is a natural, comparatively low-risk next step. |
| **STL seasonal decomposition** | Operates near its minimum reliable data requirement given the dataset's ~2.5-year span — flagged transparently rather than overstated. |

<br>

---

## 💡 Why This Approach

Most KPI-explanation tools either let a language model freestyle a plausible-sounding story from a prompt, or build a rigid rules engine that can't handle nuance.

**We built neither.**

Every number here is earned by real statistics or real retrieval. The system holds multiple hypotheses instead of collapsing to the first one. It actively looks for evidence that contradicts its own leading theory, and downgrades that theory when it finds it. And when the evidence genuinely doesn't support a confident answer, it says so, cheaply, before generating one — and tells you what would help.

**That's the actual hard problem in this track, and it's the one we built for.**

<br>

<div align="center">

---

*Team ZEUS · Accenture Innovation Challenge 2026 · Round 2*

</div>