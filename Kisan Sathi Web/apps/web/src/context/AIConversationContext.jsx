import { createContext, useContext, useMemo, useReducer } from 'react';
import { harnessClient } from '../api/harnessClient.js';

export const initialConversationState = { sessionId: null, lastSequence: 0, messages: [], pendingApproval: null, status: 'idle', error: null };

export function conversationReducer(state, action) {
  if (action.type === 'session') return { ...state, sessionId: action.sessionId, status: 'ready', error: null };
  if (action.type === 'event') {
    const event = action.event;
    if (!event || event.sequence <= state.lastSequence) return state;
    const payload = event.payload || {};
    if (event.kind === 'agentMessageDelta') {
      const id = `assistant:${event.turn_id}`;
      const messages = state.messages.some((item) => item.id === id) ? state.messages.map((item) => item.id === id ? { ...item, content: `${item.content}${payload.text || ''}` } : item) : [...state.messages, { id, role: 'assistant', content: payload.text || '' }];
      return { ...state, lastSequence: event.sequence, messages, status: 'streaming' };
    }
    if (event.kind === 'agentMessageCompleted') {
      const id = `assistant:${event.turn_id}`;
      const messages = state.messages.map((item) => item.id === id ? { ...item, content: payload.text || item.content } : item);
      return { ...state, lastSequence: event.sequence, messages, status: 'ready' };
    }
    return { ...state, lastSequence: event.sequence, pendingApproval: event.kind === 'approval' ? payload : state.pendingApproval, status: event.kind === 'turnCompleted' ? payload.status || 'ready' : state.status };
  }
  if (action.type === 'error') return { ...state, status: 'degraded', error: action.error };
  if (action.type === 'reset') return initialConversationState;
  return state;
}

const ConversationContext = createContext(null);

export function AIConversationProvider({ children }) {
  const [state, dispatch] = useReducer(conversationReducer, initialConversationState);
  const value = useMemo(() => ({ state, dispatch, client: harnessClient }), [state]);
  return <ConversationContext.Provider value={value}>{children}</ConversationContext.Provider>;
}

export function useAIConversation() {
  const value = useContext(ConversationContext);
  if (!value) throw new Error('useAIConversation must be used inside AIConversationProvider');
  return value;
}
