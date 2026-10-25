# Interview notes

## What the agent does

For each request, it first determines whether deletion was authorized. It resolves current and historical identifiers, reconstructs resource state at the audit cutoff, applies the supplied policy, and produces findings, ordered remediation, and verification. Workflow completion and operation success remain claims until direct evidence establishes the resulting state.

## Architecture

Python modules separate ingestion, intent, artifact extraction, identity resolution, timeline reconstruction, policy, planning, validation, and export. OpenRouter free models interpret each distinct request text once in bounded batches. The final run uses local PDF extraction and OCR geometry for screenshots. Model interpretations pass schema validation; native row and panel bindings constrain artifact ownership. Paid model IDs and nonzero routing prices are rejected.

## Evidence and identity

The supplied request email can match a current or historical address. Only aliases known at the cutoff are eligible; shared ambiguous aliases and names alone do not establish ownership. Both capture and observation timestamps must precede the cutoff. Trace IDs connect related log lines, explicit catalog links resolve business references, and replica scopes remain separate so a clean primary cannot conceal a remaining replica.

## Policy and remediation

Policy chooses deletion, redaction, anonymization, or retention. Tombstones preserve the permitted stable internal reference while removing prohibited direct identifiers. Unsafe synchronization and restore paths are stopped before record changes. Findings cite eligible evidence; proposed work and future checks have empty citations. Required retained records receive presence checks.

## Evaluation and cost

The public development set has 32/32 matching statuses, 72.11% exact step precision, 70.98% recall, 82.59% positional field accuracy, and 7/32 exact sequences. Independent fixtures exercise non-deletion, complete deletion with required retention, and incomplete deletion with records, flows, and backups. Additional tests cover cutoff isolation, replica drift, screenshot ownership, free-only routing, and trace redaction. Hidden accuracy is not known.

The final output contains all 518 cases. Its cached preprocessing attributes 21,996 input and 18,004 output tokens: 40,000 total, or 77.22 per request, across 13 free-model responses. The final rerun has zero new cloud calls and $0 reported cost. Exploratory calls unused by final predictions are not assigned to the final run.

## Be candid about limits

Some deleted physical resource keys cannot be connected to a subject using eligible evidence; verification then uses a supplied stable subject lookup reference. Negative checks also rely on a documented completeness assumption for dedicated snapshots and unfiltered global exports. These choices and differing citations or coverage contribute to sequence mismatches. More explicit source query coverage and persistent historical resource mappings would improve certainty without inventing identifiers or using hidden answers.
