---
language: en
license: mit
library_name: keras
tags:
- image-classification
- plant-disease-detection
- agriculture
- computer-vision
- cnn
- deep-learning
datasets:
- vipoooool/new-plant-diseases-dataset
metrics:
- accuracy
- precision
- recall
- f1-score
base_model:
- tensorflow
---

# Harimitra - Plant Disease Detection Model

## Model Description

Harimitra is a deep learning model for automated plant disease detection and classification. Built using Convolutional Neural Networks (CNN), this model can identify 38 different plant disease classes from leaf images, helping farmers and agricultural professionals diagnose plant health issues quickly and accurately.

## Model Details

- **Model Type**: Image Classification (CNN)
- **Framework**: Keras/TensorFlow
- **Model Size**: 31.4 MB (.keras format) / 94.2 MB (.h5 format)
- **Input**: RGB plant leaf images (256×256 pixels)
- **Output**: Classification across 38 disease classes
- **Classes**: 38 (various plant species and their diseases/healthy states)

## Dataset

This model was trained on the **New Plant Diseases Dataset** from Kaggle:
- **Source**: [vipoooool/new-plant-diseases-dataset](https://www.kaggle.com/datasets/vipoooool/new-plant-diseases-dataset)
- **Total Images**: 87,900 leaf images
- **Resolution**: 256×256 pixels
- **Classes**: 38 unique classes (combinations of plant species and disease status)
- **Split**:
  - Training: 70,295 images
  - Validation: 17,572 images  
  - Test: 33 images

Each class represents a specific combination of plant type and disease condition (or healthy state). The dataset covers multiple plant species including tomato, potato, corn, grape, apple, and others, with various diseases such as bacterial spot, early blight, late blight, leaf mold, and healthy leaf conditions.

## Intended Use

This model is designed to:
- Identify plant diseases from leaf images across 38 different classes
- Assist farmers in early disease detection and diagnosis
- Support agricultural decision-making and crop management
- Enable automated plant health monitoring systems
- Facilitate precision agriculture applications

## How to Use

### Installation
```bash
pip install -r requirement.txt
```

### Quick Start
```python
from tensorflow import keras
import numpy as np
from PIL import Image

# Load the model
model = keras.models.load_model('trained_model.keras')

# Load and preprocess image
img = Image.open('plant_leaf.jpg')
img = img.resize((256, 256))  # Dataset standard size
img_array = np.array(img) / 255.0  # Normalize to [0, 1]
img_array = np.expand_dims(img_array, axis=0)

# Make prediction
predictions = model.predict(img_array)
predicted_class = np.argmax(predictions, axis=1)

print(f"Predicted class: {predicted_class[0]}")
print(f"Confidence: {np.max(predictions)*100:.2f}%")
```

### Using the Main Script
```bash
python main.py --image path/to/plant_leaf.jpg
```

## Training

The model was trained using the notebooks provided in this repository:
- **Training Pipeline**: `Train_plant_disease.ipynb` - Complete training workflow
- **Testing & Evaluation**: `Test_Plant_Disease.ipynb` - Model evaluation and testing
- **Training Metrics**: Available in `training_hist.json`

### Training Configuration
- Input image size: 256×256×3
- Dataset split: ~80% train, ~20% validation
- Framework: TensorFlow/Keras

## Files in this Repository

| File | Size | Description |
|------|------|-------------|
| `trained_model.keras` | 31.4 MB | Model in Keras format (recommended) |
| `trained_model.h5` | 94.2 MB | Model in H5 format (legacy) |
| `main.py` | 4.53 KB | Main inference script |
| `Train_plant_disease.ipynb` | 552 KB | Training notebook |
| `Test_Plant_Disease.ipynb` | 600 KB | Testing and evaluation notebook |
| `training_hist.json` | 862 B | Training metrics and history |
| `requirement.txt` | 126 B | Required dependencies |
| `home_page.jpeg` | 75.9 KB | Application interface image |

## Performance

Training metrics and performance details are available in `training_hist.json`. The model was evaluated on multiple metrics including:
- Accuracy
- Precision
- Recall
- F1-Score

## Supported Plant Species and Diseases

The model can classify 38 different classes including various combinations of:

**Plant Species**: Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, Tomato

**Disease Types**: Bacterial spot, Early blight, Late blight, Leaf blight, Leaf scorch, Leaf mold, Septoria leaf spot, Spider mites, Target spot, Tomato Yellow Leaf Curl Virus, Tomato mosaic virus, Black rot, Esca, Cedar apple rust, Powdery mildew, and Healthy conditions

## Limitations and Considerations

- Model performance is optimal with 256×256 pixel images
- Best results achieved with clear, well-lit images of plant leaves
- Performance may vary with images taken in different environmental conditions
- Model is trained on controlled dataset images; real-world field conditions may present additional challenges
- Recommended to use as a diagnostic aid rather than sole decision-making tool

## Use Cases

- **Smart Farming**: Integration into precision agriculture systems
- **Mobile Applications**: Disease detection apps for farmers
- **Automated Monitoring**: Greenhouse and crop monitoring systems  
- **Educational Tools**: Training resources for agricultural students
- **Research**: Baseline for plant pathology research

## Citation

If you use this model in your research or application, please cite:
```bibtex
@misc{harimitra2025,
  author = {sudhir75},
  title = {Harimitra: Plant Disease Detection Model},
  year = {2025},
  publisher = {HuggingFace},
  url = {https://huggingface.co/sudhir75/Harimitra}
}

@dataset{new_plant_diseases_dataset,
  author = {vipoooool},
  title = {New Plant Diseases Dataset},
  year = {2020},
  publisher = {Kaggle},
  url = {https://www.kaggle.com/datasets/vipoooool/new-plant-diseases-dataset}
}
```

## License

This model is released under the MIT License.

## Acknowledgments

- Dataset: New Plant Diseases Dataset by vipoooool on Kaggle
- Based on PlantVillage dataset methodology
- Built with TensorFlow/Keras

## Contact & Support

For questions, issues, or contributions:
- Open an issue in this repository
- Check the training notebooks for implementation details
- Review `training_hist.json` for model performance metrics

## Future Improvements

- Expansion to additional plant species and diseases
- Real-time inference optimization
- Mobile deployment (TensorFlow Lite conversion)
- Integration with IoT devices for automated monitoring
- Multi-language support for global agricultural use