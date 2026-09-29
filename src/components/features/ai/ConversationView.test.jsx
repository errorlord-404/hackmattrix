import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ConversationView from './ConversationView.jsx';
import { navigateToUiAction } from './uiNavigation.js';

const mocks = vi.hoisted(() => ({ speakMessage: vi.fn().mockResolvedValue(undefined), submitImage: vi.fn().mockResolvedValue(true), setAutoPlay: vi.fn(), restartConversation: vi.fn().mockResolvedValue(true), uiAction: null, consumeUiAction: vi.fn() }));

vi.mock('./VoiceButton.jsx', () => ({ default: () => <button type="button">voice input</button> }));
vi.mock('../../../context/AIConversationContext.jsx', () => ({
  useAIConversation: () => ({
    messages: [{ id: 'assistant-1', role: 'assistant', text: 'Please inspect the field. Farmer summary: Inspect the field before irrigating.', englishText: 'Please inspect the field. Farmer summary: Inspect the field before irrigating.', localizedSummary: 'कृपया सिंचाई से पहले खेत देखें।', languageCode: 'hi-IN', time: '10:00 AM' }],
    sendText: vi.fn(), voiceState: 'idle', processing: false, language: 'hi', submitImage: mocks.submitImage, error: null,
    toolEvents: [], pendingAction: null, resolveConfirmation: vi.fn(), harnessStatus: 'ready', speakMessage: mocks.speakMessage,
    autoPlay: false, setAutoPlay: mocks.setAutoPlay, conversationLanguage: 'hi-IN',
    uiAction: mocks.uiAction, consumeUiAction: mocks.consumeUiAction, restartConversation: mocks.restartConversation,
  }),
}));

describe('ConversationView', () => {
  afterEach(() => { cleanup(); mocks.uiAction = null; mocks.consumeUiAction.mockClear(); });
  it('keeps Codex’s English answer and shows a separate local-language explanation', () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<ConversationView />);
    expect(screen.getByText(/Please inspect the field/)).toBeTruthy();
    expect(screen.getByText('Farmer explanation')).toBeTruthy();
    expect(screen.getByText('कृपया सिंचाई से पहले खेत देखें।')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Speak this answer' }));
    expect(mocks.speakMessage).toHaveBeenCalledWith(expect.objectContaining({ localizedSummary: 'कृपया सिंचाई से पहले खेत देखें।' }));
  });

  it('offers explicit photo library and camera attachment controls', () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<ConversationView />);
    expect(screen.getByRole('button', { name: 'Choose crop photo' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Take crop photo' })).toBeTruthy();
    expect(screen.getByText(/tap once to record, again to send/i)).toBeTruthy();
    expect(screen.getByText(/max 8 MB/i)).toBeTruthy();
  });

  it('offers one conversation-wide auto-speak switch', () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<ConversationView />);
    const autoSpeak = screen.getByRole('button', { name: 'Turn automatic speech on' });
    expect(autoSpeak).toBeTruthy();
    fireEvent.click(autoSpeak);
    expect(mocks.setAutoPlay).toHaveBeenCalledWith(true);
  });

  it('lets the farmer start a fresh Codex conversation without leaving the chat', () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<ConversationView />);
    fireEvent.click(screen.getByRole('button', { name: 'Start a new Codex conversation' }));
    expect(mocks.restartConversation).toHaveBeenCalledOnce();
  });

  it('opens only the route supplied by an allowlisted Codex UI action', () => {
    Element.prototype.scrollIntoView = vi.fn();
    window.history.replaceState({}, '', '/ai');
    mocks.uiAction = { id: 'setup-1', path: '/fields?add=1' };
    render(<ConversationView />);
    expect(window.location.pathname).toBe('/fields');
    expect(window.location.search).toBe('?add=1');
    expect(mocks.consumeUiAction).toHaveBeenCalledWith('setup-1');
  });

  it('uses a hash route when the packaged Electron app loads from a file URL', () => {
    const location = { protocol: 'file:', hash: '' };
    const history = { pushState: vi.fn() };
    const emit = vi.fn();
    navigateToUiAction('/marketplace', location, history, emit);
    expect(location.hash).toBe('#/marketplace');
    expect(history.pushState).not.toHaveBeenCalled();
    expect(emit).not.toHaveBeenCalled();
  });
});
