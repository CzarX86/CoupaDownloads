
import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { submitAnnotation, Document } from '../api/pdfTraining';

interface AnnotationCardProps {
  doc: Document | null;
}

const AnnotationCard: React.FC<AnnotationCardProps> = ({ doc }) => {
  const queryClient = useQueryClient();
  const [annotationFile, setAnnotationFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: (annotationData: unknown) => {
        if (!doc) return Promise.reject('No document selected');
        return submitAnnotation(doc.id, annotationData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setAnnotationFile(event.target.files?.[0] || null);
  };

  const handleSubmit = () => {
    if (annotationFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result;
        if (typeof content === 'string') {
            try {
                const jsonData = JSON.parse(content);
                mutation.mutate(jsonData);
            } catch (error) {
                console.error('Error parsing JSON file', error);
                // Handle error appropriately in the UI
            }
        }
      };
      reader.readAsText(annotationFile);
    }
  };

  if (!doc) {
    return <div>Select a document to see details.</div>;
  }

  return (
    <div>
      <h3>Reviewing: {doc.filename}</h3>
      <p>Upload annotation export JSON:</p>
      <input type="file" accept=".json" onChange={handleFileChange} />
      <button onClick={handleSubmit} disabled={!annotationFile || mutation.isPending}>
        {mutation.isPending ? 'Submitting...' : 'Submit Annotation'}
      </button>
      {mutation.isError && (
        <div style={{ color: 'red' }}>
          An error occurred: {(mutation.error as Error).message}
        </div>
      )}
    </div>
  );
};

export default AnnotationCard;
