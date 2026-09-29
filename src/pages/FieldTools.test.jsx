import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CropGuide, PestDisease } from './FieldTools.jsx';

const mocks = vi.hoisted(() => ({ stageCropImage: vi.fn(), createCropHealthConsent: vi.fn(), createDiagnosisFromUpload: vi.fn(), createDiagnosisFeedback: vi.fn(), getCropOptions: vi.fn(), getTimeline: vi.fn(), sendText: vi.fn() }));
vi.mock('../context/FarmDataContext.jsx', () => ({ useFarmData: () => ({ fields: [{ id: 'field-1', name: 'North field', current_crop: 'Tomato' }] }) }));
vi.mock('../context/AIConversationContext.jsx', () => ({ useAIConversation: () => ({ sendText: mocks.sendText }) }));
vi.mock('../api/farmStateApi.js', () => ({ farmStateApi: { stageCropImage: mocks.stageCropImage, createCropHealthConsent: mocks.createCropHealthConsent, createDiagnosisFromUpload: mocks.createDiagnosisFromUpload, createDiagnosisFeedback: mocks.createDiagnosisFeedback, getCropOptions: mocks.getCropOptions, getTimeline: mocks.getTimeline } }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('PestDisease', () => {
  it('shows model evidence and limitations from a completed crop-health response', async () => {
    mocks.stageCropImage.mockResolvedValue({ upload_id: 'upload-1' });
    mocks.createCropHealthConsent.mockResolvedValue({ consent_receipt_id: 'consent-1' });
    mocks.createDiagnosisFromUpload.mockResolvedValue({
      id: 'diagnosis-1', status: 'completed', label: 'healthy', confidence: 0.92,
      provider: 'local_tflite_demo', created_at: new Date().toISOString(),
      model_id: 'tfhub-mobilenetv3-small-tomato-specialist', model_version: 'controlled-demo-v0.2',
      inference_location: 'local-server-tflite', candidates: [{ label: 'healthy', score: 0.92 }, { label: 'late_blight', score: 0.04 }],
      crop_candidates: [{ label: 'tomato', score: 0.98 }, { label: 'potato', score: 0.01 }],
      limitations: ['Not field validated.'],
    });
    render(<MemoryRouter><PestDisease /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText('What crop is in this photo?'), { target: { value: 'tomato' } });
    fireEvent.change(screen.getByLabelText('What crop is in this photo?').closest('div').parentElement.querySelector('#diagnosis-file'), { target: { files: [new File(['image'], 'leaf.jpg', { type: 'image/jpeg' })] } });
    fireEvent.click(screen.getByLabelText('Approve crop-health screening'));
    fireEvent.click(screen.getByRole('button', { name: 'Save photo & run crop-health check' }));
    await waitFor(() => expect(screen.getByText('Model confidence: 92%')).toBeTruthy());
    expect(screen.getByText('Suggested crop — please confirm')).toBeTruthy();
    expect(screen.getByText('Model alternatives')).toBeTruthy();
    expect(screen.getByText(/Not field validated/)).toBeTruthy();
    expect(mocks.stageCropImage).toHaveBeenCalledWith(expect.any(File), 'field-1');
    expect(mocks.createCropHealthConsent).toHaveBeenCalledWith('upload-1', 'approved');
    expect(mocks.createDiagnosisFromUpload).toHaveBeenCalledWith('upload-1', 'consent-1', 'tomato');
    expect(mocks.sendText).toHaveBeenCalledWith(expect.stringContaining('diagnosis-1'), { via: 'crop-health-screen', fieldId: 'field-1' });
  });

  it('records opt-in feedback as a review lead instead of calling it model training', async () => {
    mocks.stageCropImage.mockResolvedValue({ upload_id: 'upload-1' });
    mocks.createCropHealthConsent.mockResolvedValue({ consent_receipt_id: 'consent-1' });
    mocks.createDiagnosisFromUpload.mockResolvedValue({ id: 'diagnosis-1', status: 'needs_expert_review', label: 'late_blight', provider: 'local_tflite_demo', created_at: new Date().toISOString(), limitations: ['Not field validated.'] });
    mocks.createDiagnosisFeedback.mockResolvedValue({ share_for_model_improvement: true });
    const { container } = render(<MemoryRouter><PestDisease /></MemoryRouter>);
    const ui = within(container);
    fireEvent.change(ui.getAllByRole('combobox')[1], { target: { value: 'tomato' } });
    fireEvent.change(container.querySelector('#diagnosis-file'), { target: { files: [new File(['image'], 'leaf.jpg', { type: 'image/jpeg' })] } });
    fireEvent.click(ui.getByLabelText('Approve crop-health screening'));
    fireEvent.click(ui.getByRole('button', { name: 'Save photo & run crop-health check' }));
    await waitFor(() => expect(ui.getByText('Was this result correct?')).toBeTruthy());
    fireEvent.click(ui.getByLabelText('Share diagnosis feedback for model improvement'));
    fireEvent.click(ui.getByRole('button', { name: 'Save my feedback' }));
    await waitFor(() => expect(mocks.createDiagnosisFeedback).toHaveBeenCalledWith('diagnosis-1', expect.objectContaining({ correctness: 'confirmed', confirmed_crop: 'tomato', label: 'late_blight', share_for_model_improvement: true })));
    expect(ui.getByText(/needs expert review before it can be used for model work/i)).toBeTruthy();
  });
});

describe('CropGuide', () => {
  it('shows sourced evidence without presenting a crop as an automatic choice', async () => {
    mocks.getTimeline.mockResolvedValue([]);
    mocks.getCropOptions.mockResolvedValue([{ crop_name: 'Paddy(Common)', season: 'Kharif', reference_price_per_quintal: 2379, price_source: 'Official source', source_url: 'https://example.test/price', checks: { season: true, previous_crop_rotation: null, soil_type: null }, missing_evidence: ['previous_crop_rotation', 'soil_type'], conflicts: [], status: 'candidate_needs_review' }]);
    render(<MemoryRouter><CropGuide /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'Run local crop rules' }));
    await waitFor(() => expect(screen.getByText('Paddy(Common)')).toBeTruthy());
    expect(screen.getByText('Online research available')).toBeTruthy();
    expect(screen.getByText(/Still needed: previous_crop_rotation, soil_type/)).toBeTruthy();
    expect(mocks.getCropOptions).toHaveBeenCalledWith('field-1', { season: 'Kharif', previousCrop: 'Tomato', soilType: '' });
  });

  it('hands an online sowing query to the agent after preserving the local fallback', async () => {
    render(<MemoryRouter><CropGuide /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'Research full sowing plan' }));
    await waitFor(() => expect(mocks.sendText).toHaveBeenCalledWith(
      expect.stringContaining('higher yield, export quality, or organic farming'),
      { via: 'crop-sowing-plan', fieldId: 'field-1' },
    ));
  });
});
