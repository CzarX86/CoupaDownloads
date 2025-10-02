import React, { useMemo, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDocuments, uploadDocument, Document } from '../api/pdfTraining';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from './ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { useToast } from './ui/use-toast';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { cn } from '../lib/utils';

interface DocumentTableProps {
  onSelectDocument: (doc: Document) => void;
  selectedDocumentId?: string | null;
}

const statusLabels: Record<Document['status'], string> = {
  PENDING: 'Pending',
  IN_REVIEW: 'In review',
  COMPLETED: 'Completed',
};

const statusStyles: Record<Document['status'], string> = {
  PENDING: 'bg-blue-100 text-blue-800 dark:bg-blue-400/20 dark:text-blue-200',
  IN_REVIEW: 'bg-amber-100 text-amber-900 dark:bg-amber-400/20 dark:text-amber-100',
  COMPLETED: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-400/20 dark:text-emerald-100',
};

const formatDate = (date: string) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(date));

const DocumentTable: React.FC<DocumentTableProps> = ({
  onSelectDocument,
  selectedDocumentId,
}) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: getDocuments,
  });

  const mutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({
        title: 'Upload complete',
        description: `${doc.filename} is ready for analysis.`,
      });
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'Unexpected error during upload.';
      toast({
        variant: 'destructive',
        title: 'Upload failed',
        description: message,
      });
    },
  });

  const handleFileUpload = (file: File | undefined) => {
    if (!file) {
      return;
    }
    mutation.mutate(file);
  };

  const handleFileDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    handleFileUpload(file);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    handleFileUpload(file);
    event.target.value = '';
  };

  const hasDocuments = (documents?.length ?? 0) > 0;

  const uploadHint = useMemo(
    () => (
      <ul className="list-disc space-y-1 pl-4 text-left text-sm text-muted-foreground">
        <li>Only PDF files are accepted at the moment.</li>
        <li>Uploads larger than 20MB may take a few seconds to appear.</li>
        <li>Documents move from <strong>Pending</strong> to <strong>Completed</strong> once retraining finishes.</li>
      </ul>
    ),
    []
  );

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle className="text-xl">Documents</CardTitle>
          <CardDescription>Select a document to review annotations or preview the PDF.</CardDescription>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" className="w-full sm:w-auto">
              Upload tips
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload guidelines</DialogTitle>
              <DialogDescription>
                Keep uploads lightweight to get the fastest feedback from the assistant.
              </DialogDescription>
            </DialogHeader>
            {uploadHint}
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          onDragOver={(event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'copy';
          }}
          onDragEnter={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleFileDrop}
          className={cn(
            'flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-6 text-center transition-colors',
            isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/40 hover:border-primary/60'
          )}
        >
          <p className="text-sm font-medium">Drag and drop a PDF or use the upload button.</p>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Uploading…' : 'Select PDF'}
          </Button>
          <Input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Filename</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading && (
                <TableRow>
                  <TableCell colSpan={3}>
                    <div className="flex h-16 items-center justify-center text-sm text-muted-foreground">
                      Loading documents…
                    </div>
                  </TableCell>
                </TableRow>
              )}

              {!isLoading && !hasDocuments && (
                <TableRow>
                  <TableCell colSpan={3}>
                    <div className="flex h-16 items-center justify-center text-sm text-muted-foreground">
                      No documents uploaded yet.
                    </div>
                  </TableCell>
                </TableRow>
              )}

              {documents?.map((doc) => (
                <TableRow
                  key={doc.id}
                  data-state={selectedDocumentId === doc.id ? 'selected' : undefined}
                  className="cursor-pointer"
                  onClick={() => onSelectDocument(doc)}
                >
                  <TableCell className="font-medium">{doc.filename}</TableCell>
                  <TableCell>
                    <span
                      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${statusStyles[doc.status]}`}
                    >
                      {statusLabels[doc.status]}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(doc.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
};

export default DocumentTable;