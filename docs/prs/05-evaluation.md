Title: Measure public-case accuracy and package only complete submissions

Adds status, exact-step, field, and sequence metrics; three independent end-to-end scenarios; CI; runnable setup instructions; and an allow-listed packager. Unresolved cases count as evaluation failures, and packaging refuses incomplete outputs or unfinished reports.

Validation: 23 unit/CLI integration tests, participant-data inventory, full local diagnostic run, and public-sample comparison. Current status accuracy is 22/32 and exact sequence accuracy is 5/32; unsupported cases count as failures. Development coverage and known failures are reported directly in evaluation Markdown; no hidden accuracy or final submission is claimed.
