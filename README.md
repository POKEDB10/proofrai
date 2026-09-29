# ProofRAI

ProofRAI is an assurance workspace for language model assistants. It tests one target assistant, HireAssist, which assists recruiters with application summaries, candidate questions, and screening notes.

The system runs a closed loop in code: system description, identified risks, approved controls, application enforcement, comparative test execution on baseline and controlled versions, an evidence record, and human decisions.

ProofRAI does not make a model ethical, safe, or compliant, and it certifies nothing.

## Requirements

- Python 3.11 or later
- Node.js 18 or later
- An API key for Google Gemini, or a local Ollama instance

## Setup

1. Copy `.env.example` to `.env` and set required variables:

       PROVIDER=gemini
       TARGET_MODEL=gemini-3.5-flash-lite
       JUDGE_MODEL=gemini-3.5-flash
       GEMINI_API_KEY=your_gemini_api_key_here
       OLLAMA_URL=http://localhost:11434

   The judge model must differ from the target model to prevent self-evaluation bias.

2. Install backend dependencies:

       pip install -r backend/requirements.txt

3. Install frontend dependencies:

       npm --prefix frontend install

## Running checks

Run code quality and style validation:

    make check

This executes ruff, pytest (70 tests), TypeScript compilation, and scripts/style_check.py.

## Running the application

Start the backend API server:

    make dev-backend

The backend serves API endpoints at `http://localhost:8000/api`.

Start the frontend development server in a separate terminal:

    make dev-frontend

The interface opens at `http://localhost:5173`.

## Running the evaluation suite from the command line

Execute a comparative evaluation run across all 30 test cases:

    python -m backend.core.suite.cli --run-id run-01

The runner writes execution results to SQLite at `backend/data/ledger.db` and exports `evidence_run-01.json` and `report.html` to `examples/`.

## What this run shows

- Side-by-side comparison of baseline and controlled versions on 30 test cases (16 attack, 14 benign)
- Exact character span highlights for leaked sensitive fields and canary tokens
- Tool call gating that queues high-impact actions for human authorization
- Automated post-model criteria grounding checks for candidate screening notes
- Pre-model pattern detection and refusal of discriminatory filtering requests
- Release gate evaluation based on critical failures, review requirements, and benign over-blocking

## What this run does not show

- It does not prove that the assistant is safe or compliant for production deployment
- It does not evaluate live recruiter interactions, drift, or multi-turn conversational attacks
- It does not measure downstream human hiring outcomes or real workplace fairness
- It does not constitute legal advice or regulatory certification under the EU AI Act, NIST AI RMF, or local labour laws

## Repository layout

    proofrai/
      AGENTS.md
      DESIGN.md
      README.md
      Makefile
      .env.example
      backend/
        app/             FastAPI app, routes, settings
        core/
          llm/           adapter, providers, disk cache
          target/        HireAssist, simulated tools, prompts
          controls/      library loader, pipeline, one module per control
          suite/         case schema, runner, CLI
          checks/        deterministic checks
          judge/         rubric judge
          intake/        interview schema, conflict rules, risk map, system card
          ledger/        SQLite models, export
          gate/          release gate
        data/            candidates.json, jobs.json, control_library.yaml, suite.yaml
        tests/
      frontend/
        src/
          styles/        tokens.css, base.css, one css file per screen
          screens/       Describe, Card, Controls, Test, Evidence
          components/    only what two or more screens share
          api.ts
      scripts/
        style_check.py
      docs/
        decisions.md
        limits.md
      examples/          one committed evidence export

## Known limits

ProofRAI operates on a fixed suite of 30 synthetic test cases. All candidate profiles, resumes, and job listings use synthetic test data. For a complete list of technical and operational limits, see `docs/limits.md`.
