import axios from 'axios';
import { Annotation, AnnotationStatus, Entity, EntityLocation } from '../models';

const API_BASE_URL = '/api/pdf-training';

export interface Document {
  id: string; // Changed from number to string to match backend
  filename: string;
  content_type?: string | null;
  size_bytes?: number | null;
  status: AnnotationStatus;
  created_at: string;
  updated_at: string;
}

interface DocumentListResponse {
  items: Document[];
}

export interface TrainingRun {
  id: string; // Changed from number to string to match backend
  started_at: string;
  status: 'running' | 'completed' | 'failed';
  metrics: Record<string, unknown>;
  artifacts: Record<string, string>;
}

export interface Job {
    id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    type: 'extraction' | 'training';
}

export interface DocumentVersion {
  id: string;
  ordinal: number;
  source_storage_path: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail {
  document: Document;
  versions: DocumentVersion[];
  annotations: Annotation[];
}

export interface AnnotationCreatePayload {
  type: string;
  value: string;
  notes?: string;
  reviewer?: string;
  location?: EntityLocation;
}

export interface AnnotationUpdatePayload {
  type?: string;
  value?: string;
  notes?: string;
  reviewer?: string;
  status?: AnnotationStatus;
  location?: EntityLocation;
}

export interface JobResponse {
  job_id: string;
  job_type: 'ANALYSIS' | 'TRAINING';
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
}

export const getDocuments = async (): Promise<Document[]> => {
  const response = await axios.get<DocumentListResponse>(`${API_BASE_URL}/documents`);
  return response.data.items;
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

export const getJobs = async (): Promise<Job[]> => {
    const response = await axios.get(`${API_BASE_URL}/jobs`);
    return response.data;
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

export const getDocumentDetail = async (documentId: string): Promise<DocumentDetail> => {
  const response = await axios.get(`${API_BASE_URL}/documents/${documentId}`);
  return response.data;
};

export const createAnnotation = async (
  documentId: string,
  payload: AnnotationCreatePayload,
): Promise<Annotation> => {
  const response = await axios.post(
    `${API_BASE_URL}/documents/${documentId}/annotations`,
    payload,
  );
  return response.data;
};

export const updateAnnotation = async (
  annotationId: string,
  payload: AnnotationUpdatePayload,
): Promise<Annotation> => {
  const response = await axios.put(
    `${API_BASE_URL}/annotations/${annotationId}`,
    payload,
  );
  return response.data;
};

export const deleteAnnotation = async (annotationId: string): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/annotations/${annotationId}`);
};

export const sendModelFeedback = async (documentId: string): Promise<JobResponse> => {
  const response = await axios.post(`${API_BASE_URL}/documents/${documentId}/feedback`, {});
  return response.data;
};