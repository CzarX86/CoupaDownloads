import axios from 'axios';

const API_BASE_URL = '/api/pdf-training';

export interface Document {
  id: number;
  filename: string;
  status: 'new' | 'extracted' | 'reviewing' | 'completed';
  created_at: string;
}

export interface TrainingRun {
  id: number;
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

export const getJobs = async (): Promise<Job[]> => {
    const response = await axios.get(`${API_BASE_URL}/jobs`);
    return response.data;
};

export const submitAnnotation = async (documentId: number, annotationData: unknown): Promise<void> => {
    await axios.post(`${API_BASE_URL}/documents/${documentId}/annotations`, annotationData);
};

export const fetchPdfContent = async (documentId: string): Promise<string> => {
  const response = await axios.get(`${API_BASE_URL}/documents/${documentId}/content`, {
    responseType: 'blob', // Important: responseType must be 'blob' for file downloads
  });
  return URL.createObjectURL(response.data); // Return a URL to the blob
};