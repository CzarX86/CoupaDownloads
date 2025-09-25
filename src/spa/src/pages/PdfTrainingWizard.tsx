import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DocumentTable from '../components/DocumentTable';
import TrainingHistory from '../components/TrainingHistory';
import AnnotationCard from '../components/AnnotationCard';
import WarningsPanel from '../components/WarningsPanel';
import PdfViewer from '../components/PdfViewer';
import DocumentProcessingStatus from '../components/DocumentProcessingStatus';
import LLMSupportPanel from '../components/LLMSupportPanel';
import { Document } from '../api/pdfTraining';

const queryClient = new QueryClient();

const PdfTrainingWizard: React.FC = () => {
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [warnings] = useState<string[]>([]);

  // This would be passed to the DocumentTable and updated on row selection
  const handleSelectDocument = (doc: Document) => {
    setSelectedDoc(doc);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="wizard-dashboard">
        <div>
          <WarningsPanel warnings={warnings} />
          <DocumentTable onSelectDocument={handleSelectDocument} />
          <DocumentProcessingStatus documentId={selectedDoc ? String(selectedDoc.id) : null} />
          <PdfViewer documentId={selectedDoc ? String(selectedDoc.id) : null} />
        </div>
        <div>
          <AnnotationCard doc={selectedDoc} />
          <LLMSupportPanel documentId={selectedDoc ? String(selectedDoc.id) : null} />
          <TrainingHistory />
        </div>
      </div>
    </QueryClientProvider>
  );
};

export default PdfTrainingWizard;