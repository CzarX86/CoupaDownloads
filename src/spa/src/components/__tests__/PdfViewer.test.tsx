import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

import PdfViewer from '../PdfViewer';

vi.mock('react-pdf/dist/Page/AnnotationLayer.css', () => ({}));
vi.mock('react-pdf/dist/Page/TextLayer.css', () => ({}));

const fetchPdfContentMock = vi.fn();

vi.mock('../../api/pdfTraining', () => ({
  fetchPdfContent: (...args: unknown[]) => fetchPdfContentMock(...args)
}));

vi.mock('react-pdf', () => {
  const React = require('react');
  const Document = ({ children, onLoadSuccess }: { children: React.ReactNode; onLoadSuccess?: (info: { numPages: number }) => void; }) => {
    React.useEffect(() => {
      onLoadSuccess?.({ numPages: 3 });
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
  });

  it('renders a placeholder when no document is selected', () => {
    renderWithClient(<PdfViewer documentId={null} />);
    expect(screen.getByText('Select a document to view its PDF.')).toBeInTheDocument();
  });

  it('shows a loading state while the PDF is being fetched', async () => {
    fetchPdfContentMock.mockImplementation(() => new Promise(() => undefined));
    renderWithClient(<PdfViewer documentId="doc-1" />);

    expect(screen.getByText('Loading PDF...')).toBeInTheDocument();
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

  it('renders an error state when fetching fails', async () => {
    fetchPdfContentMock.mockRejectedValue(new Error('boom'));
    renderWithClient(<PdfViewer documentId="doc-err" />);

    await waitFor(() => {
      expect(screen.getByText(/Error loading PDF/i)).toBeInTheDocument();
    });
  });
});
