import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import VoiceAssistant from './VoiceAssistant.jsx';

const mocks = vi.hoisted(() => ({ submitImage: vi.fn().mockResolvedValue(true) }));

vi.mock('../components/features/ai/VoiceButton.jsx', () => ({ default: () => <button type="button">Voice input</button> }));
vi.mock('../components/features/ai/ConversationView.jsx', () => ({ default: () => <div>Conversation</div> }));
vi.mock('../context/AIConversationContext.jsx', () => ({
  useAIConversation: () => ({
    language: 'en',
    voiceState: 'idle',
    fields: [{ id: 'field-1', name: 'North field' }],
    selectedField: { id: 'field-1', name: 'North field' },
    selectedFieldId: 'field-1',
    setSelectedFieldId: vi.fn(),
    sendText: vi.fn(),
    submitImage: mocks.submitImage,
    processing: false,
  }),
}));

describe('VoiceAssistant', () => {
  afterEach(() => cleanup());

  it('keeps camera and photo-library attachments available beside voice input', async () => {
    const { container } = render(<VoiceAssistant />);

    expect(screen.getByRole('button', { name: 'Choose crop photo' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Take crop photo' })).toBeTruthy();
    expect(screen.getByText(/Attach a clear leaf photo from camera or library/i)).toBeTruthy();

    const file = new File(['leaf'], 'tomato-leaf.jpg', { type: 'image/jpeg' });
    fireEvent.change(container.querySelectorAll('input[type="file"]')[0], { target: { files: [file] } });
    await waitFor(() => expect(mocks.submitImage).toHaveBeenCalledWith(file));
    expect(screen.getByText(/Photo added/i)).toBeTruthy();
  });
});
