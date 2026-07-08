# Machine-Sortable Filing Prompt

Use this prompt for future AI agents, teammates, and project automation working inside the Vagus Graph folder.

## System Instruction

When creating project records for Somach.life, use machine-sortable ISO 8601 filenames and structural category prefixes. Do not use alphabetical month names, informal date strings, or spaces in metadata-heavy filenames.

Use this pattern:

```text
YYYY-MM-DD_[Category]_[Project]_[Short-Description].[Extension]
```

Example:

```text
2026-07-07_RD_vagus-graph_hackwithbay-story.md
```

## Why This Matters

Alphabetical month abbreviations and single-digit days break chronological sorting in bash, Python, file explorers, and AI indexing workflows. For example, `2026-Jul-10` can sort before `2026-Jul-7` because plain ASCII sorting compares characters, not calendar meaning. ISO 8601 dates solve this:

```text
2026-07-07
2026-07-08
2026-07-10
```

The category prefix also supports USCIS STEM OPT audit alignment. Each project artifact should be easy to map back to the training objectives in the Form I-983, especially Applied Computer Science and Cognitive Neuropsychology work.

## Categories

- `RD`: Research & Development, including computational neuroscience, cognitive modeling, physiological inference, and product experiments.
- `ENG`: Software Engineering, including codebase work, databases, integrations, APIs, deployment, and testing.
- `DES`: Product Design, including user flows, interface design, spatial UI mockups, and demo narratives.
- `OPS`: Operations, including incorporation, legal, finance, compliance, submissions, partner materials, and audit records.

## Delimiters

Use underscores to separate metadata sections:

```text
[Date]_[Category]_[Project]_[Description]
```

Use hyphens inside multi-word project names and descriptions:

```text
2026-07-08_OPS_vagus-graph_hackwithbay-submission-details.md
```

This keeps filenames readable for humans and parseable by regex-based AI tools.
