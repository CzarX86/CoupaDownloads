import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  getLLMSupport,
  JobDetail,
  JobResponse,
  LLMSupportPayload,
  startLLMSupport,
} from '../api/pdfTraining';
import { useJobDetailPolling } from '../hooks/useJobPolling';

interface LLMSupportPanelProps {
  documentId: string | null;
}

const renderJobStatus = (job: JobDetail | null | undefined) => {
  if (!job) {
    return null;
  }
  if (job.status === 'FAILED') {
    return (
      <div className="llm-support__status llm-support__status--error" role="alert" data-testid="llm-support-status-error">
        <strong>LLM helper failed.</strong>
        <div>{job.detail ?? 'Check backend logs for details.'}</div>
      </div>
    );
  }
  if (job.status === 'PENDING' || job.status === 'RUNNING') {
    return (
      <div className="llm-support__status llm-support__status--active" aria-live="polite" data-testid="llm-support-status-running">
        <span className="processing-status__spinner" aria-hidden="true" />
        <div>
          <strong>Generating LLM suggestions…</strong>
          <div>{job.detail ?? 'The helper is reviewing the latest predictions.'}</div>
        </div>
      </div>
    );
  }
  return null;
};

const LLMSupportPanel: React.FC<LLMSupportPanelProps> = ({ documentId }) => {
  const queryClient = useQueryClient();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const supportQuery = useQuery<LLMSupportPayload>({
    queryKey: ['llm-support', documentId],
    queryFn: () => getLLMSupport(documentId as string),
    enabled: Boolean(documentId),
    staleTime: 1000 * 30,
  });

  const jobQuery = useJobDetailPolling(activeJobId, {
    onSuccess: (job) => {
      if (job.status === 'SUCCEEDED') {
        queryClient.invalidateQueries({ queryKey: ['llm-support', documentId] });
        setActiveJobId(null);
      }
      if (job.status === 'FAILED') {
        setActiveJobId(null);
      }
    },
  });

  const mutation = useMutation<JobResponse, unknown, void>({
    mutationFn: async () => {
      if (!documentId) {
        throw new Error('Document not selected');
      }
      return startLLMSupport(documentId);
    },
    onSuccess: (response) => {
      setActiveJobId(response.job_id);
      queryClient.invalidateQueries({ queryKey: ['llm-support', documentId] });
    },
  });

  if (!documentId) {
    return (
      <section className="llm-support" aria-live="polite">
        <header>
          <h3>LLM Helper</h3>
        </header>
        <p className="llm-support__placeholder">Select a document to request LLM-backed suggestions.</p>
      </section>
    );
  }

  const isRunning = Boolean(activeJobId) && (jobQuery.data?.status === 'PENDING' || jobQuery.data?.status === 'RUNNING');
  const support = supportQuery.data;

  return (
    <section className="llm-support" aria-live="polite">
      <header>
        <div>
          <h3>LLM Helper</h3>
          <p className="llm-support__caption">Generate optional LLM critiques for the selected document.</p>
        </div>
        <button
          type="button"
          className="llm-support__action"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || isRunning}
        >
          {mutation.isPending || isRunning ? 'Requesting…' : 'Generate suggestions'}
        </button>
      </header>

      {renderJobStatus(jobQuery.data)}

      {supportQuery.isLoading && !support ? (
        <p className="llm-support__placeholder" data-testid="llm-support-loading">Fetching the latest LLM feedback…</p>
      ) : null}

      {supportQuery.isError ? (
        <p className="llm-support__status llm-support__status--error" role="alert">
          {(supportQuery.error as Error)?.message ?? 'Failed to fetch LLM support payload.'}
        </p>
      ) : null}

      {support && support.rows.length === 0 ? (
        <p className="llm-support__placeholder">No suggestions recorded yet. Run the helper to populate this panel.</p>
      ) : null}

      {support && support.rows.length > 0 ? (
        <div className="llm-support__results">
          <div className="llm-support__meta">
            <span>Model: {support.model}</span>
            <span>Provider: {support.provider}</span>
            <span>Mode: {support.dry_run ? 'Dry-run' : 'Live'}</span>
          </div>
          <ul>
            {support.rows.map((row) => (
              <li key={row.row_id} className="llm-support__row">
                <header>
                  <strong>Row {row.row_id}</strong>
                  {typeof row.cost_usd === 'number' ? (
                    <span className="llm-support__cost">${row.cost_usd.toFixed(6)}</span>
                  ) : null}
                </header>
                <ul className="llm-support__suggestions">
                  {row.suggestions.map((suggestion) => (
                    <li key={`${row.row_id}-${suggestion.field}`}>
                      <strong>{suggestion.field}</strong>
                      <span className={`llm-support__decision llm-support__decision--${suggestion.decision}`}>
                        {suggestion.decision}
                      </span>
                      {suggestion.suggested ? <span className="llm-support__value">{suggestion.suggested}</span> : null}
                      {suggestion.rationale ? <span className="llm-support__rationale">{suggestion.rationale}</span> : null}
                      {typeof suggestion.confidence === 'number' ? (
                        <span className="llm-support__confidence">Confidence: {Math.round(suggestion.confidence * 100)}%</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
};

export default LLMSupportPanel;
