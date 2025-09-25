import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

import PdfViewer from '../PdfViewer';

vi.mock('react-pdf/dist/Page/AnnotationLayer.css', () => ({}));
vi.mock('react-pdf/dist/Page/TextLayer.css', () => ({}));

const fetchPdfContentMock = vi.fn();
const getJobsMock = vi.fn();

let mockedPageCount = 3;

vi.mock('../../api/pdfTraining', () => ({
  fetchPdfContent: (...args: unknown[]) => fetchPdfContentMock(...args),
  getJobs: (...args: unknown[]) => getJobsMock(...args)
}));

vi.mock('react-pdf', () => {
  const React = require('react');
  const Document = ({ children, onLoadSuccess }: { children: React.ReactNode; onLoadSuccess?: (info: { numPages: number }) => void; }) => {
    React.useEffect(() => {
      onLoadSuccess?.({ numPages: mockedPageCount });
    }, []);
    return <div data-testid="pdf-document">{children}</div>;
  };
  const Page = ({ pageNumber }: { pageNumber: number }) => (
    <div data-testid="pdf-page">Page {pageNumber}</div>
  );
  const pdfjs = {
    version: '3.11.174',
    GlobalWorkerOptions: { workerSrc: '' }
  };
  return { Document, Page, pdfjs };
});

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false
      }
    }
  });
  return render(
    <QueryClientProvider client={client}>
      {ui}
    </QueryClientProvider>
  );
}

describe('PdfViewer', () => {
  beforeEach(() => {
    fetchPdfContentMock.mockReset();
    getJobsMock.mockReset();
    mockedPageCount = 3;
    getJobsMock.mockResolvedValue([]);
  });

  it('renders a placeholder when no document is selected', () => {
    renderWithClient(<PdfViewer documentId={null} />);
    expect(screen.getByText('Select a document to view its PDF.')).toBeInTheDocument();
  });

  it('shows a loading state while the PDF is being fetched', async () => {
    fetchPdfContentMock.mockImplementation(() => new Promise(() => undefined));
    renderWithClient(<PdfViewer documentId="doc-1" />);

    expect(screen.getByTestId('pdf-loading-spinner')).toBeInTheDocument();
  });

  it('shows job status when preprocessing is still running and requested', async () => {
    fetchPdfContentMock.mockImplementation(() => new Promise(() => undefined));
    getJobsMock.mockResolvedValue([
      {
        id: 'job-123',
        job_type: 'ANALYSIS',
        status: 'RUNNING',
        detail: 'Extracting metadata',
        payload: null,
        resource_type: 'document',
        resource_id: 'doc-99',
        started_at: null,
        finished_at: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }
    ]);

    renderWithClient(<PdfViewer documentId="doc-99" showJobStatus />);

    expect(await screen.findByText('Analyzing document…')).toBeInTheDocument();
    expect(screen.getByText('Extracting metadata')).toBeInTheDocument();
  });

  it('renders the PDF content and supports pagination controls', async () => {
    fetchPdfContentMock.mockResolvedValue('blob:pdf');
    renderWithClient(<PdfViewer documentId="doc-2" />);

    await screen.findByTestId('pdf-document');
    expect(fetchPdfContentMock).toHaveBeenCalledWith('doc-2');
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Page 3 of 3')).toBeInTheDocument();

    // Attempting to go beyond the last page keeps the same number
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Page 3 of 3')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /previous/i }));
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument();
  });

  it('disables pagination controls for single-page PDFs', async () => {
    mockedPageCount = 1;
    fetchPdfContentMock.mockResolvedValue('blob:pdf');

    renderWithClient(<PdfViewer documentId="doc-single" />);

    await screen.findByTestId('pdf-document');
    expect(screen.getByText('Page 1 of 1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
  });

  it('renders an error state when fetching fails', async () => {
    fetchPdfContentMock.mockRejectedValue(new Error('boom'));
    renderWithClient(<PdfViewer documentId="doc-err" />);

    await waitFor(() => {
      expect(screen.getByText(/Error loading PDF/i)).toBeInTheDocument();
    });
  });
});
