# EU AI Act Governance Workspace

An enterprise-style AI governance prototype for assessing AI use cases against the EU AI Act.

This project combines retrieval-augmented generation, rule-based decision logic, confidence scoring, and a human-in-the-loop review workflow to turn a simple chat interaction into a reusable governance workspace. Instead of only answering questions, it helps structure AI assessments, surface missing facts, explain why a classification was reached, and preserve cases for later review.

## Why this project exists

Organizations adopting AI need more than a generic chatbot. They need a way to:

- triage AI use cases
- distinguish likely high-risk, transparency, minimal-risk, and unclear scenarios
- ask targeted follow-up questions when facts are missing
- trace answers back to legal sources
- keep a reusable record of prior assessments

This workspace is a prototype for exactly that use case.

## What the app can do

- Analyze AI use cases against the EU AI Act
- Retrieve supporting legal context from a locally indexed HTML version of the EU AI Act
- Combine rule-based risk signals with LLM reasoning
- Ask follow-up questions only when the answer affects classification
- Explain the decision flow behind a classification
- Show source excerpts with legal locators
- Estimate answer confidence based on retrieval, citations, locator quality, and consistency
- Save assessments into a lightweight governance queue
- Re-open, review, update, and delete saved cases
- Manage saved cases in a dedicated Review Board with sortable issue keys

## Core capabilities

### 1. AI use case assessment

Users describe an AI use case in plain language. The system retrieves relevant legal passages, analyzes the use case through a structured decision engine, and generates a classification-oriented answer.

### 2. Follow-up refinement

If key facts are missing, the app asks targeted follow-up questions such as whether a system affects employment decisions, uses biometric identification, or performs continuous monitoring. Follow-ups are tracked so previously answered questions are not repeatedly shown.

### 3. Explainable reasoning

The interface shows a decision flow diagram so users can inspect which rule categories were triggered, including areas such as:

- monitoring or surveillance
- employment context
- employment decision impact
- biometric identification
- emotion recognition
- synthetic media generation
- image or likeness usage
- consent-sensitive context
- personal assistant context

### 4. Source-backed responses

The app uses a local HTML copy of the EU AI Act, processes it into embeddings, and retrieves relevant chunks from a FAISS index. Each answer can reference supporting legal material with locators where available.

### 5. Governance workflow

Assessments can be saved and managed as reusable governance cases with review states:

- Draft
- Needs More Info
- In Review
- Approved

This turns the prototype into more than a chat UI. It becomes a lightweight review workflow for AI governance.

## Architecture overview

### Frontend

- `Streamlit`
- Glass-style governance workspace UI
- Chat interaction
- Insights panel with confidence gauge and decision flow
- Dedicated `Review Board` view for persisted assessment cases

### Retrieval layer

- `sentence-transformers` for embeddings
- `FAISS` for semantic search
- local EU AI Act HTML as the primary knowledge source

### Decision layer

- custom rule engine in `app/decision_engine.py`
- detects signals such as surveillance, employment context, biometric usage, synthetic media, consent-sensitive scenarios, and self-use productivity assistants

### LLM layer

- `DeepSeek` via OpenAI-compatible API client
- structured JSON responses
- classification constrained to:
  - `high-risk`
  - `transparency`
  - `minimal`
  - `unclear`

### Confidence layer

- combines:
  - retrieval strength
  - source coverage
  - decision clarity
  - citation strength
  - locator quality
  - consistency with structured rule signals

### Persistence

- saved assessments are persisted in SQLite locally
- when `SUPABASE_DB_URL` is configured, persistence switches to Supabase Postgres
- legacy JSON assessment data can be migrated automatically on first load
- issue keys are generated in the format `COMPL-XXX`

## How it works

1. A user enters an AI use case.
2. The app retrieves relevant chunks from the indexed EU AI Act.
3. A decision engine extracts structured risk and governance signals.
4. The LLM generates a structured answer using both retrieved context and decision hints.
5. The app calculates a confidence score and visualizes the decision flow.
6. If important facts are missing, follow-up questions are generated.
7. The user can refine the answer and save the case into a review workflow.

## Repository structure

```text
app/
  assessment_store.py      Lightweight persistence for saved assessments
  confidence.py            Confidence calculation logic
  decision_engine.py       Structured rule-based analysis
  llm.py                   DeepSeek/OpenAI-compatible answer generation
  rag_pipeline.py          FAISS retrieval pipeline

data/
  assessments/            Saved governance cases
  index/                  FAISS index + metadata
  raw/                    Source HTML files

tests/
  test_assessment_store.py
  test_confidence.py
  test_decision_engine.py

scripts/
  ingest.py               Builds the vector index from EU AI Act HTML

ui/
  assets/                 Background and UI assets
  streamlit_app.py        Main application
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/skulld0zer/compliance_llm.git
cd compliance_llm
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add environment variables

Create a `.env` file in the project root:

```env
DEEPSEEK_API_KEY=your_api_key_here
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_publishable_key
SUPABASE_DB_URL=your_supabase_postgres_or_pooler_connection_string
```

Notes:

- `SUPABASE_DB_URL` is optional for local-only use
- if it is set, the app will use Supabase Postgres instead of local SQLite
- if your database password contains special characters such as `?` or `@`, encode them in the connection string

## Data preparation

The project is designed to work with a local HTML copy of the EU AI Act. If you want to rebuild the retrieval index, place the source HTML in `data/raw/` and run:

```bash
python scripts/ingest.py
```

This generates the vector index and metadata used by the RAG pipeline.

## Run the app

```bash
streamlit run ui/streamlit_app.py
```

## Development workflow

This repository follows a lightweight Git-based workflow:

- `main` is the stable branch
- `dev` can be used as an integration or staging branch
- feature work should ideally happen in short-lived branches and be merged through pull requests

## Continuous integration

The project includes a GitHub Actions workflow in `.github/workflows/ci.yml`.

On every push or pull request to `main` or `dev`, the pipeline:

- installs dependencies
- validates Python syntax
- runs automated `pytest` checks
- verifies benchmark governance scenarios such as:
  - personal calendar assistant -> minimal candidate
  - employee monitoring -> high-risk candidate
  - employee marketing images without consent -> transparency candidate

You can run the same checks locally with:

```bash
pytest -q
```

## Example use cases

- "Can I monitor the productivity of my employees by utilizing AI-based surveillance software that monitors their screen activity during work hours?"
- "Can I use AI to track my own personal calendar and notify me if I booked two meetings at the same time?"
- "Can I generate marketing images with AI of my employees without their consent?"

## Current limitations

- This is a prototype, not a production legal advisory system.
- Some classifications still depend on the quality of the user's description.
- The current hosted persistence uses a direct database connection and is not yet hardened with a full production security model.
- The tool supports governance decision support, not legally binding advice.

## Roadmap

Planned next steps:

- stronger automated tests for rule logic and classification edge cases
- improved answer formatting for more memo-style legal output
- more deterministic handling of benchmark governance scenarios
- harden Supabase/Postgres security and deployment setup

## Disclaimer

This project is for prototyping, learning, and portfolio purposes. It does not provide legal advice and should not be used as a substitute for formal legal review.
