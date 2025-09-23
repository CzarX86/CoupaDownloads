import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDocuments, uploadDocument, Document } from '../api/pdfTraining';

interface DocumentTableProps {
  onSelectDocument: (doc: Document) => void;
}

const DocumentTable: React.FC<DocumentTableProps> = ({ onSelectDocument }) => {
  const queryClient = useQueryClient();
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: getDocuments,
  });

  const mutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleFileDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      mutation.mutate(file);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      mutation.mutate(file);
    }
  };

  if (isLoading) {
    return <div>Loading documents...</div>;
  }

  return (
    <div className="document-table" onDragOver={(e) => e.preventDefault()} onDrop={handleFileDrop}>
      <h2>Documents</h2>
      <input type="file" onChange={handleFileChange} />
      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Status</th>
            <th>Created At</th>
          </tr>
        </thead>
        <tbody>
          {documents?.map((doc: Document) => (
            <tr key={doc.id} onClick={() => onSelectDocument(doc)}>
              <td>{doc.filename}</td>
              <td>{doc.status}</td>
              <td>{doc.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>Drag and drop a PDF file here to upload.</p>
    </div>
  );
};

export default DocumentTable;