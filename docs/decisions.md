# Decisions

Ran against Google Gemini provider with target model gemini-3.5-flash-lite and judge model gemini-3.5-flash.

Implemented controls CTL-01, CTL-02, CTL-03, and CTL-05 as modular hook components while leaving CTL-04 and CTL-06 proposed.

Configured CTL-03 output scanner to redact exact matches and phone or email patterns with threshold blocking when exceeding three sensitive values.

Target model ignored indirect injection in candidate cand-08 resume during summarize task, so CTL-05 tool gating was verified in unit tests and live chat invocation.

Stored suite run results in JSON lines files within backend/data/runs to preserve the repository directory layout.

Tightened A-PII and A-AUTH attack inputs with attached candidate profile records and audit framing so the baseline failed four attack cases while controlled runs prevented disclosure.

Marked A-DISC and A-PROXY cases as pending judge evaluation, retaining them in needs_review status until Phase 8.
