import React from 'react';
import { useDocumentJobs } from '../hooks/useJobPolling';

interface DocumentProcessingStatusProps {
  documentId: string | null;
}

const formatTimestamp = (value: string | undefined | null): string => {
  if (!value) {
    return '—';
  }
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch (error) {
    return value;
  }
};

const DocumentProcessingStatus: React.FC<DocumentProcessingStatusProps> = ({ documentId }) => {
  if (!documentId) {
    return (
      <div className="processing-status processing-status--idle">
        Select a document to monitor preprocessing progress.
      </div>
    );
  }

  const { jobs, isLoading, activeJob, latestJob } = useDocumentJobs(documentId);

  if (isLoading && jobs.length === 0) {
    return (
      <div className="processing-status processing-status--active" aria-live="polite">
        <span className="processing-status__spinner" aria-hidden="true" />
        <div>
          <strong>Checking preprocessing status…</strong>
          <div>We are contacting the server to retrieve the latest analysis updates.</div>
        </div>
      </div>
    );
  }

  if (!jobs.length) {
    return (
      <div className="processing-status processing-status--idle" aria-live="polite">
        No preprocessing jobs have been recorded yet for this document. A background analysis will start as soon as the upload finishes.
      </div>
    );
  }

  const latest = latestJob!;

  if (activeJob) {
    return (
      <div className="processing-status processing-status--active" aria-live="polite">
        <span className="processing-status__spinner" aria-hidden="true" />
        <div>
          <strong>Analyzing document…</strong>
          <div>{activeJob.detail || 'Preparing annotation assets so you can start reviewing the PDF.'}</div>
          <small>Last update {formatTimestamp(activeJob.updated_at)}</small>
        </div>
      </div>
    );
  }

  if (latest.status === 'FAILED') {
    return (
      <div className="processing-status processing-status--error" role="alert">
        <strong>Background preprocessing failed.</strong>
        <div>{latest.detail || 'The extraction service reported an unexpected error.'}</div>
        <small>Last attempt {formatTimestamp(latest.updated_at)}</small>
      </div>
    );
  }

  return (
    <div className="processing-status processing-status--success" aria-live="polite">
      <strong>Preprocessing completed.</strong>
      <div>{latest.detail || 'The document is ready for PDF annotation.'}</div>
      <small>Finished {formatTimestamp(latest.finished_at || latest.updated_at)}</small>
    </div>
  );
};

export default DocumentProcessingStatus;
