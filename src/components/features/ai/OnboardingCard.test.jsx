import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OnboardingCard from './OnboardingCard.jsx';

const conversation = vi.hoisted(() => ({
  onboarding: null,
  onboardingError: null,
  refreshOnboardingStatus: vi.fn(),
  language: 'en',
  sendText: vi.fn(),
  processing: false,
}));
vi.mock('../../../context/AIConversationContext.jsx', () => ({ useAIConversation: () => conversation }));

afterEach(() => { cleanup(); conversation.onboarding = null; conversation.sendText.mockClear(); });

describe('chat onboarding guidance', () => {
  it('opens the map workflow for a missing field', () => {
    conversation.onboarding = { next_setup_step: 'create_field', voice_configured: true };
    render(<MemoryRouter><OnboardingCard /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /Open field map/ }).getAttribute('href')).toBe('/fields?add=1');
    expect(screen.getByText(/trace the corners/i)).toBeTruthy();
  });

  it('opens boundary review for an approximate field', () => {
    conversation.onboarding = { next_setup_step: 'review_boundary', voice_configured: true };
    render(<MemoryRouter><OnboardingCard /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /Review boundary/ }).getAttribute('href')).toBe('/fields?review=1');
  });

  it('asks the agent to confirm a crop-cycle write before saving', () => {
    conversation.onboarding = { next_setup_step: 'start_crop_cycle', voice_configured: true };
    render(<MemoryRouter><OnboardingCard /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: /Start crop cycle/ }));
    expect(conversation.sendText).toHaveBeenCalledWith(expect.stringContaining('confirm the exact record before saving'));
  });
});
