# EU AI Act Governance Workspace

An AI governance prototype for assessing enterprise AI use cases against the EU AI Act.

Live application: `Add your Streamlit link here`

## Overview

This application turns a simple compliance chat into a structured governance workflow. It combines retrieval over the EU AI Act, rule-based decision support, LLM reasoning, confidence scoring, and a review board for persisted assessments.

## Highlights

- `RAG over the EU AI Act`: retrieval from a locally processed HTML version of the regulation
- `Structured decision engine`: rule-based signals for surveillance, employment context, biometric use, synthetic media, consent-sensitive scenarios, and self-use assistants
- `Human-in-the-loop refinement`: targeted follow-up questions only when facts are missing
- `Explainability`: decision flow diagram, source excerpts, legal locators, and confidence breakdown
- `Review Board`: persisted cases with sortable issue keys in the format `COMPL-XXX`
- `Cloud-backed persistence`: local SQLite for development, Supabase Postgres for hosted usage
- `CI workflow`: GitHub Actions pipeline with automated benchmark checks

## What it does

- classifies AI use cases into `high-risk`, `transparency`, `minimal`, or `unclear`
- asks refinement questions when the initial description is incomplete
- shows supporting legal references from the EU AI Act
- calculates confidence using retrieval quality, citation coverage, decision clarity, locator quality, and consistency
- stores and manages assessment cases with workflow status:
  - `Draft`
  - `Needs More Info`
  - `In Review`
  - `Approved`

## Architecture

- `Frontend`: Streamlit governance workspace + dedicated Review Board
- `LLM`: DeepSeek via OpenAI-compatible API
- `Retrieval`: SentenceTransformers + FAISS
- `Decision logic`: custom rule engine in `app/decision_engine.py`
- `Persistence`: SQLite locally, Supabase Postgres when `SUPABASE_DB_URL` is configured
- `Testing / CI`: pytest + GitHub Actions

## Delivery / Engineering Practices

- Git-based workflow with `main` and optional `dev` branch
- automated CI on push and pull request via `.github/workflows/ci.yml`
- benchmark test coverage for core governance scenarios:
  - personal calendar assistant -> minimal candidate
  - employee monitoring -> high-risk candidate
  - employee marketing images without consent -> transparency candidate

## Key Files

```text
app/
  assessment_store.py
  confidence.py
  decision_engine.py
  llm.py
  rag_pipeline.py

ui/
  streamlit_app.py

tests/
  test_assessment_store.py
  test_confidence.py
  test_decision_engine.py
```

## Current Scope

- enterprise-style AI use case triage
- explainable classification support under the EU AI Act
- persisted review workflow with issue-style tracking
- hosted database support for cloud deployment

## Limitations

- prototype, not legal advice
- output quality still depends on the quality of the use case description
- Supabase setup currently uses direct database connectivity rather than a fully hardened production security model

## Next Steps

- improve memo-style legal answer formatting
- expand automated test coverage
- harden hosted database security and deployment configuration
