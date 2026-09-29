# Research model placeholders

This directory contains pinned research checkpoints and generated structural
ONNX stubs that are available only for integration and compatibility testing.
They are not approved releases and
must never be copied into `models/releases/`, advertised as field validated, or
enabled for farmer-facing diagnosis.

Every placeholder package is disabled by default and records its immutable
source revision, file hashes, label order, preprocessing contract, known
evidence gaps, and intended routing role. The standalone release catalog remains
the only activation boundary: `models/catalog.json` still requires separately
approved identifier and crop-specialist releases.

The first package, `ktt-mobilenetv3-int8`, is a compact MIT-declared ONNX model
used to prove model loading and modular routing. It covers common bean, cassava,
and maize labels. Only maize intersects the current India-common-crop catalog,
so it cannot serve as the general crop identifier or an all-crop specialist.

The `stub-disease-*` packages cover 15 high-priority Indian crop integration
slots. Their disease taxonomies are drafts, and their ONNX graphs intentionally
emit constant zero logits. They let the application test package discovery,
crop-specific routing, lazy loading, tensor compatibility, and fallback behavior
without pretending that untrained weights can diagnose plants. Every stub sets
`diagnostic_capability: false`, prohibits activation, and is rejected by the
approved-release catalog.

Regenerate the structural stubs in a Python environment with `onnx==1.19.0`
and `numpy`:

```powershell
python scripts/generate_top15_placeholder_models.py
```

Run the integrity checks with:

```powershell
python scripts/validate_placeholder_models.py --require-installed
```

Graph and golden-output checks require ONNX Runtime. A reproducible container
command is documented in the package manifest; those checks do not change the
application dependency locks.
