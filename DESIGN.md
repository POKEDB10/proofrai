# DESIGN.md

Interface rules for ProofRAI. These replace any earlier UI guidance. `AGENTS.md` still applies: no dependencies beyond the allowed list, no extra screens, no decoration.

## 1. Brief

**Subject.** A test report for an AI assistant. A person describes the assistant, chooses safeguards, runs the same tests with and without them, and reads the evidence.

**Audience.** A developer or reviewer at a small team, on a laptop, reading closely. They are checking a claim, not being sold one.

**Job of the interface.** Make one thing easy to see: for each test case, what the assistant did before the controls, what it did after, and which control made the difference.

**Vernacular to borrow from.** Diff viewers, test matrices, lab result sheets, code review. Not SaaS marketing pages.

## 2. Direction

Quiet, dense, exact. Everything is a table, a rule or a line of text, except one element.

**The one memorable element is the results plate**: a single strip of small squares, one per test case, with a baseline row above a controlled row. A reader sees at a glance where a red square became green, and where a control broke a legitimate task. Spend the design effort here. Keep everything around it plain.

**The second distinctive behaviour is inline evidence**: when a check fails, the exact text that caused it is highlighted in the response. A leaked date of birth, an obeyed canary word, a tool call the model tried to make. The interface shows proof at the span level, not a score.

Left-aligned everywhere. Nothing is centred. No hero. The first screen is the first question.

## 3. Defaults this project rejects, and why

Research on AI-generated interfaces converges on the same cluster of tells. Any one is a design choice. Several together read as generated. Treat this table as a ban list.

| Tell | Rule |
|---|---|
| Inter, Roboto, system-ui as the only typeface | IBM Plex Sans and IBM Plex Mono only |
| Purple, indigo or blue-violet anywhere; blue-to-purple gradients | No gradients of any kind. No blue-violet hues in the palette |
| A warm cream background with a serif display face and a terracotta accent | Cool grey ground, white working surfaces, no serif, no warm clay accent |
| Everything in a rounded card, cards inside cards, one radius on everything | No cards. Structure comes from rules and whitespace. Radius only on controls and plate cells |
| Soft grey shadow under every panel | No shadows at all |
| Glass or blur effects | Banned |
| Coloured left-border callouts and quote blocks | Banned. Use a bold label and a rule |
| Icons or emoji inside small tinted squares | No emoji. No decorative icons. Three functional icons only (section 9) |
| Three identical feature cards in a row | Not applicable: there is no marketing content |
| Permanent dark theme with one neon accent | Light only |
| Tracked-out uppercase eyebrow above every heading | No uppercase text. No eyebrows |
| Meta strings joined with middle dots; spaced em-dash labels; arrows appended to buttons | Banned in interface copy |
| Numbered markers (01, 02, 03) on things that are not a sequence | Numbers appear only on the five workflow steps, which are a sequence, and in data |
| Two equal-weight buttons side by side | One solid button per view. Other actions are text links |
| One word in a headline given a different colour or italic | Banned |
| Fade-and-slide entrance on every section, hover lift on every card | No entrance animation. No hover motion |
| Vague uplift copy ("Build trust in your AI") | Plain, specific, short. See section 8 |

## 4. Tokens

All colour, size and radius values live in `frontend/src/styles/tokens.css`. That file is the only place a colour literal may appear. Every other stylesheet uses `var(--...)`.

    :root {
      --ground: #EEF0F2;        page background
      --surface: #FFFFFF;       tables, panes, forms
      --surface-hover: #F3F5F7; row hover, selected row
      --ink: #1E2530;           text, primary button
      --ink-2: #56606E;         secondary text, table headers
      --rule: #CBD1D8;          borders
      --rule-soft: #E1E5E9;     row dividers

      --pass: #1B6E4F;
      --fail: #B3261E;
      --review: #9A6700;
      --fail-wash: #F6DAD7;     highlight behind leaked or forbidden text
      --mark: #F3DC8B;          highlight behind canary text and tool attempts

      --font-sans: "IBM Plex Sans", sans-serif;
      --font-mono: "IBM Plex Mono", monospace;

      --text-meta: 12px;
      --text-table: 13px;
      --text-body: 15px;
      --text-section: 18px;
      --text-title: 26px;

      --radius-control: 3px;
      --radius-cell: 2px;

      --space-1: 4px;
      --space-2: 8px;
      --space-3: 12px;
      --space-4: 20px;
      --space-5: 32px;
      --space-6: 56px;
    }

Colour means one thing each. Ink is for text and the single primary action. Green, red and ochre mean pass, fail and review, nowhere else. Never use a status colour for decoration, links or emphasis.

Links are ink with an underline. Visited state is not styled.

## 5. Type

- Load fonts locally through `@fontsource/ibm-plex-sans` (weights 400 and 600) and `@fontsource/ibm-plex-mono` (weights 400 and 500). No external font requests.
- Two weights only in sans: 400 and 600.
- Body 15px, line-height 1.5. Table text 13px. Meta text 12px. Section headings 18px at 600. Page title 26px at 600, line-height 1.2.
- Sentence case everywhere. No uppercase. No letter-spacing.
- Prose lines are at most 68 characters wide.
- Mono is for content that is literally machine text: model responses, ids (`CTL-05`, `A-INJ-02`), hashes, model names, counts in tables. Do not use mono for decorative small labels.
- Numeric columns are right-aligned with `font-variant-numeric: tabular-nums`.

## 6. Layout and components

**Page.** Ground colour behind everything. Content column is at most 1200px, left-aligned, 32px side padding. Working areas (tables, panes, forms) sit on `--surface` with a 1px `--rule` border. Nothing sits inside a bordered thing that is itself inside a bordered thing.

**Top bar.** 44px tall, `--surface`, 1px bottom rule. From the left: the wordmark "ProofRAI" as plain text at 600, then the five steps, then on the far right the current run id and target model in mono at meta size.

Steps read: `1 Describe`, `2 Card`, `3 Controls`, `4 Test`, `5 Evidence`. The current step has weight 600 and a 2px ink underline. Steps may carry a short live count where it means something: "Controls (4 approved)", "Test (run 2f9a)". No icons.

**Buttons.** Primary: ink background, white text, 32px tall, `--radius-control`, 14px side padding. Text label states the action: "Run suite", "Save answers", "Confirm card". One primary per view. Every other action is a text link with an underline. No outlined-secondary buttons.

**Inputs.** 32px tall, 1px `--rule` border, `--radius-control`, `--surface` background. Native radio buttons and checkboxes with `accent-color: var(--ink)`. Labels sit above inputs, at 13px and 600.

**Focus.** `outline: 2px solid var(--ink); outline-offset: 2px` on every focusable element. Never removed.

**Tables.** Header row: 12px, 600, `--ink-2`, 1px ink bottom border. Body rows 32px minimum, 1px `--rule-soft` between rows. Hover and selected rows use `--surface-hover` as a full-row background. No coloured left edge on selected rows. Expanded rows open instantly and contain their content directly on `--surface`, with panes divided by a single 1px rule.

**Status marker.** An 8px square filled with the status colour, then the word: Pass, Fail, Review, Error, Over-blocked. Colour never appears without the word.

**Radius.** `--radius-control` on buttons and inputs, `--radius-cell` on plate cells, `0` on everything else.

**Spacing.** Tight inside a group (`--space-2`), looser between groups (`--space-4`), largest between sections (`--space-5`). Do not space everything evenly.

## 7. Screens

Wireframes are plain text. Match the structure, not the exact widths.

### 1 Describe

Single column, 640px wide.

    Describe the assistant

    Eight questions about how it is used. Your answers shape the
    system card and the proposed controls.

    What does the assistant do?
      [x] Summarises applications   [x] Answers candidate questions
      [x] Drafts screening notes    [ ] Sends messages

    ...

    Outputs are used to
      ( ) inform recruiters   ( ) determine outcomes   ( ) neither

    Where does a person step in?
      ( ) never  ( ) before actions  ( ) always
      Conflict: outputs determine outcomes and no person steps in.

    [Save answers]

A conflict flag appears under the question that caused it. It is a line of text with the bold word "Conflict" and a review-coloured square. Not a callout box.

### 2 Card

A document. Fields as a two-column list: label in `--ink-2`, value in ink. Below it, the two drafted paragraphs (intended use, known limits).

While unconfirmed, a line above the drafts reads "Draft. Not confirmed." After confirming it reads "Confirmed by (name) on (date)." Drafts are editable text areas. Primary button: "Confirm card". Text link: "Regenerate drafts".

### 3 Controls

    Controls                                           4 of 6 approved

    Approved  ID      Control                        Acts at       Addresses
    [x]       CTL-01  Minimise protected fields      Before model  Disclosure
    [x]       CTL-02  Treat candidate text as data   Before model  Injection
    [ ]       CTL-04  Require job-related rationale  After model   Unjustified output
    ...

    Only approved controls run.                        [Go to test]

Row expands to show rationale, references (source names as text, external links where a URL exists) and the test ids that check the control.

### 4 Test

    Test                                                      [Run suite]
    Target gemini-...   Judge gemini-...   Suite v1, 30 cases   Controls 9c1e4a

    Results plate
    baseline     ■■■■■■□■■■■■■■■■  ■■■■■■■■■■■■■■
    controlled   ■■■■■■■■■■■■■■■■  ■■■■■■■■■■■■■■
                 Attack, 16        Benign, 14

    Attack pass rate      6 of 16     ->   14 of 16
    Benign completion    14 of 14     ->   11 of 14
    Over-blocked                      3

    Filter: All  Failures  Over-blocked  Needs review

    Case      Task              Baseline   Controlled   Acted
    A-INJ-01  Summarise resume  Fail       Pass         CTL-02, CTL-05
    ...

    (expanded row)
    Baseline                              | Controlled
    (response with highlighted evidence)  | (response with highlighted evidence)
    Control events                        | Checks
    CTL-05  queue  advance_candidate      | tool_not_executed   Pass

The plate is one inline SVG. Cells are 18px squares with a 3px gap and a wider gap between the attack and benign groups. Fill by verdict: pass, fail, review, error (grey with hatch), over-blocked (fail with hatch). Hatching is an SVG pattern, never a CSS gradient. Each cell has a `<title>` and an `aria-label` with case id and verdict. Activating a cell opens that case row. Cells that have not run are outlined only.

During a run, cells fill in as results arrive. This is the progress indicator: there is no spinner and no shimmer. A text line beside the button reads "Running case 12 of 30".

Response text is shown in mono at 13px with `white-space: pre-wrap`. Highlights use `<mark>`: leaked or forbidden text on `--fail-wash`, canary text and attempted tool calls on `--mark`. Each highlight has a title naming the check that found it.

Cached results carry the word "cached" in meta text next to the timestamp.

### 5 Evidence

    Evidence                                     Run 2f9a1c

    Release gate
    ■ Review required
    Reasons
      3 benign cases were blocked by CTL-01 or CTL-03 (over-block rate 21%).
      2 results need a person to review.

    Review queue
    Case      Why it is here        Response      Decision
    ...

    Your decision
      ( ) Accept  ( ) Reject  ( ) Needs work
      Comment [                                   ]
      [Save decision]

    Download evidence (JSON)   Open report

The gate label is 26px at 600 with its status square. No banner, no coloured panel. Reasons are plain sentences with numbers. The human decision is shown below the gate and never alters it.

## 8. Copy

Words are design content. Each element does one job.

- Sentence case. Active voice. No exclamation marks. No em dashes.
- Buttons and links say what happens: "Run suite", "Save decision", "Download evidence (JSON)". A thing keeps its name across the flow: if the button says "Confirm card", the message afterwards says "Card confirmed".
- Name things by what the user understands: "controls", "test cases", "baseline", "controlled", "over-blocked". Not "guardrails", "agents", "pipelines".
- Numbers instead of adjectives: "3 of 14 legitimate tasks were blocked", not "some tasks were affected".
- Empty states say what to do. Errors say what happened and what to do next, and never apologise.
- Banned words are listed in `AGENTS.md` section 8.

| Instead of | Write |
|---|---|
| Welcome to ProofRAI! | (nothing; open on the first question) |
| Unlock the power of trusted AI | Describe the assistant |
| Something went wrong | The run stopped at A-INJ-02: the model returned a rate-limit error. Progress is saved. Run again to continue. |
| No data available | No runs yet. Run the suite to compare baseline and controlled. |
| Submit | Save answers |
| Your AI is safe | 14 of 16 attack cases passed. 2 did not. |
| Loading... | Running case 12 of 30 |

## 9. Motion, icons, accessibility

**Motion.** One animation exists: `cell-in`, a 120ms opacity change when a plate cell receives its verdict. Expanders, menus and tabs open instantly. Nothing animates on page load or on hover. Respect `prefers-reduced-motion` by removing `cell-in`.

**Icons.** Three inline SVGs, 16px, 1.5px stroke, `currentColor`: chevron (expand and collapse), close, external link. No icon library. No other icons.

**Accessibility.** Text contrast at least 4.5:1. Status is always colour plus word plus shape. All controls reachable by keyboard in a sensible order. Tables use real `<table>` markup with `<th scope>`. The plate cells are focusable and labelled.

**Viewport.** Designed for 1280px and wider. Below that, tables scroll horizontally inside their container. No mobile layout.

## 10. Self-review

After every interface phase, take screenshots at 1440 by 900 (or describe the layout precisely if screenshots are unavailable) and answer each question in writing. Fix any "no" before moving on.

1. If the wordmark were hidden, would a stranger still know this is a test report tool?
2. Is the results plate the strongest thing on the Test screen, and is everything else quieter than it?
3. Is any text a font other than IBM Plex?
4. Is there any gradient, shadow, blur, emoji, decorative icon or uppercase text?
5. Is there any bordered box inside another bordered box?
6. Does any status colour appear without its word?
7. Is there more than one solid button in the view?
8. Does every highlight in a response point to a real failed check?
9. Read every string aloud. Does any sound like a slogan?
10. Does `python scripts/style_check.py` pass?
11. Does the view still work using only the keyboard?
12. Is anything on screen there because a template would have put it there, and not because the reader needs it?
