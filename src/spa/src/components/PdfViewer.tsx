import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { fetchPdfContent, getJobs, JobDetail } from '../api/pdfTraining';

// Set up PDF.js worker source
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PdfViewerProps {
  documentId: string | null;
}

const PdfViewer: React.FC<PdfViewerProps> = ({ documentId }) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);

  const { data: pdfUrl, isLoading, isError, error } = useQuery({
    queryKey: ['pdfContent', documentId],
    queryFn: () => {
      if (!documentId) {
        return Promise.reject('No document ID provided');
      }
      return fetchPdfContent(documentId);
    },
    enabled: !!documentId, // Only run the query if documentId is available
  });

  const { data: jobs = [] } = useQuery<JobDetail[]>({
    queryKey: ['document-jobs', documentId],
    queryFn: () => getJobs({ resourceType: 'document', resourceId: documentId as string }),
    enabled: !!documentId,
  });

  const activeJob = jobs.find((job) => job.status === 'PENDING' || job.status === 'RUNNING');

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1); // Reset to first page on new document load
  };

  if (!documentId) {
    return <div className="pdf-viewer-placeholder">Select a document to view its PDF.</div>;
  }

  if (isLoading) {
    if (activeJob) {
      return (
        <div className="pdf-viewer-loading" aria-live="polite">
          <span className="processing-status__spinner" aria-hidden="true" />
          <div>
            <strong>Analyzing document…</strong>
            <div>{activeJob.detail || 'Preparing annotation assets before rendering the PDF.'}</div>
          </div>
        </div>
      );
    }
    return <div className="pdf-viewer-loading">Loading PDF...</div>;
  }

  if (isError) {
    return <div className="pdf-viewer-error">Error loading PDF: {(error as Error).message}</div>;
  }

  return (
    <div className="pdf-viewer-container">
      <Document
        file={pdfUrl}
        onLoadSuccess={onDocumentLoadSuccess}
        onLoadError={(err) => console.error('Failed to load PDF:', err)}
      >
        <Page pageNumber={pageNumber} />
      </Document>
      <div className="pdf-viewer-controls">
        <button
          onClick={() => setPageNumber(prevPage => Math.max(prevPage - 1, 1))}
          disabled={pageNumber <= 1}
        >
          Previous
        </button>
        <span>Page {pageNumber} of {numPages || '...'}</span>
        <button
          onClick={() => setPageNumber(prevPage => Math.min(prevPage + 1, numPages || 1))}
          disabled={pageNumber >= (numPages || 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default PdfViewer;