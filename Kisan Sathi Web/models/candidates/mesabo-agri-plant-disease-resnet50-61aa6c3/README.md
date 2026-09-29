---
license: apache-2.0
tags:
- image-classification
- plant-disease
- agriculture
- resnet50
- computer-vision
- west-africa
datasets:
- plantvillage
pipeline_tag: image-classification
---

# Plant Disease Detection - ResNet50

A pre-trained ResNet50 model for detecting plant diseases from leaf images, optimized for FastAPI deployment.

## Model Description

- **Architecture:** ResNet50
- **Parameters:** 23.6 million
- **Model Size:** 91 MB
- **Accuracy:** 95%+ on PlantVillage test set
- **Classes:** 38 plant disease categories
- **License:** Apache 2.0

## Supported Crops & Diseases (38 Classes)

### Maize (Corn) - 4 diseases ✅
- Cercospora leaf spot (Gray leaf spot)
- Common rust
- Northern Leaf Blight
- Healthy

### Tomato - 10 diseases ✅
- Bacterial spot
- Early blight
- Late blight
- Leaf Mold
- Septoria leaf spot
- Spider mites
- Target Spot
- Yellow Leaf Curl Virus
- Mosaic virus
- Healthy

### Other Supported Crops
- **Apple:** 4 diseases (scab, black rot, cedar rust, healthy)
- **Grape:** 4 diseases (black rot, esca, leaf blight, healthy)
- **Potato:** 3 diseases (early blight, late blight, healthy)
- **Pepper:** 2 classes (bacterial spot, healthy)
- **Cherry, Peach, Strawberry, Orange, etc.**

## Quick Start

```python
from transformers import AutoModelForImageClassification, AutoImageProcessor
from PIL import Image
import torch

# Load model
model = AutoModelForImageClassification.from_pretrained("mesabo/agri-plant-disease-resnet50")
processor = AutoImageProcessor.from_pretrained("mesabo/agri-plant-disease-resnet50")

# Inference
image = Image.open("plant_leaf.jpg").convert("RGB")
inputs = processor(images=image, return_tensors="pt")

with torch.no_grad():
    outputs = model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    predicted_idx = probs.argmax(-1).item()
    confidence = probs[0][predicted_idx].item()

print(f"Disease: {model.config.id2label[predicted_idx]}")
print(f"Confidence: {confidence * 100:.2f}%")
```

## FastAPI Integration

```python
from fastapi import FastAPI, File, UploadFile
from transformers import AutoModelForImageClassification, AutoImageProcessor
from PIL import Image
import torch
import io

app = FastAPI()

# Load model at startup
model = AutoModelForImageClassification.from_pretrained("mesabo/agri-plant-disease-resnet50")
processor = AutoImageProcessor.from_pretrained("mesabo/agri-plant-disease-resnet50")
model.eval()

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    image = Image.open(io.BytesIO(await file.read())).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_idx = probs.argmax(-1).item()
        confidence = probs[0][predicted_idx].item()
    
    return {
        "disease": model.config.id2label[predicted_idx],
        "confidence": round(confidence * 100, 2),
        "status": "success"
    }
```

## Performance

| Metric | Value |
|--------|-------|
| Accuracy | 95%+ |
| Inference Time | < 100ms (CPU) |
| Memory Usage | ~400 MB |
| Input Size | 224x224 RGB |

## West African Agriculture Note

This model currently supports **Maize and Tomato** which are important crops in West Africa. 

**Not yet supported:**
- Cassava (most important staple - coming soon)
- Cashew (major cash crop)
- Cocoa (critical for Ghana, Ivory Coast)

For cassava/cashew support, we recommend fine-tuning on the [CCMT Ghana dataset](https://data.mendeley.com/datasets/bwh3zbpkpv/1).

## Training Data

- **Dataset:** PlantVillage
- **Images:** 54,305
- **Augmentation:** Yes
- **Resolution:** 224x224

## Requirements

```bash
pip install transformers torch pillow
```

## Citation

```bibtex
@misc{agri-plant-disease-resnet50,
  author = {mesabo},
  title = {Plant Disease Detection - ResNet50},
  year = {2024},
  publisher = {Hugging Face},
  url = {https://huggingface.co/mesabo/agri-plant-disease-resnet50}
}
```

## Related Models

- [mesabo/agri-chat-multilingual](https://huggingface.co/mesabo/agri-chat-multilingual) - Multilingual agricultural chatbot (7 languages)

## License

Apache 2.0 - Commercial use allowed
