import { LoaderCircle, Mic, Square, Volume2 } from 'lucide-react';
import { useAIConversation } from '../../../context/AIConversationContext.jsx';

export default function VoiceButton({ large = false }) {
  const { voiceState, processing, startVoice, stopVoice } = useAIConversation();
  const listening = voiceState === 'listening';
  const busy = !listening && (voiceState === 'processing' || voiceState === 'responding' || processing);
  const size = large ? 50 : 19;
  const icon = voiceState === 'processing' ? <LoaderCircle className="animate-spin" size={size} /> : voiceState === 'responding' ? <Volume2 size={size} /> : listening ? <Square size={size} /> : <Mic size={size} />;
  return <button type="button" onClick={listening ? stopVoice : startVoice} disabled={busy} aria-label={listening ? 'Finish and send voice input' : 'Start voice input'} title={listening ? 'Tap again to send your voice message' : 'Start voice input'} className={`${large ? 'size-36 border-8' : 'size-10'} grid shrink-0 place-items-center rounded-full border-white text-white shadow-xl transition disabled:cursor-wait ${listening ? 'scale-110 bg-emerald-600 ring-8 ring-emerald-100' : voiceState === 'processing' ? 'bg-amber-500' : voiceState === 'responding' ? 'bg-info' : 'bg-primary-dark hover:scale-105 hover:bg-primary'}`}>{icon}</button>;
}
