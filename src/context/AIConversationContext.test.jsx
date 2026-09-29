import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AIConversationProvider, useAIConversation } from './AIConversationContext.jsx';
import VoiceButton from '../components/features/ai/VoiceButton.jsx';
import { farmStateApi } from '../api/farmStateApi.js';

const farmDataState = vi.hoisted(() => ({ loading: true, error: null, fields: [] }));
vi.mock('./FarmDataContext.jsx', () => ({ useFarmData: () => ({ refresh: vi.fn(), ...farmDataState }) }));
vi.mock('../hooks/useLanguage.jsx', () => ({ useLanguage: () => ({ language: 'en' }) }));

class FakeMediaRecorder {
  static isTypeSupported = (mimeType) => mimeType === 'audio/webm;codecs=opus';

  constructor(_stream, options) {
    this.mimeType = options?.mimeType || 'audio/webm';
    this.state = 'inactive';
  }

  start() { this.state = 'recording'; }

  stop() {
    this.state = 'inactive';
    this.ondataavailable?.({ data: new Blob(['recorded voice'], { type: this.mimeType }) });
    this.onstop?.();
  }
}

function SpeakSample() {
  const { speakMessage } = useAIConversation();
  return <button onClick={() => speakMessage({ text: 'Your field is ready' })}>Speak sample</button>;
}

function VoiceLanguageStatus() {
  const { conversationLanguage } = useAIConversation();
  return <span data-testid="voice-language">{conversationLanguage}</span>;
}

function VoiceErrorStatus() {
  const { error, startVoice } = useAIConversation();
  return <><button onClick={startVoice}>Start recording</button><span data-testid="voice-error">{error?.message || ''}</span></>;
}

function UiActionStatus() {
  const { uiAction } = useAIConversation();
  return <span data-testid="ui-action">{uiAction?.path || ''}</span>;
}

function RestartSample() {
  const { restartConversation } = useAIConversation();
  return <button onClick={() => restartConversation()}>Restart conversation</button>;
}

function ConnectedScreenSample() {
  const { requestAdvisorReview } = useAIConversation();
  return <button onClick={() => requestAdvisorReview({ workflow: 'irrigation-review', fieldId: 'field-1', prompt: 'Review the connected irrigation screen.' })}>Review connected screen</button>;
}

function PhotoSample({ file }) {
  const { submitImage, messages } = useAIConversation();
  return <><button onClick={() => submitImage(file)}>Upload sample photo</button><span data-testid="photo-transcript">{messages.map((message) => message.text).join(' | ')}</span></>;
}

const declaredUiActions = [
  ['open_field_editor', '/fields?add=1'], ['open_field_marker', '/fields?add=1&guided=1'], ['review_field_boundary', '/fields?review=1'],
  ['open_farm_map', '/map'], ['open_soil_health', '/soil'], ['open_weather', '/weather'],
  ['open_irrigation', '/irrigation'], ['open_field_tasks', '/tasks'], ['open_crop_health', '/pest'],
  ['open_market_prices', '/market'], ['open_government_schemes', '/schemes'], ['open_farm_finance', '/finance'],
  ['open_machinery', '/machinery'], ['open_marketplace', '/marketplace'], ['open_reports', '/reports'],
  ['open_settings', '/settings'], ['open_device_setup', '/device-setup'],
];

describe('voice input', () => {
  let originalMediaDevices;
  let bridge;
  let stopTrack;
  let playAudio;
  let eventListener;

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    farmDataState.loading = true;
    farmDataState.error = null;
    farmDataState.fields = [];
    originalMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices');
    stopTrack = vi.fn();
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }) },
    });
    vi.stubGlobal('MediaRecorder', FakeMediaRecorder);
    playAudio = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('Audio', class {
      pause() {}
      play() { return playAudio(); }
    });
    bridge = {
      session: { status: vi.fn().mockResolvedValue({ codex: { running: false } }), start: vi.fn().mockResolvedValue({ threadId: 'test-thread' }) },
      voice: {
        transcribe: vi.fn().mockResolvedValue({ status: 'completed', transcript: 'Check my field' }),
        translate: vi.fn().mockResolvedValue({ status: 'completed', translated_text: 'Check my field' }),
        synthesize: vi.fn().mockResolvedValue({ status: 'completed', audio_base64: 'UklGRg==', audio_mime_type: 'audio/wav' }),
      },
      chat: { sendText: vi.fn().mockResolvedValue({ turnId: 'test-turn' }), sendImage: vi.fn().mockResolvedValue({ turnId: 'image-turn' }) },
      onEvent: vi.fn((listener) => { eventListener = listener; return vi.fn(); }),
    };
    vi.stubGlobal('kisanHarness', bridge);
    vi.spyOn(farmStateApi, 'getOnboardingStatus').mockResolvedValue({
      next_setup_step: 'review_boundary',
      profile: { exists: true, has_coordinates: true },
      fields: { active_count: 1, with_crop_count: 0, with_active_cycle_count: 0, approximate_boundaries: 1, unclassified_boundaries: 0 },
      voice_configured: false,
      reference_database_available: false,
      latest_sensor_observed_at: null,
    });
    vi.spyOn(farmStateApi, 'stageCropImage').mockResolvedValue({ upload_id: 'upload-1' });
    vi.spyOn(farmStateApi, 'createCropHealthConsent').mockResolvedValue({ consent_receipt_id: 'consent-1' });
    vi.spyOn(farmStateApi, 'createDiagnosisFromUpload').mockResolvedValue({ id: 'f0c37c52-9187-4e3d-9655-68565d76bb0f', status: 'provider_unavailable', provider: 'unconfigured' });
    vi.stubGlobal('confirm', vi.fn(() => true));
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:photo-preview') });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    Reflect.deleteProperty(URL, 'createObjectURL');
    Reflect.deleteProperty(URL, 'revokeObjectURL');
    vi.unstubAllGlobals();
    if (originalMediaDevices) Object.defineProperty(navigator, 'mediaDevices', originalMediaDevices);
    else Reflect.deleteProperty(navigator, 'mediaDevices');
  });

  it('sends the recording for transcription when the farmer taps the mic a second time', async () => {
    render(<AIConversationProvider><VoiceButton /></AIConversationProvider>);

    fireEvent.click(screen.getByRole('button', { name: 'Start voice input' }));
    const finish = await screen.findByRole('button', { name: 'Finish and send voice input' });
    fireEvent.click(finish);

    await waitFor(() => expect(bridge.voice.transcribe).toHaveBeenCalledWith(
      expect.any(ArrayBuffer), 'unknown', 'audio/webm;codecs=opus',
    ));
    await waitFor(() => expect(bridge.chat.sendText).toHaveBeenCalledWith(
      'Check my field', expect.objectContaining({ input_via: 'voice' }),
    ));
    expect(stopTrack).toHaveBeenCalled();
  });

  it('explains how to recover when Windows or Electron blocks microphone permission', async () => {
    const denied = new Error('Permission denied');
    denied.name = 'NotAllowedError';
    navigator.mediaDevices.getUserMedia.mockRejectedValueOnce(denied);
    render(<AIConversationProvider><VoiceErrorStatus /></AIConversationProvider>);

    fireEvent.click(screen.getByRole('button', { name: 'Start recording' }));

    await waitFor(() => expect(screen.getByTestId('voice-error').textContent).toContain(
      'Allow microphone access for KisanSathi in Windows',
    ));
  });

  it('uses detected speech language for Codex translation and every automatic spoken reply', async () => {
    bridge.voice.transcribe.mockResolvedValue({ status: 'completed', transcript: 'माझ्या शेतात पाणी द्या', language_code: 'mr-IN' });
    bridge.voice.translate.mockImplementation(async ({ input, source_language_code, target_language_code }) => ({
      status: 'completed',
      translated_text: source_language_code === 'mr-IN' && target_language_code === 'en-IN'
        ? 'Please check irrigation for my field.'
        : `मराठी: ${input}`,
    }));
    render(<AIConversationProvider><><VoiceButton /><VoiceLanguageStatus /></></AIConversationProvider>);

    fireEvent.click(screen.getByRole('button', { name: 'Start voice input' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Finish and send voice input' }));

    await waitFor(() => expect(bridge.voice.transcribe).toHaveBeenCalledWith(expect.any(ArrayBuffer), 'unknown', 'audio/webm;codecs=opus'));
    await waitFor(() => expect(bridge.voice.translate).toHaveBeenCalledWith({ input: 'माझ्या शेतात पाणी द्या', source_language_code: 'mr-IN', target_language_code: 'en-IN' }));
    await waitFor(() => expect(bridge.chat.sendText).toHaveBeenCalledWith('Please check irrigation for my field.', expect.objectContaining({ farmer_language: 'mr-IN', input_via: 'voice' })));
    await waitFor(() => expect(screen.getByTestId('voice-language').textContent).toBe('mr-IN'));

    eventListener({ kind: 'agentMessageCompleted', itemId: 'reply-1', text: 'Check the moisture reading before irrigating.' });
    await waitFor(() => expect(bridge.voice.translate).toHaveBeenCalledWith({ input: 'Check the moisture reading before irrigating.', source_language_code: 'en-IN', target_language_code: 'mr-IN' }));
    await waitFor(() => expect(bridge.voice.synthesize).toHaveBeenCalledWith({ text: 'मराठी: Check the moisture reading before irrigating.', language_code: 'mr-IN' }));
    expect(playAudio).toHaveBeenCalled();
  });

  it('preserves Codex’s English output while translating only its farmer summary', async () => {
    localStorage.setItem('kisansathi-conversation-language', 'hi-IN');
    bridge.voice.translate.mockResolvedValue({ status: 'completed', translated_text: 'सिंचाई से पहले नमी की जांच करें।' });
    function Transcript() {
      const { messages } = useAIConversation();
      return <>{messages.map((message) => <span key={message.id} data-testid={message.id}>{message.text}|{message.localizedSummary || ''}</span>)}</>;
    }
    render(<AIConversationProvider><Transcript /></AIConversationProvider>);
    eventListener({ kind: 'agentMessageCompleted', itemId: 'reply-2', text: 'Check the moisture reading before irrigating. Farmer summary: Check moisture before irrigation.' });

    await waitFor(() => expect(bridge.voice.translate).toHaveBeenCalledWith({ input: 'Check moisture before irrigation.', source_language_code: 'en-IN', target_language_code: 'hi-IN' }));
    await waitFor(() => expect(screen.getByTestId('codex-reply-2').textContent).toContain('Check the moisture reading before irrigating. Farmer summary: Check moisture before irrigation.|सिंचाई से पहले नमी की जांच करें।'));
  });

  it('accepts only an allowlisted Codex field-navigation action and hides its protocol token', async () => {
    render(<AIConversationProvider><><UiActionStatus /><PhotoSample file={null} /></></AIConversationProvider>);
    eventListener({ kind: 'agentMessageCompleted', itemId: 'setup-1', text: 'Let us draw your field boundary.\n[KISANSATHI_UI:open_field_editor]' });
    await waitFor(() => expect(screen.getByTestId('ui-action').textContent).toBe('/fields?add=1'));
    expect(screen.getByTestId('photo-transcript').textContent).toContain('Let us draw your field boundary.');
    expect(screen.getByTestId('photo-transcript').textContent).not.toContain('KISANSATHI_UI');
  });

  it('does not execute or hide an unrecognised Codex navigation token', async () => {
    render(<AIConversationProvider><><UiActionStatus /><PhotoSample file={null} /></></AIConversationProvider>);
    eventListener({ kind: 'agentMessageCompleted', itemId: 'unsafe-navigation', text: 'I cannot open an external page.\n[KISANSATHI_UI:open_any_url]' });
    await waitFor(() => expect(screen.getByTestId('photo-transcript').textContent).toContain('KISANSATHI_UI:open_any_url'));
    expect(screen.getByTestId('ui-action').textContent).toBe('');
  });

  it.each(declaredUiActions)('accepts the declared %s action and maps it to %s', async (action, path) => {
    render(<AIConversationProvider><><UiActionStatus /><PhotoSample file={null} /></></AIConversationProvider>);
    eventListener({ kind: 'agentMessageCompleted', itemId: `navigation-${action}`, text: `Open the requested screen.\n[KISANSATHI_UI:${action}]` });
    await waitFor(() => expect(screen.getByTestId('ui-action').textContent).toBe(path));
    expect(screen.getByTestId('photo-transcript').textContent).not.toContain('KISANSATHI_UI');
  });

  it('plays speech returned by the configured voice provider', async () => {
    render(<AIConversationProvider><SpeakSample /></AIConversationProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Speak sample' }));

    await waitFor(() => expect(bridge.voice.synthesize).toHaveBeenCalledWith({
      text: 'Your field is ready', language_code: 'en-IN',
    }));
    await waitFor(() => expect(playAudio).toHaveBeenCalledOnce());
  });

  it('runs one read-only startup turn after farm data loads without displaying it as farmer speech', async () => {
    farmDataState.loading = false;
    function Transcript() {
      const { messages } = useAIConversation();
      return <span data-testid="message-count">{messages.length}</span>;
    }
    const view = render(<AIConversationProvider><Transcript /></AIConversationProvider>);
    await waitFor(() => expect(bridge.chat.sendText).toHaveBeenCalledWith(
      expect.stringContaining('read-only startup check'),
      expect.objectContaining({ input_via: 'startup_check' }),
    ));
    expect(bridge.chat.sendText.mock.calls[0][0]).toContain('review the approximate or unclassified field boundary');
    expect(bridge.chat.sendText.mock.calls[0][0]).toContain('"active_fields":1');
    expect(screen.getByTestId('message-count').textContent).toBe('0');
    view.rerender(<AIConversationProvider><Transcript /></AIConversationProvider>);
    expect(bridge.chat.sendText).toHaveBeenCalledOnce();
  });

  it('queues a connected manual-screen request into the same farmer-scoped advisor session', async () => {
    render(<AIConversationProvider><ConnectedScreenSample /></AIConversationProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Review connected screen' }));
    await waitFor(() => expect(bridge.chat.sendText).toHaveBeenCalledWith(
      'Review the connected irrigation screen.',
      expect.objectContaining({ field_id: 'field-1', input_via: 'ui-irrigation-review' }),
    ));
  });

  it('rechecks farmer setup when a new Codex conversation starts', async () => {
    bridge.session.restart = vi.fn().mockResolvedValue({ threadId: 'fresh-thread' });
    render(<AIConversationProvider><RestartSample /></AIConversationProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Restart conversation' }));
    await waitFor(() => expect(bridge.session.restart).toHaveBeenCalledWith({ fieldId: '', language: 'en' }));
    await waitFor(() => expect(bridge.chat.sendText).toHaveBeenCalledWith(
      expect.stringContaining('read-only startup check'),
      expect.objectContaining({ input_via: 'startup_check' }),
    ));
  });

  it('stages, obtains consent, and sends only the diagnosis record to Codex', async () => {
    const file = new File(['image data'], 'crop.jpg', { type: 'image/jpeg' });
    Object.defineProperty(file, 'arrayBuffer', { value: vi.fn().mockResolvedValue(new ArrayBuffer(4)) });
    render(<AIConversationProvider><PhotoSample file={file} /></AIConversationProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Upload sample photo' }));

    await waitFor(() => expect(bridge.chat.sendText).toHaveBeenCalledWith(
      expect.stringContaining('f0c37c52-9187-4e3d-9655-68565d76bb0f'),
      expect.objectContaining({ input_via: 'crop-health-record' }),
    ));
    expect(farmStateApi.stageCropImage).toHaveBeenCalledWith(file, '');
    expect(farmStateApi.createCropHealthConsent).toHaveBeenCalledWith('upload-1', 'approved');
    expect(farmStateApi.createDiagnosisFromUpload).toHaveBeenCalledWith('upload-1', 'consent-1', undefined);
    expect(bridge.chat.sendImage).not.toHaveBeenCalled();
  });

  it('releases temporary crop-photo URLs when the chat unmounts', async () => {
    const file = new File(['image data'], 'crop.jpg', { type: 'image/jpeg' });
    Object.defineProperty(file, 'arrayBuffer', { value: vi.fn().mockResolvedValue(new ArrayBuffer(4)) });
    const view = render(<AIConversationProvider><PhotoSample file={file} /></AIConversationProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Upload sample photo' }));

    await waitFor(() => expect(bridge.chat.sendText).toHaveBeenCalledOnce());
    view.unmount();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:photo-preview');
  });

  it('keeps one saved evidence record when Codex image inspection is unsupported', async () => {
    bridge.chat.sendText.mockRejectedValue(new Error('localImage unsupported'));
    const file = new File(['image data'], 'crop.jpg', { type: 'image/jpeg' });
    Object.defineProperty(file, 'arrayBuffer', { value: vi.fn().mockResolvedValue(new ArrayBuffer(4)) });
    render(<AIConversationProvider><PhotoSample file={file} /></AIConversationProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Upload sample photo' }));

    await waitFor(() => expect(screen.getByTestId('photo-transcript').textContent).toContain('Photo saved, but image inspection is unavailable'));
    expect(farmStateApi.createDiagnosisFromUpload).toHaveBeenCalledOnce();
  });

  it('passes the crop recorded on the selected field to the saved evidence record', async () => {
    farmDataState.fields = [{ id: 'field-1', name: 'North plot', current_crop: 'Tomato' }];
    const file = new File(['image data'], 'tomato.jpg', { type: 'image/jpeg' });
    Object.defineProperty(file, 'arrayBuffer', { value: vi.fn().mockResolvedValue(new ArrayBuffer(4)) });
    render(<AIConversationProvider><PhotoSample file={file} /></AIConversationProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Upload sample photo' }));

    await waitFor(() => expect(farmStateApi.stageCropImage).toHaveBeenCalledWith(file, 'field-1'));
    expect(farmStateApi.createDiagnosisFromUpload).toHaveBeenCalledWith('upload-1', 'consent-1', 'Tomato');
  });
});
