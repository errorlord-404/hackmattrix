import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { farmStateApi } from '../api/farmStateApi.js';
import { getFarmerId } from '../api/client.js';
import { useFarmData } from './FarmDataContext.jsx';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { createBootstrapPrompt } from './bootstrapPrompt.js';

const AIConversationContext = createContext(null);
const languageCodes = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' };
const recorderMimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus'];
const microphoneFailure = (reason) => {
  switch (reason?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
      return 'Microphone permission is blocked. Allow microphone access for KisanSathi in Windows and then try again.';
    case 'NotFoundError':
      return 'No microphone was found. Connect or enable a microphone and then try again.';
    case 'NotReadableError':
      return 'Another app is using the microphone. Close it and then try KisanSathi again.';
    case 'OverconstrainedError':
      return 'This microphone cannot use the requested recording settings. Choose another microphone and try again.';
    default:
      return `Microphone is unavailable: ${reason?.message || 'Please try again.'}`;
  }
};
const clock = (value = new Date()) => value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const harnessMissing = () => new Error('Open KisanSathi Desktop to use the Codex farm advisor. Manual farm screens remain available in this browser.');
const supportedSpeechLanguages = new Set(Object.values(languageCodes));
const normaliseSpeechLanguage = (value, fallback) => {
  const raw = String(value || '').trim().toLowerCase().replace('_', '-');
  const mapped = raw === 'en' || raw === 'en-in' ? 'en-IN' : raw === 'hi' || raw === 'hi-in' ? 'hi-IN' : raw === 'mr' || raw === 'mr-in' ? 'mr-IN' : null;
  return mapped && supportedSpeechLanguages.has(mapped) ? mapped : fallback;
};
const uiActionRoutes = Object.freeze({
  open_field_editor: '/fields?add=1',
  // Opens a local field wizard; it never reads GPS until the farmer approves it.
  open_field_marker: '/fields?add=1&guided=1',
  review_field_boundary: '/fields?review=1',
  open_farm_map: '/map',
  open_soil_health: '/soil',
  open_weather: '/weather',
  open_irrigation: '/irrigation',
  open_field_tasks: '/tasks',
  open_crop_health: '/pest',
  open_market_prices: '/market',
  open_government_schemes: '/schemes',
  open_farm_finance: '/finance',
  open_machinery: '/machinery',
  open_marketplace: '/marketplace',
  open_reports: '/reports',
  open_settings: '/settings',
  open_device_setup: '/device-setup',
});
const extractUiAction = (value) => {
  const raw = String(value || '');
  let action = null;
  const text = raw.replace(/\[KISANSATHI_UI:([a-z_]+)\]/gi, (token, requestedAction) => {
    const normalized = requestedAction.toLowerCase();
    if (!action && uiActionRoutes[normalized]) { action = normalized; return ''; }
    return token;
  }).replace(/\n{3,}/g, '\n\n').trim();
  return {
    action,
    text,
  };
};
const plainText = (value) => String(value || '')
  .replace(/```[\s\S]*?```/g, ' ')
  .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
  .replace(/[*_`#>]/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();
const englishFarmerSummary = (answer) => {
  const plain = plainText(answer);
  const match = plain.match(/(?:farmer\s+summary|summary\s+for\s+farmer)\s*:\s*([\s\S]*)/i);
  const candidate = match?.[1]?.trim() || plain;
  if (candidate.length <= 560) return candidate;
  const sentences = candidate.match(/[^.!?]+[.!?]+/g) || [];
  const compact = sentences.reduce((result, sentence) => result.length + sentence.length <= 560 ? `${result}${sentence}` : result, '');
  return compact.trim() || `${candidate.slice(0, 557).trimEnd()}…`;
};

export function AIConversationProvider({ children }) {
  const { language } = useLanguage();
  const { fields, loading: farmLoading, error: farmError, refresh } = useFarmData();
  const [selectedFieldId, setSelectedFieldId] = useState('');
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [toolEvents, setToolEvents] = useState([]);
  const [voiceState, setVoiceState] = useState('idle');
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [harnessStatus, setHarnessStatus] = useState(() => window.kisanHarness ? 'checking' : 'browser');
  const [harnessDetails, setHarnessDetails] = useState(null);
  const [onboarding, setOnboarding] = useState(null);
  const [onboardingError, setOnboardingError] = useState(null);
  const [autoPlay, setAutoPlayState] = useState(() => localStorage.getItem('kisansathi-auto-play') !== 'false');
  const [conversationLanguage, setConversationLanguageState] = useState(() => normaliseSpeechLanguage(localStorage.getItem('kisansathi-conversation-language'), languageCodes[language] || languageCodes.en));
  const [uiAction, setUiAction] = useState(null);
  const [advisorQueueRevision, setAdvisorQueueRevision] = useState(0);
  const recorder = useRef(null);
  const stream = useRef(null);
  const voiceCancelled = useRef(false);
  const voiceAudio = useRef(null);
  const messageCounter = useRef(0);
  const languageRef = useRef(language);
  const conversationLanguageRef = useRef(conversationLanguage);
  const selectedFieldRef = useRef('');
  const autoPlayRef = useRef(autoPlay);
  const assistantDrafts = useRef(new Map());
  const turnInFlight = useRef(false);
  const advisorReviewQueue = useRef([]);
  const imageObjectUrls = useRef(new Set());
  const activeFieldId = selectedFieldId || fields[0]?.id || '';
  const selectedField = fields.find((field) => field.id === activeFieldId) || fields[0] || null;

  useEffect(() => { languageRef.current = language; selectedFieldRef.current = activeFieldId; }, [activeFieldId, language]);
  useEffect(() => { conversationLanguageRef.current = conversationLanguage; }, [conversationLanguage]);
  useEffect(() => { autoPlayRef.current = autoPlay; }, [autoPlay]);

  const addMessage = useCallback((message) => setMessages((current) => [...current, message]), []);
  const updateMessage = useCallback((id, changes) => setMessages((current) => current.map((message) => message.id === id ? { ...message, ...changes } : message)), []);
  const revokeImageObjectUrls = useCallback(() => {
    imageObjectUrls.current.forEach((url) => URL.revokeObjectURL?.(url));
    imageObjectUrls.current.clear();
  }, []);
  const setAutoPlay = useCallback((value) => { setAutoPlayState(value); localStorage.setItem('kisansathi-auto-play', String(value)); }, []);
  const setConversationLanguage = useCallback((value) => {
    const next = normaliseSpeechLanguage(value, languageCodes[languageRef.current] || languageCodes.en);
    setConversationLanguageState(next);
    localStorage.setItem('kisansathi-conversation-language', next);
    return next;
  }, []);
  const refreshOnboardingStatus = useCallback(async () => {
    try {
      const status = await farmStateApi.getOnboardingStatus();
      setOnboarding(status);
      setOnboardingError(null);
      return status;
    } catch (reason) {
      setOnboardingError(reason);
      return null;
    }
  }, []);

  useEffect(() => {
    if (farmLoading !== false || farmError) return undefined;
    const timer = window.setTimeout(() => { refreshOnboardingStatus(); }, 0);
    return () => window.clearTimeout(timer);
  }, [farmError, farmLoading, refreshOnboardingStatus]);

  const speakMessage = useCallback(async (message) => {
    try {
      const bridge = window.kisanHarness;
      const text = message?.speechText || message?.localizedSummary || message?.text;
      if (!bridge || !text) throw harnessMissing();
      const response = await bridge.voice.synthesize({ text, language_code: normaliseSpeechLanguage(message.languageCode, conversationLanguageRef.current) });
      if (response.status !== 'completed' || !response.audio_base64) throw new Error(response.message || 'Sarvam speech output is unavailable.');
      voiceAudio.current?.pause();
      voiceAudio.current = new Audio(`data:${response.audio_mime_type || 'audio/wav'};base64,${response.audio_base64}`);
      await voiceAudio.current.play();
      return true;
    } catch (reason) {
      setError(reason);
      throw reason;
    }
  }, []);

  const localizeAndSpeak = useCallback(async (id, english, responseLanguage = conversationLanguageRef.current) => {
    const bridge = window.kisanHarness;
    if (!bridge) throw harnessMissing();
    const target = normaliseSpeechLanguage(responseLanguage, conversationLanguageRef.current);
    const summary = englishFarmerSummary(english);
    let localized = summary;
    if (target !== languageCodes.en) {
      const translated = await bridge.voice.translate({ input: summary, source_language_code: languageCodes.en, target_language_code: target });
      if (translated.status === 'completed' && translated.translated_text) localized = translated.translated_text;
    }
    updateMessage(id, {
      text: english,
      englishText: english,
      englishSummary: summary,
      localizedSummary: localized,
      translating: false,
      languageCode: target,
      speechText: localized,
    });
    if (autoPlayRef.current) {
      try { await speakMessage({ speechText: localized, languageCode: target }); }
      catch (reason) { setError(reason); }
    }
  }, [speakMessage, updateMessage]);

  const refreshHarnessStatus = useCallback(async () => {
    if (!window.kisanHarness) { setHarnessStatus('browser'); return null; }
    try {
      const details = await window.kisanHarness.session.status();
      setHarnessDetails(details);
      setHarnessStatus(details.codex?.running ? 'ready' : 'starting');
      return details;
    } catch (reason) {
      setHarnessStatus('unavailable');
      setError(reason);
      return null;
    }
  }, []);

  useEffect(() => {
    const bridge = window.kisanHarness;
    if (!bridge) return undefined;
    let active = true;
    const statusTimer = window.setTimeout(() => { refreshHarnessStatus(); }, 0);
    const unsubscribe = bridge.onEvent((event) => {
      if (!active) return;
      if (event.kind === 'ready') {
        setSession({ id: event.threadId });
        localStorage.setItem('kisansathi-codex-thread-id', event.threadId);
        setHarnessStatus('ready');
        setHarnessDetails((current) => ({ ...(current || {}), codex: { ...(current?.codex || {}), running: true, threadId: event.threadId } }));
      }
      if (event.kind === 'unavailable') {
        setSession(null);
        setHarnessStatus('unavailable');
        setHarnessDetails((current) => ({ ...(current || {}), codex: { ...(current?.codex || {}), running: false, lastError: event.message } }));
        setProcessing(false);
        turnInFlight.current = false;
        setError(new Error(event.message));
      }
      if (event.kind === 'agentMessageDelta') {
        const id = `codex-${event.itemId}`;
        const draft = `${assistantDrafts.current.get(id) || ''}${event.delta}`;
        assistantDrafts.current.set(id, draft);
        setMessages((current) => current.some((message) => message.id === id)
          ? current.map((message) => message.id === id ? { ...message, text: draft } : message)
          : [...current, { id, role: 'assistant', text: draft, time: clock(), streaming: true, provider: 'codex' }]);
      }
      if (event.kind === 'agentMessageCompleted') {
        const id = `codex-${event.itemId}`;
        const completed = extractUiAction(event.text || assistantDrafts.current.get(id) || '');
        const english = completed.text;
        assistantDrafts.current.delete(id);
        setMessages((current) => current.some((message) => message.id === id)
          ? current.map((message) => message.id === id ? { ...message, text: english, streaming: false, translating: true, provider: 'codex' } : message)
          : [...current, { id, role: 'assistant', text: english, englishText: english, time: clock(), translating: true, provider: 'codex' }]);
        if (completed.action) setUiAction({ id, action: completed.action, path: uiActionRoutes[completed.action] });
        localizeAndSpeak(id, english, conversationLanguageRef.current).catch((reason) => { updateMessage(id, { translating: false }); setError(reason); });
      }
      if (event.kind === 'tool') {
        setToolEvents((current) => [...current.slice(-7), { id: `${event.tool}-${Date.now()}`, ...event }]);
        if (event.status === 'completed' && event.readOnly === false) { refresh(); refreshOnboardingStatus(); }
      }
      if (event.kind === 'approval' || event.kind === 'clarification') setPendingAction(event);
      if (event.kind === 'turnCompleted') { setProcessing(false); turnInFlight.current = false; }
    });
    return () => { active = false; window.clearTimeout(statusTimer); unsubscribe(); };
  }, [localizeAndSpeak, refresh, refreshHarnessStatus, refreshOnboardingStatus, updateMessage]);

  const ensureSession = useCallback(async () => {
    const bridge = window.kisanHarness;
    if (!bridge) throw harnessMissing();
    if (session) return session;
    setHarnessStatus('starting');
    const savedThreadId = localStorage.getItem('kisansathi-codex-thread-id');
    let next;
    if (savedThreadId) {
      try { next = await bridge.session.resume(savedThreadId); }
      catch { localStorage.removeItem('kisansathi-codex-thread-id'); }
    }
    if (!next) next = await bridge.session.start({ fieldId: selectedFieldRef.current, language: languageRef.current });
    const value = { id: next.threadId };
    localStorage.setItem('kisansathi-codex-thread-id', next.threadId);
    setSession(value);
    setHarnessStatus('ready');
    return value;
  }, [session]);

  const restartConversation = useCallback(async () => {
    const bridge = window.kisanHarness;
    if (!bridge || processing || turnInFlight.current) return false;
    setProcessing(true);
    setError(null);
    setPendingAction(null);
    setMessages([]);
    revokeImageObjectUrls();
    setToolEvents([]);
    assistantDrafts.current.clear();
    localStorage.removeItem('kisansathi-codex-thread-id');
    const marker = `kisansathi-startup-check-${getFarmerId()}`;
    sessionStorage.removeItem(marker);
    try {
      const next = await bridge.session.restart({ fieldId: selectedFieldRef.current, language: languageRef.current });
      const value = { id: next.threadId };
      setSession(value);
      setHarnessStatus('ready');
      localStorage.setItem('kisansathi-codex-thread-id', next.threadId);
      const onboardingStatus = await refreshOnboardingStatus();
      turnInFlight.current = true;
      await bridge.chat.sendText(createBootstrapPrompt(onboardingStatus), {
        field_id: 'none', farmer_language: languageCodes[languageRef.current] || languageCodes.en,
        input_via: 'startup_check',
      });
      sessionStorage.setItem(marker, 'sent');
      return true;
    } catch (reason) {
      turnInFlight.current = false;
      setHarnessStatus('unavailable');
      setError(reason);
      return false;
    } finally {
      if (!turnInFlight.current) setProcessing(false);
    }
  }, [processing, refreshOnboardingStatus, revokeImageObjectUrls]);

  useEffect(() => {
    if (!window.kisanHarness || farmLoading !== false || farmError) return;
    const marker = `kisansathi-startup-check-${getFarmerId()}`;
    if (sessionStorage.getItem(marker) || turnInFlight.current) return;
    sessionStorage.setItem(marker, 'starting');
    turnInFlight.current = true;
    setProcessing(true);
    setError(null);
    Promise.all([ensureSession(), refreshOnboardingStatus()]).then(([, status]) => window.kisanHarness.chat.sendText(createBootstrapPrompt(status), {
      field_id: 'none', farmer_language: languageCodes[languageRef.current] || languageCodes.en,
      input_via: 'startup_check',
    })).then(() => sessionStorage.setItem(marker, 'sent')).catch((reason) => {
      sessionStorage.removeItem(marker);
      turnInFlight.current = false;
      setProcessing(false);
      setError(reason);
    });
  }, [ensureSession, farmError, farmLoading, refreshOnboardingStatus]);

  const sendText = useCallback(async (text, options = {}) => {
    const content = text.trim();
    if (!content || processing || turnInFlight.current) return false;
    turnInFlight.current = true;
    const id = `local-${messageCounter.current++}`;
    addMessage({ id, role: 'user', text: content, originalText: content, time: clock(), via: options.via });
    setProcessing(true);
    setError(null);
    try {
      await ensureSession();
      const source = normaliseSpeechLanguage(options.languageCode, languageCodes[languageRef.current] || languageCodes.en);
      if (!options.languageCode) setConversationLanguage(source);
      let english = content;
      if (source !== languageCodes.en) {
        const translated = await window.kisanHarness.voice.translate({ input: content, source_language_code: source, target_language_code: languageCodes.en });
        if (translated.status !== 'completed' || !translated.translated_text) throw new Error(translated.message || 'Sarvam could not translate this message.');
        english = translated.translated_text;
      }
      updateMessage(id, { text: english, englishText: english, originalText: content });
      await window.kisanHarness.chat.sendText(english, { field_id: options.fieldId || selectedFieldRef.current || 'none', farmer_language: source, input_via: options.via || 'typed' });
      return true;
    } catch (reason) { turnInFlight.current = false; setProcessing(false); setError(reason); return false; }
  }, [addMessage, ensureSession, processing, setConversationLanguage, updateMessage]);

  // Manual screens can use this one gateway for connected, contextual advice.
  // It deliberately queues rather than dropping an action while the advisor is
  // answering another request. Offline mode never creates an agent request.
  const requestAdvisorReview = useCallback((request) => {
    if (!navigator.onLine) return { queued: false, reason: 'offline' };
    if (!window.kisanHarness) return { queued: false, reason: 'advisor_unavailable' };
    const prompt = String(request?.prompt || '').trim();
    if (!prompt) return { queued: false, reason: 'missing_prompt' };
    advisorReviewQueue.current.push({
      prompt,
      fieldId: request.fieldId || selectedFieldRef.current || 'none',
      workflow: String(request.workflow || 'manual-screen').replace(/[^a-z0-9_-]/gi, '-').slice(0, 60),
    });
    setAdvisorQueueRevision((revision) => revision + 1);
    return { queued: true };
  }, []);

  useEffect(() => {
    if (processing || turnInFlight.current || !advisorReviewQueue.current.length) return;
    const next = advisorReviewQueue.current.shift();
    sendText(next.prompt, { via: `ui-${next.workflow}`, fieldId: next.fieldId });
  }, [advisorQueueRevision, processing, sendText]);

  const finishVoice = useCallback(async (blob) => {
    setVoiceState('processing');
    setError(null);
    try {
      if (!window.kisanHarness) throw harnessMissing();
      if (!blob.size) throw new Error('No audio was recorded. Please try the microphone again.');
      const result = await window.kisanHarness.voice.transcribe(await blob.arrayBuffer(), 'unknown', blob.type || 'audio/webm');
      if (result.status !== 'completed' || !result.transcript) throw new Error(result.message || 'Sarvam could not detect speech.');
      const detectedLanguage = setConversationLanguage(result.language_code);
      if (await sendText(result.transcript, { via: 'voice', languageCode: detectedLanguage })) setVoiceState('responding');
      else setVoiceState('idle');
    } catch (reason) { setError(reason); setVoiceState('idle'); }
    finally { window.setTimeout(() => setVoiceState('idle'), 700); }
  }, [sendText, setConversationLanguage]);

  const startVoice = useCallback(async () => {
    if (voiceState !== 'idle' || processing) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { setError(new Error('Audio recording is not supported by this browser.')); return; }
    try {
      voiceCancelled.current = false;
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      const supportedMimeType = recorderMimeTypes.find((mimeType) => MediaRecorder.isTypeSupported?.(mimeType));
      const nextRecorder = supportedMimeType ? new MediaRecorder(stream.current, { mimeType: supportedMimeType }) : new MediaRecorder(stream.current);
      const chunks = [];
      nextRecorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      nextRecorder.onerror = (event) => {
        voiceCancelled.current = true;
        stream.current?.getTracks().forEach((track) => track.stop());
        stream.current = null;
        recorder.current = null;
        setVoiceState('idle');
        setError(new Error(`Microphone recording failed: ${event.error?.message || 'Please try again.'}`));
      };
      nextRecorder.onstop = () => {
        stream.current?.getTracks().forEach((track) => track.stop());
        stream.current = null;
        recorder.current = null;
        if (!voiceCancelled.current) finishVoice(new Blob(chunks, { type: nextRecorder.mimeType || supportedMimeType || 'audio/webm' }));
        else setVoiceState('idle');
      };
      recorder.current = nextRecorder;
      nextRecorder.start();
      setVoiceState('listening');
    } catch (reason) {
      stream.current?.getTracks().forEach((track) => track.stop());
      stream.current = null;
      recorder.current = null;
      setVoiceState('idle');
      setError(new Error(microphoneFailure(reason)));
    }
  }, [finishVoice, processing, voiceState]);

  const stopVoice = useCallback(() => {
    if (voiceState !== 'listening' || !recorder.current) return;
    setVoiceState('processing');
    if (recorder.current.state !== 'inactive') recorder.current.stop();
    else { setVoiceState('idle'); setError(new Error('The microphone stopped before audio was captured. Please try again.')); }
  }, [voiceState]);
  const cancelVoice = useCallback(() => { voiceCancelled.current = true; recorder.current?.stop(); stream.current?.getTracks().forEach((track) => track.stop()); recorder.current = null; stream.current = null; setVoiceState('idle'); }, []);
  const resolveConfirmation = useCallback(async (decision) => {
    if (!pendingAction || !window.kisanHarness) return;
    const result = pendingAction.kind === 'clarification' ? { answers: decision.answers || {} } : { decision: decision.value || 'decline' };
    await (pendingAction.kind === 'clarification' ? window.kisanHarness.clarification.respond(pendingAction.requestId, result) : window.kisanHarness.approval.respond(pendingAction.requestId, result));
    setPendingAction(null);
  }, [pendingAction]);
  const consumeUiAction = useCallback((id) => setUiAction((current) => current?.id === id ? null : current), []);

  const submitImage = useCallback(async (file) => {
    if (!file || turnInFlight.current) return false;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || !file.size || file.size > 8 * 1024 * 1024) {
      setError(new Error('Choose a JPEG, PNG, or WebP crop photo smaller than 8 MB.'));
      return false;
    }
    turnInFlight.current = true;
    const image = URL.createObjectURL(file);
    imageObjectUrls.current.add(image);
    addMessage({ id: `image-${Date.now()}`, role: 'user', text: 'I uploaded a crop photo for inspection.', time: clock(), image });
    setProcessing(true);
    setError(null);
    try {
      const confirmedCrop = selectedField?.current_crop?.trim() || undefined;
      const staged = await farmStateApi.stageCropImage(file, activeFieldId);
      const approved = window.confirm('Send this crop photo to our crop-health service for screening? The image is sent for analysis; sensor readings stay inside KisanSathi.');
      const consent = await farmStateApi.createCropHealthConsent(staged.upload_id, approved ? 'approved' : 'declined');
      if (!approved) {
        addMessage({ id: `image-declined-${staged.upload_id}`, role: 'assistant', text: 'Photo saved privately. I will not send it to the crop-health service. You can approve screening later or describe the symptoms in chat.', time: clock(), warning: 'External crop-health processing was declined.' });
        turnInFlight.current = false;
        setProcessing(false);
        return true;
      }
      const result = await farmStateApi.createDiagnosisFromUpload(staged.upload_id, consent.consent_receipt_id, confirmedCrop);
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(result?.id || '')) {
        throw new Error('The photo service did not return a usable evidence record ID. Please retry or ask for help.');
      }
      const providerStatus = ['completed', 'provider_unavailable', 'needs_crop_confirmation', 'needs_expert_review', 'unsupported_crop']
        .includes(result.status) ? result.status : 'inconclusive';
      if (window.kisanHarness) {
        await ensureSession();
        try {
          await window.kisanHarness.chat.sendText(
            `The farmer approved crop.health screening for a saved crop photo. The farmer-scoped diagnosis evidence record is ${result.id}, with provider status ${providerStatus}. Do not request or inspect image bytes in this turn. Call get_diagnosis for that exact record, reconcile its immutable sensor context with the visual candidates, and explain that screening output is not a confirmed diagnosis. Confirm crop/field when uncertain and do not prescribe chemicals or doses.`,
            { field_id: selectedFieldRef.current || 'none', input_via: 'crop-health-record' });
        } catch (reason) {
          if (!/image|vision|localImage|unsupported/i.test(reason.message || '')) throw reason;
          addMessage({ id: `diagnosis-${result.id}`, role: 'assistant', text: result.status === 'completed' && result.label
            ? `Photo saved. The model suggested ${result.label}, but this is not a confirmed diagnosis. Please confirm the crop and describe any symptoms.`
            : 'Photo saved, but image inspection is unavailable. Please confirm the crop and describe any symptoms.',
          time: clock(), provider: result.provider, via: 'diagnosis', warning: 'Codex image inspection was unavailable; the photo remains in the farm diagnosis record.' });
          turnInFlight.current = false;
          setProcessing(false);
          return true;
        }
      } else {
        const detail = result.status === 'completed' && result.label
          ? `Photo saved. The model suggested ${result.label}, but this is not a confirmed diagnosis. Please confirm the crop and describe any symptoms.`
          : 'Photo saved. Automated diagnosis is unavailable or inconclusive; please confirm the crop and describe any symptoms.';
        addMessage({ id: `diagnosis-${result.id}`, role: 'assistant', text: detail, time: clock(), provider: result.provider, via: 'diagnosis' });
        turnInFlight.current = false;
        setProcessing(false);
        return true;
      }
    } catch (reason) {
      turnInFlight.current = false; setProcessing(false); setError(reason);
      return false;
    }
    return true;
  }, [activeFieldId, addMessage, ensureSession, selectedField]);

  useEffect(() => () => { voiceCancelled.current = true; voiceAudio.current?.pause(); recorder.current?.stop(); stream.current?.getTracks().forEach((track) => track.stop()); revokeImageObjectUrls(); }, [revokeImageObjectUrls]);

  const value = {
    messages, toolEvents, voiceState, processing, error, session, harnessStatus, harnessDetails, onboarding, onboardingError, autoPlay,
    selectedField, fields, localizedFields: fields, selectedFieldId: activeFieldId, setSelectedFieldId, conversationLanguage, uiAction, consumeUiAction, restartConversation,
    sendText, requestAdvisorReview, startVoice, stopVoice, cancelVoice, submitImage, pendingAction, resolveConfirmation, speakMessage,
    setAutoPlay, refreshHarnessStatus, refreshOnboardingStatus, language,
  };
  return <AIConversationContext.Provider value={value}>{children}</AIConversationContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAIConversation() { const context = useContext(AIConversationContext); if (!context) throw new Error('useAIConversation must be used inside AIConversationProvider'); return context; }
