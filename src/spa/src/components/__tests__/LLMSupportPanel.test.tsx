import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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
  });

  it('renders placeholder when no document is selected', () => {
    wrapper(<LLMSupportPanel documentId={null} />);
    expect(screen.getByText(/Select a document/)).toBeInTheDocument();
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
  });
});
