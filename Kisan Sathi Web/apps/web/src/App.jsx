import { useEffect, useRef, useState } from 'react';
import {
  ArrowUpRight,
  CalendarDays,
  Check,
  ChevronDown,
  CircleAlert,
  CloudSun,
  ImagePlus,
  Leaf,
  MapPin,
  Menu,
  MessageCircle,
  Paperclip,
  RefreshCw,
  Send,
  Sprout,
  ThermometerSun,
  Upload,
  X,
} from 'lucide-react';
import { api, ApiError, createTurnId, getSessionId } from './lib/api.js';
import { predictCropDisease } from './api/cropDiseaseClient.js';

const starterMessages = [
  {
    id: 'welcome',
    role: 'assistant',
    content: 'Good morning. I can help you read the signals from your field, one observation at a time.',
    note: 'Advisor workspace ready · no field reading has been inferred',
  },
];

const prompts = [
  'What should I look at after this week’s rain?',
  'Help me make a plan for my tomato plot',
  'How do I compare today’s mandi prices?',
];

function stateLabel(state) {
  return { checking: 'Checking', connected: 'Connected', unavailable: 'Unavailable', degraded: 'Degraded' }[state] || 'Unavailable';
}

function StatusDot({ state }) {
  return <span className={`status-dot status-dot--${state}`} aria-hidden="true" />;
}

function ProviderRow({ label, detail, state, icon: Icon }) {
  return (
    <div className="provider-row">
      <div className="provider-icon"><Icon size={16} strokeWidth={1.8} /></div>
      <div className="provider-copy">
        <span>{label}</span>
        <small>{detail}</small>
      </div>
      <div className="provider-state"><StatusDot state={state} /> <span>{stateLabel(state)}</span></div>
    </div>
  );
}

function FieldSketch() {
  return (
    <div className="field-sketch" aria-label="Illustrated map of the selected North plot">
      <div className="sketch-compass">N</div>
      <div className="sketch-road" />
      <div className="sketch-plot sketch-plot--one"><span>01</span></div>
      <div className="sketch-plot sketch-plot--two"><span>02</span></div>
      <div className="sketch-plot sketch-plot--three"><span>03</span></div>
      <div className="sketch-pin"><MapPin size={14} fill="currentColor" /></div>
      <span className="sketch-label">North plot</span>
      <span className="sketch-scale">100 m</span>
    </div>
  );
}

function Message({ message }) {
  const isAssistant = message.role === 'assistant';
  return (
    <article className={`message message--${message.role}`}>
      <div className="message-avatar" aria-hidden="true">{isAssistant ? <Sprout size={17} /> : 'AS'}</div>
      <div className="message-body">
        <div className="message-meta"><strong>{isAssistant ? 'Sathi' : 'You'}</strong><span>{message.time || (isAssistant ? 'just now' : 'just sent')}</span></div>
        <p>{message.content}</p>
        {message.note && <span className="message-note"><Check size={12} /> {message.note}</span>}
      </div>
    </article>
  );
}

function CropScreening({ onRetry, capabilities }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [state, setState] = useState('empty');
  const [error, setError] = useState('');
  const [crop, setCrop] = useState('tomato');
  const [result, setResult] = useState(null);

  const chooseFile = async (nextFile) => {
    if (!nextFile) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(nextFile.type)) {
      setError('Please choose a JPEG, PNG, or WebP image.');
      return;
    }
    if (nextFile.size > 8 * 1024 * 1024) {
      setError('That image is larger than 8 MB. Choose a smaller field photo.');
      return;
    }
    setError('');
    setResult(null);
    setFile(nextFile);
    setState('screening');
    try {
      const response = await predictCropDisease(nextFile, { crop });
      setResult(response);
      setState('result');
    } catch (screeningError) {
      setError(screeningError.message || 'The prototype model could not process this image.');
      setState('error');
    }
  };

  const reset = () => {
    setFile(null); setError(''); setResult(null); setState('empty');
    onRetry?.();
  };

  return (
    <section className="screening-card" aria-labelledby="screening-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Field check · optional</span>
          <h2 id="screening-title">Crop health, at a glance</h2>
        </div>
        <ImagePlus size={21} strokeWidth={1.6} aria-hidden="true" />
      </div>
      <p className="section-intro">Add a clear leaf photo for a bounded prototype screening response. It is a signal to discuss—not a diagnosis or treatment instruction.</p>
      <label className="screening-crop-picker" htmlFor="screening-crop">Prototype crop</label>
      <select id="screening-crop" value={crop} onChange={(event) => setCrop(event.target.value)} disabled={state === 'screening'}>
        {(capabilities?.supported_crops || [{ id: 'tomato', name: 'Tomato' }]).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select>
      {state === 'empty' && (
        <button className="upload-zone" type="button" onClick={() => inputRef.current?.click()}>
          <span className="upload-mark"><Upload size={17} /></span>
          <span><strong>Drop a field photo here</strong><small>or browse · JPEG, PNG, WebP · max 8 MB</small></span>
          <ArrowUpRight size={17} className="upload-arrow" />
        </button>
      )}
      {state !== 'empty' && (
        <div className="selected-file">
          <div className="file-thumb"><Leaf size={19} /></div>
          <div><strong>{file?.name}</strong><small>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB · ready to send` : 'No file selected'}</small></div>
          <button className="icon-button" type="button" onClick={reset} aria-label="Remove selected photo"><X size={16} /></button>
        </div>
      )}
      <input ref={inputRef} className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseFile(event.target.files?.[0])} />
      {state === 'screening' && <div className="degraded-box"><ThermometerSun size={16} /><span><strong>Running the prototype model…</strong> The server is screening this image with the selected research checkpoint.</span></div>}
      {state === 'result' && result && <div className="degraded-box" role="status"><ThermometerSun size={16} /><span><strong>{result.status === 'uncertain' ? 'Uncertain screening signal.' : result.prediction?.disease_name || 'Screening completed.'}</strong>{result.prediction ? ` ${(result.prediction.confidence * 100).toFixed(1)}% confidence.` : ' No prediction was generated.'} <small>{result.warnings?.[0]}</small></span></div>}
      {state === 'error' && <div className="degraded-box" role="alert"><ThermometerSun size={16} /><span><strong>Prototype screening failed.</strong> {error}</span></div>}
      {error && <p className="error-copy" role="alert">{error}</p>}
    </section>
  );
}

export default function App() {
  const [messages, setMessages] = useState(starterMessages);
  const [draft, setDraft] = useState('');
  const [sessionId] = useState(() => getSessionId());
  const [sendState, setSendState] = useState('idle');
  const [networkState, setNetworkState] = useState('checking');
  const [providerState, setProviderState] = useState('checking');
  const [toolState, setToolState] = useState('checking');
  const [visionState, setVisionState] = useState('checking');
  const [visionCapabilities, setVisionCapabilities] = useState(null);
  const [prototypeCapabilities, setPrototypeCapabilities] = useState(null);
  const [statusMessage, setStatusMessage] = useState('Checking the HTTP services…');
  const [menuOpen, setMenuOpen] = useState(false);
  const endOfMessages = useRef(null);

  const checkStatus = async () => {
    setNetworkState('checking'); setProviderState('checking'); setToolState('checking'); setVisionState('checking'); setStatusMessage('Checking the standalone API…');
    const [health, readiness, tools, vision, prototype] = await Promise.allSettled([api.healthz(), api.readyz(), api.tools(), api.visionCapabilities(), api.cropDiseasePrototype()]);
    const healthOk = health.status === 'fulfilled';
    const readyOk = readiness.status === 'fulfilled';
    const providerOk = healthOk && health.value?.provider === 'configured';
    setNetworkState(healthOk ? 'connected' : 'unavailable');
    setProviderState(providerOk ? 'connected' : healthOk ? 'degraded' : 'unavailable');
    setToolState(tools.status === 'fulfilled' ? 'connected' : readyOk ? 'connected' : healthOk ? 'degraded' : 'unavailable');
    const capabilities = vision.status === 'fulfilled' ? vision.value : null;
    const prototypeProfile = prototype.status === 'fulfilled' ? prototype.value : null;
    setPrototypeCapabilities(prototypeProfile);
    setVisionCapabilities(capabilities);
    setVisionState(prototypeProfile?.status === 'prototype_available' ? 'connected' : prototypeProfile ? 'degraded' : 'unavailable');
    setStatusMessage(healthOk ? (providerOk && readyOk ? 'Standalone API is ready.' : providerOk ? 'API is live; readiness is degraded.' : 'API is live; the language provider is unavailable.') : 'The API is unavailable. You can still prepare a field note offline.');
  };

  useEffect(() => { checkStatus(); }, []);
  useEffect(() => { endOfMessages.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [messages, sendState]);

  const send = async (event) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendState === 'sending') return;
    setDraft('');
    setMessages((current) => [...current, { id: `user-${Date.now()}`, role: 'user', content }]);
    setSendState('sending');
    const turnId = createTurnId();
    const assistantId = `assistant-${turnId}`;
    let streamStatus = 'ok';
    let receivedAssistantEvent = false;
    const conversation = [...messages.filter((message) => message.id !== 'welcome'), { role: 'user', content }];
    try {
      await api.streamChat({ sessionId, turnId, messages: conversation, onEvent: (eventPayload) => {
        const payload = eventPayload?.payload || {};
        if (eventPayload?.kind === 'agentMessageDelta') {
          receivedAssistantEvent = true;
          setMessages((current) => {
            const existing = current.find((message) => message.id === assistantId);
            const nextContent = `${existing?.content || ''}${payload.text || ''}`;
            return existing ? current.map((message) => message.id === assistantId ? { ...message, content: nextContent } : message) : [...current, { id: assistantId, role: 'assistant', content: nextContent, note: 'HTTP/NDJSON response' }];
          });
        }
        if (eventPayload?.kind === 'agentMessageCompleted') {
          receivedAssistantEvent = true;
          setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: payload.text || message.content, note: 'Advisor response · review before acting' } : message));
        }
        if (eventPayload?.kind === 'unavailable') {
          receivedAssistantEvent = true;
          streamStatus = 'degraded';
          const message = payload.message || 'The configured language provider is unavailable.';
          setMessages((current) => [...current, { id: assistantId, role: 'assistant', content: message, note: 'Provider unavailable · no recommendation generated' }]);
        }
        if (eventPayload?.kind === 'diagnostic' || (eventPayload?.kind === 'turnCompleted' && payload.status === 'degraded')) streamStatus = 'degraded';
      } });
      if (streamStatus === 'degraded' && !receivedAssistantEvent) setMessages((current) => [...current, { id: assistantId, role: 'assistant', content: 'The advisor stream is degraded. No recommendation was generated.', note: 'Standalone API diagnostic' }]);
      setSendState(streamStatus === 'degraded' ? 'degraded' : 'idle');
    } catch (error) {
      setSendState('degraded');
      setMessages((current) => [...current, { id: assistantId, role: 'assistant', content: error instanceof ApiError ? error.message : 'The advisor is unavailable right now.', note: 'No recommendation was generated' }]);
    }
  };

  return (
    <div className="app-shell">
      <div className="grain" aria-hidden="true" />
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Kisan Sathi home"><span className="brand-mark"><Sprout size={19} /></span><span>Kisan <em>Sathi</em></span></a>
        <div className="topbar-meta"><span className="date-note"><CalendarDays size={15} /> 17 September 2026</span><span className="topbar-rule" /><span className="connection-pill"><StatusDot state={networkState} /> {stateLabel(networkState)}</span></div>
        <button className="menu-button" type="button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-label="Open navigation"><Menu size={20} /></button>
      </header>
      {menuOpen && <nav className="mobile-menu" aria-label="Primary navigation"><a href="#conversation" onClick={() => setMenuOpen(false)}>Advisor</a><a href="#field" onClick={() => setMenuOpen(false)}>Field context</a><a href="#screening" onClick={() => setMenuOpen(false)}>Crop check</a></nav>}

      <main id="top" className="page-frame">
        <section className="masthead">
          <div className="masthead-copy">
            <div className="eyebrow-row"><span className="eyebrow">Field notebook / 04</span><span className="rule-dot" /></div>
            <h1>Good decisions<br /><i>start with a closer look.</i></h1>
            <p className="masthead-deck">A grounded farm companion for the small signals—weather, soil, crop, market—that shape the next decision.</p>
          </div>
          <div className="masthead-aside"><div className="aside-line" /><p>Today’s note</p><strong>Observe first.<br />Act with context.</strong><span>— your Sathi</span></div>
        </section>

        <div className="workspace-grid">
          <section id="conversation" className="conversation-panel panel-card" aria-labelledby="conversation-title">
            <div className="panel-topline"><span className="eyebrow">01 · Conversation</span><span className="live-tag"><span className="live-dot" /> private field note</span></div>
            <div className="conversation-heading"><div><h2 id="conversation-title">What are you seeing?</h2><p>Ask in your own words. Sathi will keep the answer close to your field context.</p></div><MessageCircle size={23} strokeWidth={1.5} /></div>
            <div className="message-list" aria-live="polite">
              {messages.map((message) => <Message key={message.id} message={message} />)}
              {sendState === 'sending' && <div className="typing-state"><span /><span /><span /> Sathi is checking the available services…</div>}
              <div ref={endOfMessages} />
            </div>
            <form className="composer" onSubmit={send}>
              <label className="visually-hidden" htmlFor="question">Ask Sathi a question</label>
              <textarea id="question" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Write a question or field observation…" rows="2" maxLength={1200} disabled={sendState === 'sending'} />
              <div className="composer-footer"><span><Paperclip size={14} /> Attach context later</span><span>{draft.length}/1200</span><button className="send-button" type="submit" disabled={!draft.trim() || sendState === 'sending'} aria-label="Send question"><Send size={17} /></button></div>
            </form>
            <div className="quick-prompts"><span>Try asking</span>{prompts.map((prompt) => <button key={prompt} type="button" onClick={() => setDraft(prompt)}>{prompt}</button>)}</div>
            {sendState === 'degraded' && <div className="notice-bar" role="status"><CircleAlert size={16} /><span>Conversation is in an unavailable state. No farm action was taken.</span><button type="button" onClick={() => { setSendState('idle'); checkStatus(); }}><RefreshCw size={14} /> Retry</button></div>}
          </section>

          <aside className="context-column">
            <section id="field" className="field-card panel-card" aria-labelledby="field-title">
              <div className="panel-topline"><span className="eyebrow">02 · Field context</span><button className="quiet-button" type="button">Change <ChevronDown size={14} /></button></div>
              <div className="field-card-heading"><div><span className="field-status"><span className="status-dot status-dot--connected" /> selected field</span><h2 id="field-title">North plot</h2><p><MapPin size={14} /> Chitradurga, Karnataka</p></div><div className="crop-stamp"><span>crop</span><strong>Tomato</strong></div></div>
              <FieldSketch />
              <div className="field-facts"><div><span>Stage</span><strong>Flowering</strong></div><div><span>Last note</span><strong>Not recorded</strong></div></div>
              <div className="context-empty"><CircleAlert size={15} /><span>No recent observations connected. Add a note to build this field’s timeline.</span></div>
            </section>

            <section className="provider-card panel-card" aria-labelledby="provider-title">
              <div className="panel-topline"><span className="eyebrow">03 · Service status</span><button className="icon-button" type="button" onClick={checkStatus} aria-label="Refresh service status"><RefreshCw size={15} /></button></div>
              <h2 id="provider-title">What’s available now</h2>
              <ProviderRow label="Farm API" detail="field context + notes" state={networkState} icon={CloudSun} />
              <ProviderRow label="Advisor provider" detail="conversation + sources" state={providerState} icon={MessageCircle} />
              <ProviderRow label="Tool catalog" detail="bounded standalone tools" state={toolState} icon={ThermometerSun} />
              <ProviderRow label="Crop models" detail={prototypeCapabilities ? `${prototypeCapabilities.model_count} research models · ${prototypeCapabilities.supported_crops.length} crops` : 'prototype catalog unavailable'} state={visionState} icon={Leaf} />
              <p className="status-footnote"><span className="status-dot status-dot--degraded" /> {statusMessage}</p>
            </section>
          </aside>
        </div>

              <section id="screening"><CropScreening capabilities={prototypeCapabilities} onRetry={() => setStatusMessage('Photo cleared. No screening result was retained.')} /></section>
        <footer className="page-footer"><span>Kisan Sathi / built for the field</span><span>Information support only · confirm consequential decisions with a local agronomist</span><span>HTTP API mode</span></footer>
      </main>
    </div>
  );
}
