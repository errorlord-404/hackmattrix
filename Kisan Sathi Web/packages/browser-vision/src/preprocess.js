export function preprocessImageData(imageData, specification) {
  const width = specification?.width;
  const height = specification?.height;
  if (!Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0) {
    throw new Error('preprocessing requires positive width and height');
  }
  if (imageData.width !== width || imageData.height !== height) {
    throw new Error('image data must be resized by the browser capture layer before preprocessing');
  }
  const mean = specification.mean || [0, 0, 0];
  const std = specification.std || [1, 1, 1];
  const output = new Float32Array(width * height * 3);
  for (let pixel = 0; pixel < width * height; pixel += 1) {
    for (let channel = 0; channel < 3; channel += 1) {
      output[channel * width * height + pixel] = ((imageData.data[pixel * 4 + channel] / 255) - mean[channel]) / std[channel];
    }
  }
  return output;
}
