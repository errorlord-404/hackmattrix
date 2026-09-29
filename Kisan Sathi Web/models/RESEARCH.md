# Crop disease model research — 18 September 2026

## Conclusion

The requested two-stage design is feasible and is the best deployment shape:
a small crop identifier runs first, then the browser lazily downloads only the
selected crop's disease specialist. The same ONNX artifacts can run on a light
CPU server when the browser is unsupported or a safety gate fails.

There is no credible, field-validated, lightweight model on TorchVision or
TensorFlow Hub that diagnoses all common Indian crops. Those hubs provide
general ImageNet backbones. Public agriculture repositories mostly provide
datasets, training notebooks, or research checkpoints with insufficient
license, field, OOD, calibration, and cross-runtime evidence for direct use.

Accordingly, the system now contains modular slots for 26 crop specialists,
but no source is marked deployable. Eight crops have useful research starting
points; the remaining slots require licensed, locally relevant data.

## Selected architecture

| Stage | Default candidate | Client target | Server target | Why |
|---|---|---|---|---|
| Crop identifier | MobileNetV3-Small | INT8 ONNX, WASM first, WebGPU optional, target <=6 MB | ONNX Runtime CPU | Compact 2.54M-parameter backbone and low compute; farmer confirmation catches uncertain routing. |
| Disease specialist | MobileNetV3-Small | Lazy INT8 ONNX, target <=6 MB per crop | Same ONNX artifact | Scales by crop without downloading every model. |
| Accuracy benchmark | EfficientNetV2-B0 | Only if measured latency/size passes | ONNX Runtime CPU | Useful comparison for difficult specialists such as tomato, but not the default footprint. |
| Fallback | No model substitution | Send owned upload to server | Approved specialist or expert review | A generic vision LLM or ImageNet model never becomes a disease authority. |

ONNX Runtime documents WASM as the broad browser baseline and WebGPU as an
optional accelerator. Its deployment guide also recommends conditional imports,
correct WASM asset serving, and IndexedDB caching for larger model files. Static
INT8 quantization is the recommended starting point for CNNs, but every
quantized artifact must be re-evaluated for accuracy loss.

## Source assessment

| Source | What it supplies | Crops/use | Integration decision |
|---|---|---|---|
| TorchVision MobileNetV3-Small | ~9.8 MB ImageNet weights, 2.54M parameters | Router/specialist backbone | Fine-tune only; never present ImageNet output as crop disease. |
| TensorFlow Hub MobileNetV3-Small | 224px feature vector | Router/specialist backbone | Fine-tune and export to ONNX; license/release review still required. |
| TensorFlow Hub EfficientNetV2-B0 | 224px feature vector | Accuracy benchmark | Compare on identical field/OOD set and target devices. |
| PlantVillage | 54,306 controlled leaves, 14 species, 38 labels | Maize, soybean, potato, tomato, citrus/orange, grape and others | Warm-start only; controlled backgrounds are not a field test. |
| PlantDoc | 2,598 less-controlled images, 13 species | Auxiliary external-domain checks | Attribution required; too small to certify a release. |
| Rice leaf disease classification collection | Six rice states | Rice training candidate | Verify original-source terms, then train; no ready lightweight release. |
| FoMo4Wheat | 86M+ parameter wheat foundation checkpoints | Wheat benchmark | Too large for this client design and lacks the final compact disease head. |

Public tutorial checkpoints found for cotton, rice, wheat, and mixed crops were
not selected as executable artifacts. Common problems were missing or ambiguous
redistribution terms, tiny/random test splits, no OOD rejection, no India field
holdout, heavy backbones, or a Keras/PyTorch checkpoint not suitable for the
shared browser/server runtime.

## Crop coverage status

Research starting points currently exist for rice, wheat, maize, soybean,
potato, tomato, citrus, and grape. Slots also exist for sorghum, pearl millet,
finger millet, chickpea, pigeon pea, mung bean, black gram, groundnut,
rapeseed/mustard, cotton, jute, sugarcane, onion, chilli, banana, mango, tea,
and coconut. These latter slots intentionally remain `missing` until a source
passes provenance and agronomy review. Bell-pepper images are not treated as a
substitute for chilli.

## Minimum release evidence per model

- Exact ONNX, labels, preprocessing, and manifest SHA-256 values and byte sizes.
- Redistribution approval for weights and every training/evaluation dataset.
- Splits by farm/field and date, not random near-duplicate images.
- Per-class recall, macro-F1, calibration, score/margin acceptance, and unknown
  rejection on independent farmer-phone imagery.
- Challenge images: wrong crops, weeds, soil, hands, blur, exposure failures,
  pests, nutrient/water stress, and unlisted diseases.
- Float-versus-INT8 parity plus browser WASM, WebGPU, and server CPU golden cases.
- Target-device p50/p95 latency, peak memory, download size, and thermal checks.
- Agronomist approval of labels and limitations; results remain screening
  candidates and cannot directly authorize pesticide, fertilizer, or machinery.

## Primary references

- [TorchVision MobileNetV3-Small](https://docs.pytorch.org/vision/main/models/generated/torchvision.models.mobilenet_v3_small.html)
- [TensorFlow Hub transfer learning](https://www.tensorflow.org/tutorials/images/transfer_learning_with_hub)
- [PlantVillage dataset](https://github.com/spMohanty/PlantVillage-Dataset)
- [PlantDoc dataset](https://github.com/pratikkayal/PlantDoc-Dataset)
- [Rice leaf disease dataset collection](https://github.com/ai-agriculture-circuits-and-systems/rice_leaf_disease_classification)
- [FoMo4Wheat](https://github.com/PheniX-Lab/FoMo4Wheat)
- [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/)
- [ONNX Runtime Web deployment](https://onnxruntime.ai/docs/tutorials/web/deploy.html)
- [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
