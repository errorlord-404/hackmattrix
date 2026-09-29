import { useRef, useState } from 'react';
import { uploadMedia, validateImageFile } from '../../../api/mediaClient.js';
import { MediaStatus } from './MediaStatus.jsx';

export function ImageComposer({ fieldId, crop, onResult }) {
  const inputRef = useRef(null);
  const [state, setState] = useState('empty');
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const choose = async (file) => {
    const validation = validateImageFile(file);
    if (!validation.ok) { setError(new Error(validation.message)); setState('error'); return; }
    if (!fieldId || !crop) { setError(new Error('Select an owned field and confirmed crop before sending an image.')); setState('error'); return; }
    setError(null); setState('uploading');
    try {
      const response = await uploadMedia('image', file, { fieldId, crop, idempotencyKey: `image-${Date.now()}` });
      setResult(response); onResult?.(response); setState(response.status);
    } catch (uploadError) { setError(uploadError); setState('error'); }
  };

  return <section className="media-composer" aria-label="Crop image screening"><input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => choose(event.target.files?.[0])} /><button type="button" onClick={() => inputRef.current?.click()} disabled={state === 'uploading'}>{state === 'uploading' ? 'Sending…' : 'Add field photo'}</button><MediaStatus result={result} error={error} onRetry={() => { setError(null); setResult(null); setState('empty'); }} />{result?.diagnosis === null && <p>Image received. No diagnosis was generated.</p>}</section>;
}
