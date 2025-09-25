export interface EntityLocation {
  page_num: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
}

export interface Entity {
  type: string;
  value: string;
  location?: EntityLocation;
}

export type AnnotationStatus = 'PENDING' | 'IN_REVIEW' | 'COMPLETED';

export interface Annotation {
  id: string;
  document_id: string;
  type?: string | null;
  value?: string | null;
  location?: EntityLocation;
  reviewer?: string | null;
  notes?: string | null;
  status: AnnotationStatus;
  created_at: string;
  updated_at: string;
}
