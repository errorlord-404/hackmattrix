import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import FieldTasks from './FieldTasks.jsx';

const mocks = vi.hoisted(() => ({
  listFieldTasks: vi.fn(),
  getCropStageActionProposals: vi.fn(),
  createFieldTask: vi.fn(),
  updateFieldTaskStatus: vi.fn(),
}));

vi.mock('../context/FarmDataContext.jsx', () => ({
  useFarmData: () => ({ fields: [{ id: 'field-1', name: 'North field' }] }),
}));
vi.mock('../api/farmStateApi.js', () => ({ farmStateApi: mocks }));

describe('FieldTasks', () => {
  it('renders persisted actions and creates a farmer-confirmed task', async () => {
    mocks.listFieldTasks.mockResolvedValue([{ id: 'task-1', field_id: 'field-1', title: 'Inspect leaves', due_at: null, source: 'farmer_confirmed:agent', created_at: new Date().toISOString(), status: 'open' }]);
    mocks.getCropStageActionProposals.mockResolvedValue([{ crop_cycle_id: 'cycle-1', crop_name: 'tomato', stage: 'flowering', title: 'Check crop health and moisture at flowering', why: 'Review conditions', due_hint: 'Today', source: 'crop_stage_rule_v1' }]);
    mocks.createFieldTask.mockResolvedValue({ id: 'task-2' });
    render(<FieldTasks />);
    await waitFor(() => expect(screen.getByText('Inspect leaves')).toBeTruthy());
    fireEvent.change(screen.getByLabelText('Action title'), { target: { value: 'Record moisture' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add field action' }));
    await waitFor(() => expect(mocks.createFieldTask).toHaveBeenCalledWith(expect.objectContaining({ field_id: 'field-1', title: 'Record moisture', source: 'farmer_confirmed:manual_ui' })));
    fireEvent.click(screen.getByRole('button', { name: 'Accept as field action' }));
    await waitFor(() => expect(mocks.createFieldTask).toHaveBeenCalledWith(expect.objectContaining({ title: 'Check crop health and moisture at flowering', source: 'farmer_confirmed:crop_stage_rule_v1' })));
  });
});
