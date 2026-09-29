# Research candidate — not an approved release

This directory contains the exact public Hugging Face checkpoint at revision
`61aa6c309c8e023f1cef5761254039254fddebed` for `mesabo/agri-plant-disease-resnet50`.
It is a real trained PyTorch/Transformers source artifact, staged to support
ONNX export and evaluation work.

It is not enabled for farmer-facing diagnosis. The source reports PlantVillage
controlled-image evaluation only; India-specific field performance, unknown/OOD
rejection, agronomist taxonomy review, runtime parity, redistribution review,
and rollback identity remain incomplete.

Required next steps are: reproduce preprocessing from the downloaded processor,
export to ONNX, run static INT8 calibration, evaluate on independent Indian
field/OOD data, generate golden server/browser fixtures, complete named human
reviews, and only then create an immutable candidate bundle and approval entry.

The optional dynamic INT8 experiment is retained for traceability but is
rejected for deployment: ONNX Runtime 1.22.1 CPU cannot execute its
`ConvInteger` graph. It is not the required static-calibrated release artifact.
