# Known limits

ProofRAI evaluates safeguards on language model assistants through automated test execution. It does not certify systems, ensure compliance, or make models safe. The tool operates under the following technical and operational limits.

## Small fixed test suite

The test suite contains 30 test cases: 16 attack cases and 14 benign cases. A fixed suite of this size covers specific known failure modes, including prompt injection, demographic bias, and data leakage. It does not cover the full space of possible model inputs, multi-turn adversarial dialogues, or evolving jailbreak techniques.

## Synthetic data

All candidate records, resumes, and job descriptions are synthetic. Field values use distinctive test tokens to enable exact matching. Real recruitment documents exhibit greater syntactic variation, formatting irregularities, OCR errors, and domain jargon that synthetic test data does not reproduce.

## Single target assistant

ProofRAI evaluates one specific target assistant: HireAssist. The hooks, schemas, and candidate data structures are designed for this single recruiting workflow. The findings do not apply to other conversational assistants, tools, or domains without custom test suites and controls.

## No production monitoring

The evaluation runs offline against static test cases. It does not monitor live user traffic, track production drift, detect live security incidents, or observe feedback loops from real human recruiters.

## No audit of real hiring outcomes

The tests measure whether the assistant refused a prompt, masked a field, queued an action, or cited criteria in generated text. This does not measure whether downstream human hiring decisions are fair, unbiased, or merit-based. ProofRAI does not evaluate human recruiter behaviour or organisational hiring outcomes.

## No legal conclusions

ProofRAI does not verify compliance with any statute, regulation, or standard, including the EU AI Act, NIST AI RMF, OWASP LLM Top 10, or Digital Dubai guidelines. References to external frameworks are for technical cross-referencing only. ProofRAI provides test evidence, not legal advice or certification.

## Judge model limits

Automated model judges have documented biases:
- Length preference: longer explanations are often scored more favourably regardless of accuracy.
- Self-enhancement: models may favour outputs that match their own training patterns.
- Position sensitivity: order of prompt inputs can change the verdict.
- Superficial refusal detection: polite refusals that still provide harmful assistance can be misclassified as safe.

A judge model cannot verify factual ground truth, internal reasoning, or subtle policy nuance. For this reason, cases where the judge is uncertain enter the human review queue, and human reviewers can override any judged verdict.

## Results depend on the model tested

All metrics reflect the specific combination of target model, judge model, prompt versions, and temperature setting tested. Changing the model provider, upgrading a model checkpoint, or modifying the system prompt will produce different results.
