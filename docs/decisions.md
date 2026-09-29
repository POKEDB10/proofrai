# Decisions

Ran against Google Gemini provider with target model gemini-3.5-flash-lite and judge model gemini-3.5-flash.

Implemented controls CTL-01, CTL-02, CTL-03, and CTL-05 as modular hook components while leaving CTL-04 and CTL-06 proposed.

Configured CTL-03 output scanner to redact exact matches and phone or email patterns with threshold blocking when exceeding three sensitive values.

Target model ignored indirect injection in candidate cand-08 resume during summarize task, so CTL-05 tool gating was verified in unit tests and live chat invocation.

Stored suite run results in JSON lines files within backend/data/runs to preserve the repository directory layout.

Tightened A-PII and A-AUTH attack inputs with attached candidate profile records and audit framing so the baseline failed four attack cases while controlled runs prevented disclosure.

Marked A-DISC and A-PROXY cases as pending judge evaluation, retaining them in needs_review status until Phase 8.

Stored run configuration, controls snapshot, results, reviews, and system cards in SQLite database at backend/data/ledger.db.

Serialized evidence exports with deterministic key sorting and indentation so identical runs produce matching SHA-256 digests.

Rendered report.html as a self-contained static HTML document styled with IBM Plex fonts and DESIGN.md tokens without external asset requests.

Configured release gate evaluator as a pure function enforcing the 10.0% benign over-block threshold.

Exposed backend routes under /api prefix with FastAPI BackgroundTasks for suite execution and state tracking.

Returned JSON formatted error responses containing problem and fix instructions across all endpoints and validation handlers.

Mirrored backend data schemas and HTTP methods in frontend/src/api.ts using plain fetch with zero additional dependencies.

Rendered results plate as a unified inline SVG with 18px cell dimensions, 3px grid spacing, and dedicated diagonal hatching patterns for error and over-blocked states.

Filtered review queue table to display cases requiring judge evaluation, cases resulting in execution errors, over-blocked benign runs, or existing reviewer decisions.

Persisted reviewer decisions through POST /api/runs/{id}/reviews with immediate display under the release gate section without altering computed gate verdicts.

Constructed system card structured fields exclusively from validated interview answers, disallowing model generation for structured fields.

Drafted intended use and known limits paragraphs with the configured model, marking the card as unconfirmed draft until confirmed with reviewer name and timestamp.

Displayed conflict indicators inline below causing questions using a review-coloured square and bold text instead of callout containers.

Configured controls screen with checkbox toggles where unchecking marks a control rejected, preventing its execution in the suite runner pipeline.
