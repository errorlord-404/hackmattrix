import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Bot, Camera, Check, ImagePlus, Mic, RotateCcw, Send, Sparkles, User, Volume2, VolumeX, Wrench } from 'lucide-react';
import VoiceButton from './VoiceButton.jsx';
import OnboardingCard from './OnboardingCard.jsx';
import { navigateToUiAction } from './uiNavigation.js';
import { useAIConversation } from '../../../context/AIConversationContext.jsx';

const statusCopy = { en: 'Tap the mic or type a message below', hi: 'माइक दबाएं या नीचे संदेश लिखें', mr: 'मायक्रोफोन टॅप करा किंवा संदेश लिहा' };

function OriginalSpeech({ message }) {
  if (!message.originalText || message.originalText === message.text) return null;
  return <details className="mt-2 rounded-lg border border-white/40 bg-white/10 px-2.5 py-1.5 text-[11px] text-white/90">
    <summary className="cursor-pointer font-semibold">Original speech</summary>
    <p className="mt-1 whitespace-pre-wrap leading-5">{message.originalText}</p>
  </details>;
}

function LocalFarmerExplanation({ message }) {
  if (!message.localizedSummary || message.languageCode === 'en-IN') return null;
  return <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12px] leading-5 text-emerald-950"><p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-emerald-700">Farmer explanation</p><p className="whitespace-pre-wrap">{message.localizedSummary}</p></div>;
}

export default function ConversationView({ compact = false }) {
  const { messages, sendText, voiceState, processing, language, submitImage, error, toolEvents, pendingAction, resolveConfirmation, harnessStatus, speakMessage, autoPlay, setAutoPlay, conversationLanguage, uiAction, consumeUiAction, restartConversation } = useAIConversation();
  const [input, setInput] = useState('');
  const [clarificationText, setClarificationText] = useState('');
  const [attachmentState, setAttachmentState] = useState('');
  const [speakerState, setSpeakerState] = useState('');
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const cameraRef = useRef(null);
  const status = statusCopy[language] || statusCopy.en;

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, processing, voiceState]);
  useEffect(() => {
    if (!uiAction?.path) return;
    navigateToUiAction(uiAction.path);
    consumeUiAction(uiAction.id);
  }, [consumeUiAction, uiAction]);
  const submit = (event) => { event.preventDefault(); if (voiceState === 'idle' && input.trim()) { sendText(input); setInput(''); } };
  const question = pendingAction?.payload?.questions?.[0];
  const requestText = pendingAction?.payload?.reason || question?.question || 'Allow KisanSathi to complete this requested farm action?';
  const submitPhoto = async (file, source) => {
    if (!file) return;
    setAttachmentState(source === 'camera' ? 'Saving camera photo…' : 'Saving crop photo…');
    const accepted = await submitImage(file);
    setAttachmentState(accepted ? 'Photo added to this farm conversation.' : 'Photo could not be added. Check the message above and try again.');
  };
  const testSpeaker = async () => {
    setSpeakerState('Testing speaker…');
    try {
      const testText = conversationLanguage === 'hi-IN' ? 'आपका KisanSathi स्पीकर काम कर रहा है।' : conversationLanguage === 'mr-IN' ? 'तुमचा KisanSathi स्पीकर काम करत आहे.' : 'Your KisanSathi speaker is working.';
      await speakMessage({ speechText: testText, languageCode: conversationLanguage });
      setSpeakerState('Speaker test sent. If you did not hear it, check your device volume and voice settings.');
    } catch {
      setSpeakerState('Speaker test could not start. Check the Sarvam key and voice settings.');
    }
  };

  return <div className="flex min-h-0 w-full flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-card">
    <div className="flex items-center justify-between gap-3 border-b border-border bg-emerald-50/70 px-4 py-2 text-[11px] font-semibold text-primary-dark">
      <span className="flex items-center gap-1.5"><span className={`size-2 rounded-full ${harnessStatus === 'ready' ? 'bg-emerald-500' : harnessStatus === 'starting' ? 'animate-pulse bg-amber-500' : 'bg-red-500'}`} />Codex farm harness</span>
      <div className="ml-auto flex items-center gap-2"><span className="hidden sm:inline">{harnessStatus === 'ready' ? 'Grounded tools connected' : harnessStatus === 'browser' ? 'Desktop companion required' : harnessStatus}</span><button type="button" disabled={processing} onClick={() => restartConversation()} aria-label="Start a new Codex conversation" title="Start a fresh Codex conversation; farm records are kept" className="inline-flex items-center gap-1 rounded-full border border-transparent bg-emerald-100/60 px-2.5 py-1 text-text-secondary transition hover:bg-white disabled:opacity-50"><RotateCcw size={13} /><span className="hidden sm:inline">New chat</span></button><button type="button" onClick={() => setAutoPlay(!autoPlay)} aria-pressed={autoPlay} aria-label={autoPlay ? 'Turn automatic speech off' : 'Turn automatic speech on'} title={autoPlay ? 'Automatic speech is on for every Codex answer' : 'Turn on automatic speech for every Codex answer'} className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 transition ${autoPlay ? 'border-primary/25 bg-white text-primary-dark shadow-sm' : 'border-transparent bg-emerald-100/60 text-text-secondary hover:bg-white'}`}>{autoPlay ? <Volume2 size={13} /> : <VolumeX size={13} />}<span>Auto-speak {autoPlay ? 'on' : 'off'}</span></button></div>
    </div>
    <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
      <OnboardingCard />
      {messages.length ? messages.map((message) => <div key={message.id} className={`flex items-start gap-2.5 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
        <div className={`grid size-8 shrink-0 place-items-center rounded-full text-xs font-bold ${message.role === 'user' ? 'bg-primary text-white' : 'bg-emerald-100 text-emerald-800'}`}>{message.role === 'user' ? <User size={15} /> : <Bot size={15} />}</div>
        <div className={`flex max-w-[85%] flex-col ${message.role === 'user' ? 'items-end' : 'items-start'}`}>
          <span className="mb-1 px-1 text-[11px] font-bold text-text-secondary">{message.role === 'user' ? 'You' : 'KisanSathi · Codex'}</span>
          <div className={`rounded-2xl px-4 py-3 text-xs leading-relaxed sm:text-sm ${message.role === 'user' ? 'rounded-tr-none bg-primary text-white' : 'rounded-tl-none border border-border bg-surface-muted text-text-primary'}`}>
            {message.image && <img src={message.image} alt="Uploaded crop" className="mb-2 max-h-48 w-full rounded-xl object-cover" />}
            {message.text && <p className="whitespace-pre-wrap">{message.text}</p>}
            {message.role === 'assistant' && message.text && <button type="button" onClick={() => speakMessage(message).catch(() => undefined)} className="mt-2 inline-flex items-center gap-1 rounded-md border border-border bg-white/70 px-2 py-1 text-[11px] font-semibold text-primary-dark hover:bg-white" aria-label="Speak this answer"><Volume2 size={12} /> Speak</button>}
            {message.role === 'assistant' && <LocalFarmerExplanation message={message} />}
            {message.role === 'user' && <OriginalSpeech message={message} />}
            {message.translating && <span className="mt-2 inline-flex items-center gap-1 text-[10px] text-text-muted"><Sparkles size={11} className="animate-spin" /> Translating for your language…</span>}
            {message.via === 'voice' && <span className="mt-2 inline-flex items-center gap-1 text-[10px] opacity-70"><Mic size={11} /> Voice message</span>}
            {message.warning && <p className="mt-2 flex items-start gap-1 text-[10px] text-amber-700"><AlertTriangle size={12} className="mt-0.5 shrink-0" />{message.warning}</p>}
            {message.citations?.length > 0 && <p className="mt-2 text-[10px] text-text-muted">Sources: {message.citations.map((item) => item.source || item.title).join(', ')}</p>}
          </div>
          <span className="mt-1 px-1 text-[10px] text-text-muted">{message.time}</span>
        </div>
      </div>) : <div className="grid min-h-48 place-items-center text-center text-sm text-text-secondary"><div><Sparkles className="mx-auto text-primary" size={25} /><p className="mt-3">{processing ? 'Codex is preparing a grounded response…' : 'Ask about a recorded field observation.'}</p></div></div>}

      {toolEvents.slice(-3).map((event) => <div key={event.id} className={`rounded-xl border px-3 py-2 text-xs ${event.status === 'failed' ? 'border-red-200 bg-red-50 text-red-700' : 'border-emerald-100 bg-emerald-50 text-primary-dark'}`}>
        <div className="flex items-center gap-2"><Wrench size={14} /><span className="font-semibold">{event.tool}</span><span className="ml-auto">{event.status === 'completed' ? <Check size={14} /> : event.status === 'inProgress' ? 'Running…' : 'Unavailable'}</span></div>
        {event.action?.affected_ids && Object.keys(event.action.affected_ids).length > 0 && <p className="mt-1 text-[10px]">Updated: {Object.values(event.action.affected_ids).join(', ')}</p>}
        {event.action?.warnings?.length > 0 && <p className="mt-1 flex items-start gap-1 text-[10px] text-amber-700"><AlertTriangle size={11} />{event.action.warnings.join(' ')}</p>}
      </div>)}

      {pendingAction && <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950"><p className="font-bold">{pendingAction.kind === 'clarification' ? 'KisanSathi needs one detail' : 'Farmer confirmation required'}</p><p className="mt-1 leading-5">{requestText}</p>{pendingAction.kind === 'clarification' ? <div className="mt-3 flex flex-wrap gap-2">{question?.options?.map((option) => <button key={option.label} onClick={() => resolveConfirmation({ answers: { [question.id]: { answers: [option.label] } } })} className="rounded-lg border border-amber-300 bg-white px-3 py-2 font-semibold">{option.label}</button>)}{!question?.options?.length && <><input value={clarificationText} onChange={(event) => setClarificationText(event.target.value)} className="min-w-40 flex-1 rounded-lg border border-amber-300 bg-white px-3 py-2" placeholder="Type your answer" /><button disabled={!clarificationText.trim()} onClick={() => { resolveConfirmation({ answers: { [question?.id || 'answer']: { answers: [clarificationText] } } }); setClarificationText(''); }} className="rounded-lg bg-primary px-3 py-2 font-semibold text-white disabled:opacity-50">Send</button></>}</div> : <div className="mt-3 flex gap-2"><button onClick={() => resolveConfirmation({ value: 'accept' })} className="rounded-lg bg-primary px-3 py-2 font-semibold text-white">Confirm</button><button onClick={() => resolveConfirmation({ value: 'decline' })} className="rounded-lg border border-amber-300 px-3 py-2 font-semibold">Cancel</button></div>}</div>}
      {processing && <div className="flex w-fit items-center gap-2 rounded-xl border border-border bg-surface-muted p-3 text-xs text-text-secondary"><Sparkles size={15} className="animate-spin text-primary" />{language === 'hi' ? 'सोच रहा हूँ…' : language === 'mr' ? 'विचार करत आहे…' : 'Codex is checking your farm tools…'}</div>}
      {error && <p className="rounded-lg bg-red-50 p-3 text-xs text-red-700">{error.message}</p>}
      <div ref={endRef} />
    </div>
    {!compact && <div className="shrink-0 space-y-2 border-t border-border bg-white p-3 sm:p-4">
      <div className="flex items-center gap-2 sm:gap-3"><VoiceButton /><form onSubmit={submit} className="flex flex-1 items-center gap-2 rounded-2xl border border-border bg-surface-muted/40 px-3 py-1.5">
        <button type="button" onClick={() => inputRef.current?.click()} aria-label="Choose crop photo" title="Choose a crop photo" disabled={processing} className="grid size-8 shrink-0 place-items-center rounded-lg text-text-secondary hover:bg-emerald-50 hover:text-primary disabled:opacity-40"><ImagePlus size={17} /></button>
        <button type="button" onClick={() => cameraRef.current?.click()} aria-label="Take crop photo" title="Take a crop photo" disabled={processing} className="grid size-8 shrink-0 place-items-center rounded-lg text-text-secondary hover:bg-emerald-50 hover:text-primary disabled:opacity-40"><Camera size={17} /></button>
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; submitPhoto(file, 'library'); event.target.value = ''; }} />
        <input ref={cameraRef} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; submitPhoto(file, 'camera'); event.target.value = ''; }} />
        <input value={input} onChange={(event) => setInput(event.target.value)} placeholder={voiceState === 'listening' ? 'Tap the mic again to send your voice message' : status} className="min-w-0 flex-1 bg-transparent py-1 text-xs outline-none sm:text-sm" /><button type="submit" disabled={!input.trim() || processing || voiceState !== 'idle'} aria-label="Send message" className="grid size-8 shrink-0 place-items-center rounded-xl bg-primary text-white disabled:opacity-40"><Send size={15} /></button>
      </form></div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pl-12 text-[11px] text-text-secondary"><span><b className="text-primary-dark">Mic:</b> tap once to record, again to send.</span><span><b className="text-primary-dark">Photo:</b> choose or take a clear leaf photo (JPEG, PNG, WebP; max 8 MB).</span><button type="button" onClick={testSpeaker} className="font-semibold text-primary underline underline-offset-2">Test speaker</button>{attachmentState && <span role="status" className="font-semibold text-primary-dark">{attachmentState}</span>}{speakerState && <span role="status" className="font-semibold text-primary-dark">{speakerState}</span>}</div>
    </div>}
  </div>;
}
