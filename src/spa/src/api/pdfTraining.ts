import axios from 'axios';
import { Entity } from '../models';

const API_BASE_URL = '/api/pdf-training';

export interface Document {
  id: string;
  filename: string;
  status: 'PENDING' | 'IN_REVIEW' | 'COMPLETED';
  content_type?: string | null;
  size_bytes?: number | null;
  created_at: string;
  updated_at: string;
}

export interface TrainingRun {
  id: string;
  started_at: string;
  status: 'running' | 'completed' | 'failed';
  metrics: Record<string, unknown>;
  artifacts: Record<string, string>;
}

export type JobStatus = 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
export type JobType = 'ANALYSIS' | 'ANNOTATION' | 'TRAINING';

export interface JobDetail {
  id: string;
  job_type: JobType;
  status: JobStatus;
  detail?: string | null;
  payload?: Record<string, unknown> | null;
  resource_type?: string | null;
  resource_id?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  updated_at: string;
}

interface JobListResponse {
  jobs: JobDetail[];
}

export interface JobResponse {
  job_id: string;
  job_type: JobType;
  status: JobStatus;
}

export interface LLMFieldSuggestion {
  field: string;
  decision: string;
  suggested?: string;
  rationale?: string;
  confidence?: number;
}

export interface LLMSupportRow {
  row_id: string;
  suggestions: LLMFieldSuggestion[];
  usage?: Record<string, unknown> | null;
  cost_usd?: number | null;
}

export interface LLMSupportPayload {
  document_id: string;
  generated_at: string;
  provider: string;
  model: string;
  dry_run: boolean;
  fields: string[];
  rows: LLMSupportRow[];
}

interface LLMSupportRequest {
  fields?: string[];
  provider?: string;
  model?: string;
  dry_run?: boolean;
}

export const getDocuments = async (): Promise<Document[]> => {
  const response = await axios.get(`${API_BASE_URL}/documents`);
  return response.data;
};

export const uploadDocument = async (file: File): Promise<Document> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API_BASE_URL}/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getTrainingRuns = async (): Promise<TrainingRun[]> => {
  const response = await axios.get(`${API_BASE_URL}/training-runs`);
  return response.data;
};

export const getJobs = async (params?: { resourceType?: string; resourceId?: string }): Promise<JobDetail[]> => {
  const response = await axios.get<JobListResponse>(`${API_BASE_URL}/jobs`, {
    params: {
      resource_type: params?.resourceType,
      resource_id: params?.resourceId,
    },
  });
  return response.data.jobs;
};

export const submitAnnotation = async (documentId: string, annotationData: unknown): Promise<void> => { // Changed documentId to string
    await axios.post(`${API_BASE_URL}/documents/${documentId}/annotations`, annotationData);
};

export const fetchPdfContent = async (documentId: string): Promise<string> => {
  const response = await axios.get(`${API_BASE_URL}/documents/${documentId}/content`, {
    responseType: 'blob', // Important: responseType must be 'blob' for file downloads
  });
  return URL.createObjectURL(response.data); // Return a URL to the blob
};

export const fetchEntities = async (documentId: string): Promise<Entity[]> => {
  const response = await axios.get(`${API_BASE_URL}/documents/${documentId}/entities`);
  return response.data;
};

export const getJob = async (jobId: string): Promise<JobDetail> => {
  const response = await axios.get<JobDetail>(`${API_BASE_URL}/jobs/${jobId}`);
  return response.data;
};

export const startLLMSupport = async (
  documentId: string,
  payload: LLMSupportRequest = {},
): Promise<JobResponse> => {
  const response = await axios.post(`${API_BASE_URL}/documents/${documentId}/support/llm`, payload);
  return response.data;
};

export const getLLMSupport = async (documentId: string): Promise<LLMSupportPayload> => {
  const response = await axios.get(`${API_BASE_URL}/documents/${documentId}/support/llm`);
  return response.data;
};