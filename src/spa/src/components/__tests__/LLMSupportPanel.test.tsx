import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

import LLMSupportPanel from '../LLMSupportPanel';
import type { LLMSupportPayload } from '../../api/pdfTraining';

const mockGetLLMSupport = vi.fn();
const mockGetJob = vi.fn();
const mockStartSupport = vi.fn();

vi.mock('../../api/pdfTraining', () => ({
  getLLMSupport: (...args: unknown[]) => mockGetLLMSupport(...args),
  getJob: (...args: unknown[]) => mockGetJob(...args),
  startLLMSupport: (...args: unknown[]) => mockStartSupport(...args),
}));

const wrapper = (ui: React.ReactElement) => {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

describe('LLMSupportPanel', () => {
  beforeEach(() => {
    mockGetLLMSupport.mockReset();
    mockGetJob.mockReset();
    mockStartSupport.mockReset();
    mockGetLLMSupport.mockResolvedValue({
      document_id: 'doc-default',
      generated_at: '2024-01-01T00:00:00Z',
      provider: 'deepseek',
      model: 'deepseek-chat',
      dry_run: true,
      fields: [],
      rows: [],
    });
    mockGetJob.mockResolvedValue({
      id: 'job',
      job_type: 'ANNOTATION',
      status: 'SUCCEEDED',
      detail: null,
      payload: null,
      resource_type: 'document',
      resource_id: 'doc-1',
      started_at: null,
      finished_at: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    });
  });

  it('renders placeholder when no document is selected', () => {
    wrapper(<LLMSupportPanel documentId={null} />);
    expect(screen.getByText(/Select a document/)).toBeInTheDocument();
  });

  it('renders loading state when fetching suggestions', async () => {
    mockGetLLMSupport.mockImplementation(() => new Promise(() => undefined));

    wrapper(<LLMSupportPanel documentId="doc-load" />);

    expect(await screen.findByTestId('llm-support-loading')).toBeInTheDocument();
  });

  it('renders error state when fetching suggestions fails', async () => {
    mockGetLLMSupport.mockRejectedValue(new Error('Failed to fetch'));

    wrapper(<LLMSupportPanel documentId="doc-err" />);

    expect(await screen.findByText(/Failed to fetch/)).toBeInTheDocument();
  });

  it('renders running state when a support job is active', async () => {
    mockGetLLMSupport.mockResolvedValueOnce({
      document_id: 'doc-run',
      generated_at: '2024-06-01T00:00:00Z',
      provider: 'deepseek',
      model: 'deepseek-chat',
      dry_run: true,
      fields: [],
      rows: [],
    });
    mockStartSupport.mockResolvedValue({ job_id: 'job-123', job_type: 'ANNOTATION', status: 'PENDING' });
    mockGetJob.mockResolvedValue({
      id: 'job-123',
      job_type: 'ANNOTATION',
      status: 'RUNNING',
      detail: 'Analyzing',
      payload: null,
      resource_type: 'document',
      resource_id: 'doc-run',
      started_at: null,
      finished_at: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    });

    wrapper(<LLMSupportPanel documentId="doc-run" />);

    const trigger = await screen.findByRole('button', { name: /Generate suggestions/i });
    await userEvent.click(trigger);

    expect(await screen.findByTestId('llm-support-status-running')).toBeInTheDocument();
    expect(screen.getByText(/Analyzing/)).toBeInTheDocument();
  });

  it('renders fetched suggestions', async () => {
    const payload: LLMSupportPayload = {
      document_id: 'doc-1',
      generated_at: '2024-06-01T00:00:00Z',
      provider: 'deepseek',
      model: 'deepseek-chat',
      dry_run: true,
      fields: ['contract_name'],
      rows: [
        {
          row_id: '1',
          cost_usd: 0.123456,
          suggestions: [
            {
              field: 'contract_name',
              decision: 'change',
              suggested: 'Updated value',
              rationale: 'Example rationale',
              confidence: 0.8,
            },
          ],
        },
      ],
    };
    mockGetLLMSupport.mockResolvedValue(payload);

    wrapper(<LLMSupportPanel documentId="doc-1" />);

    await waitFor(() => expect(screen.getByText('Updated value')).toBeInTheDocument());
    expect(screen.getByText(/Model:/)).toHaveTextContent('deepseek-chat');
    expect(screen.getByText(/Example rationale/)).toBeInTheDocument();
    expect(screen.getByText(/Confidence: 80%/)).toBeInTheDocument();
    expect(screen.getByText('$0.123456')).toBeInTheDocument();
  });
});
