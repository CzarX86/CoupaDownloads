import { useQuery } from '@tanstack/react-query';
import { getJob, getJobs, JobDetail } from '../api/pdfTraining';

const ACTIVE_STATUSES: ReadonlySet<JobDetail['status']> = new Set(['PENDING', 'RUNNING']);
const DEFAULT_POLL_INTERVAL = 2000;

const hasActiveJobs = (jobs: JobDetail[] | undefined): boolean =>
  Array.isArray(jobs) && jobs.some((job) => ACTIVE_STATUSES.has(job.status));

export interface DocumentJobPollingResult {
  jobs: JobDetail[];
  activeJob: JobDetail | null;
  latestJob: JobDetail | null;
  isLoading: boolean;
  isFetching: boolean;
}

export const useDocumentJobs = (
  documentId: string | null,
  options?: { pollIntervalMs?: number; enabled?: boolean }
): DocumentJobPollingResult => {
  const pollInterval = options?.pollIntervalMs ?? DEFAULT_POLL_INTERVAL;
  const enabled = options?.enabled ?? Boolean(documentId);
  const query = useQuery<JobDetail[]>({
    queryKey: ['document-jobs', documentId],
    queryFn: () => getJobs({ resourceType: 'document', resourceId: documentId as string }),
    enabled,
    initialData: [],
    refetchInterval: (data) => (hasActiveJobs(data) ? pollInterval : false),
  });

  const jobs = query.data ?? [];
  const activeJob = jobs.find((job) => ACTIVE_STATUSES.has(job.status)) ?? null;
  const latestJob = jobs.length > 0 ? jobs[0] : null;

  return {
    jobs,
    activeJob,
    latestJob,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
  };
};

export interface JobDetailPollingOptions {
  pollIntervalMs?: number;
  onSuccess?: (job: JobDetail) => void;
}

export const useJobDetailPolling = (
  jobId: string | null,
  options?: JobDetailPollingOptions
) => {
  const pollInterval = options?.pollIntervalMs ?? DEFAULT_POLL_INTERVAL;
  return useQuery<JobDetail>({
    queryKey: ['job-detail', jobId],
    queryFn: () => getJob(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (data) => (data && ACTIVE_STATUSES.has(data.status) ? pollInterval : false),
    onSuccess: options?.onSuccess,
  });
};
