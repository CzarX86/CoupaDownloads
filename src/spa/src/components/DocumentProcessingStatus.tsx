import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJobs, JobDetail } from '../api/pdfTraining';

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

  const { data: jobs = [], isLoading } = useQuery<JobDetail[]>({
    queryKey: ['document-jobs', documentId],
    queryFn: () => getJobs({ resourceType: 'document', resourceId: documentId }),
    enabled: !!documentId,
    refetchInterval: (data) => {
      if (!Array.isArray(data)) {
        return false;
      }
      const active = data.some((job) => job.status === 'PENDING' || job.status === 'RUNNING');
      return active ? 2000 : false;
    },
    initialData: [],
  });

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

  const activeJob = jobs.find((job) => job.status === 'PENDING' || job.status === 'RUNNING');
  const latestJob = jobs[0];

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

  if (latestJob.status === 'FAILED') {
    return (
      <div className="processing-status processing-status--error" role="alert">
        <strong>Background preprocessing failed.</strong>
        <div>{latestJob.detail || 'The extraction service reported an unexpected error.'}</div>
        <small>Last attempt {formatTimestamp(latestJob.updated_at)}</small>
      </div>
    );
  }

  return (
    <div className="processing-status processing-status--success" aria-live="polite">
      <strong>Preprocessing completed.</strong>
      <div>{latestJob.detail || 'The document is ready for PDF annotation.'}</div>
      <small>Finished {formatTimestamp(latestJob.finished_at || latestJob.updated_at)}</small>
    </div>
  );
};

export default DocumentProcessingStatus;
