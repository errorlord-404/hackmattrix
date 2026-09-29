---
language: en
license: apache-2.0
tags:
- image-classification
- keras
- tensorflow
- plant-disease
- efficientnet
datasets:
- PlantVillage
metrics:
- accuracy
library_name: keras
---

# PlantVillage Plant Disease Detection (EfficientNet)

This model is a Keras implementation of EfficientNet trained to classify 38 types of plant diseases from the PlantVillage dataset.

## Model Description
- **Architecture:** EfficientNet (Keras .keras format)
- **Task:** Image Classification (38 classes)
- **Dataset:** PlantVillage (color images)

## Evaluation Results
The model achieves an overall accuracy of **41.68%** on the provided test set.

### Metrics
- **Accuracy:** 41.68%
- **Total Test Images:** 511

## Intended Use
This model is intended for educational and research purposes in the field of agricultural plant pathology. It can be used to identify potential diseases from leaf images.

## Limitations
- Performance may vary significantly across different plant species and disease types.
- The model was trained on the PlantVillage dataset and may not generalize well to images taken in different environmental conditions or on different leaf backgrounds.

## How to Use

```python
import tensorflow as tf
from tensorflow.keras.models import load_model
import numpy as np

# Load model
model = load_model("plant_disease_efficientnet.keras")

# Preprocess image (EfficientNet expectation)
# ... see inference.py for details
```

## Repository
GitHub: [JinWei225/Plant-disease-detection](https://github.com/JinWei225/Plant-disease-detection)
