import React, { useState } from 'react';
import DocumentTable from '../components/DocumentTable';
import TrainingHistory from '../components/TrainingHistory';
import AnnotationCard from '../components/AnnotationCard';
import WarningsPanel from '../components/WarningsPanel';
import PdfViewer from '../components/PdfViewer';
import { Document } from '../api/pdfTraining';

const PdfTrainingWizard: React.FC = () => {
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [warnings] = useState<string[]>([]);

  const handleSelectDocument = (doc: Document) => {
    setSelectedDoc(doc);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
      <div className="space-y-6">
        <WarningsPanel warnings={warnings} />
        <DocumentTable
          onSelectDocument={handleSelectDocument}
          selectedDocumentId={selectedDoc?.id}
        />
        <PdfViewer documentId={selectedDoc?.id ?? null} />
      </div>
      <div className="space-y-6">
        <AnnotationCard doc={selectedDoc} />
        <TrainingHistory />
      </div>
    </div>
  );
};

export default PdfTrainingWizard;