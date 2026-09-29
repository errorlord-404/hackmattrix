# Release evidence

The canonical release ledger is `tests/results/gate-results.json`, with
`tests/results/artifact-checksums.json` binding its referenced logs and outputs.
The ledger includes direct model-catalog validation and the real
Compose-backed Chromium/Firefox/WebKit matrix through the `model-catalog` and
`browser-matrix` gates. `docs/PARITY_REPORT.md` is generated from
that ledger. The current ledger is not release-ready: all implemented
software/deployment gates pass, while the CV approval gate remains failed
until real distributable model evidence is supplied and independently
approved.
