import { useRef, useState } from 'react';
import { uploadMedia } from '../../../api/mediaClient.js';
import { MediaStatus } from './MediaStatus.jsx';

export function VoiceButton({ language = 'en-IN', onResult }) {
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const [state, setState] = useState('idle');
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const start = async () => {
    setError(null); setResult(null);
    if (!globalThis.navigator?.mediaDevices?.getUserMedia || !globalThis.MediaRecorder) {
      setState('unsupported');
      setError(new Error('Voice capture is not supported in this browser.')); return;
    }
    try {
      const stream = await globalThis.navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setState('uploading');
        try {
          const response = await uploadMedia('voice', new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' }), { language, idempotencyKey: `voice-${Date.now()}` });
          setResult(response); onResult?.(response); setState(response.status);
        } catch (uploadError) { setError(uploadError); setState('error'); }
      };
      recorderRef.current = recorder; recorder.start(); setState('recording');
    } catch (permissionError) { setState('permission-denied'); setError(new Error('Microphone permission was denied. No transcript was generated.')); }
  };

  return <div className="media-control"><button type="button" onClick={state === 'recording' ? () => recorderRef.current?.stop() : start} disabled={state === 'uploading'} aria-label={state === 'recording' ? 'Stop recording' : 'Start voice note'}>{state === 'recording' ? 'Stop recording' : state === 'uploading' ? 'Uploading…' : 'Record voice note'}</button><span>{state === 'permission-denied' ? 'Permission denied' : state === 'unsupported' ? 'Unsupported browser' : ''}</span><MediaStatus result={result} error={error} onRetry={() => { setError(null); setState('idle'); }} /></div>;
}
