import axios from 'axios';
import { Entity } from '../models'; // Import Entity interface

const API_BASE_URL = '/api/pdf-training';

export interface Document {
  id: string; // Changed from number to string to match backend
  filename: string;
  status: 'new' | 'extracted' | 'reviewing' | 'completed';
  created_at: string;
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