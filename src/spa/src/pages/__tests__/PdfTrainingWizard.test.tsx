import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';

import PdfTrainingWizard from '../PdfTrainingWizard';
import type { Document } from '../../api/pdfTraining';

const mockDocument: Document = {
  id: 'doc-123',
  filename: 'contract.pdf',
  status: 'completed',
  created_at: '2024-01-01T00:00:00Z'
};

vi.mock('../../components/DocumentTable', () => ({
  default: ({ onSelectDocument }: { onSelectDocument: (doc: Document) => void }) => (
    <button type="button" onClick={() => onSelectDocument(mockDocument)}>
      Select Document
    </button>
  )
}));

vi.mock('../../components/TrainingHistory', () => ({
  default: () => <div>TrainingHistory</div>
}));

vi.mock('../../components/AnnotationCard', () => ({
  default: () => <div>AnnotationCard</div>
}));

vi.mock('../../components/WarningsPanel', () => ({
  default: () => <div>WarningsPanel</div>
}));

vi.mock('../../components/PdfViewer', () => ({
  default: ({ documentId }: { documentId: string | null }) => (
    <div data-testid="pdf-viewer-prop">{documentId ?? 'none'}</div>
  )
}));

describe('PdfTrainingWizard integration', () => {
  it('passes the selected document id to the PdfViewer', () => {
    render(<PdfTrainingWizard />);

    expect(screen.getByTestId('pdf-viewer-prop')).toHaveTextContent('none');

    fireEvent.click(screen.getByText('Select Document'));

    expect(screen.getByTestId('pdf-viewer-prop')).toHaveTextContent('doc-123');
  });
});
