import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import DocumentTable from '../components/DocumentTable';
import TrainingHistory from '../components/TrainingHistory';
import AnnotationCard from '../components/AnnotationCard';
import WarningsPanel from '../components/WarningsPanel';
import PdfViewer from '../components/PdfViewer';
import AnnotationForm from '../components/AnnotationForm';
import { Document, getDocumentDetail } from '../api/pdfTraining';
import { Annotation, EntityLocation } from '../models';

interface SelectionContext {
  text: string;
  location: EntityLocation;
}

const PdfTrainingWizard: React.FC = () => {
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [warnings] = useState<string[]>([]);

  const [isFormOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [selection, setSelection] = useState<SelectionContext | null>(null);
  const [prefill, setPrefill] = useState<{ type?: string; value?: string; location?: EntityLocation } | null>(null);
  const [editingAnnotation, setEditingAnnotation] = useState<Annotation | null>(null);

  const handleSelectDocument = (doc: Document) => {
    setSelectedDoc(doc);
    setFormOpen(false);
    setSelection(null);
    setPrefill(null);
    setEditingAnnotation(null);
  };

  const documentDetailQuery = useQuery({
    queryKey: ['documentDetail', selectedDoc?.id],
    queryFn: () => {
      if (!selectedDoc) {
        return Promise.reject('No document selected');
      }
      return getDocumentDetail(selectedDoc.id);
    },
    enabled: !!selectedDoc?.id,
  });

  const annotations = useMemo(() => documentDetailQuery.data?.annotations ?? [], [documentDetailQuery.data]);

  const openCreateForm = (initial?: { type?: string; value?: string; location?: EntityLocation } | null) => {
    setFormMode('create');
    setSelection(initial?.value && initial.location ? { text: initial.value, location: initial.location } : null);
    setPrefill(initial ?? null);
    setEditingAnnotation(null);
    setFormOpen(true);
  };

  const openEditForm = (annotation: Annotation) => {
    setFormMode('edit');
    setEditingAnnotation(annotation);
    setPrefill({
      type: annotation.type ?? undefined,
      value: annotation.value ?? undefined,
      location: annotation.location ?? undefined,
    });
    setSelection(null);
    setFormOpen(true);
  };

  const handleSelection = (context: SelectionContext) => {
    openCreateForm({ value: context.text, location: context.location });
  };

  const handleEntityClick = (entity: { type: string; value: string; location?: EntityLocation }) => {
    openCreateForm({ type: entity.type, value: entity.value, location: entity.location });
  };

  const handleAnnotationClick = (annotation: Annotation) => {
    openEditForm(annotation);
  };

  const closeForm = () => {
    setFormOpen(false);
    setSelection(null);
    setPrefill(null);
    setEditingAnnotation(null);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
      <div className="space-y-6">
        <WarningsPanel warnings={warnings} />
        <DocumentTable
          onSelectDocument={handleSelectDocument}
          selectedDocumentId={selectedDoc?.id}
        />
        <PdfViewer
          documentId={selectedDoc?.id ?? null}
          annotations={annotations}
          onCreateFromSelection={handleSelection}
          onEntityClick={handleEntityClick}
          onAnnotationClick={handleAnnotationClick}
        />
      </div>
      <div className="space-y-6">
        <AnnotationCard
          doc={selectedDoc}
          annotations={annotations}
          onCreateAnnotation={() => openCreateForm(null)}
          onEditAnnotation={openEditForm}
        />
        <TrainingHistory />
      </div>

      {selectedDoc && (
        <AnnotationForm
          documentId={selectedDoc.id}
          open={isFormOpen}
          mode={formMode}
          selection={selection}
          prefill={prefill}
          annotation={editingAnnotation}
          onClose={closeForm}
        />
      )}
    </div>
  );
};

export default PdfTrainingWizard;
