import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { fetchPdfContent } from '../api/pdfTraining';
import { Button } from './ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from './ui/card';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PdfViewerProps {
  documentId: string | null;
}

const PdfViewer: React.FC<PdfViewerProps> = ({ documentId }) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);

  const { data: pdfUrl, isLoading, isError, error } = useQuery({
    queryKey: ['pdfContent', documentId],
    queryFn: () => {
      if (!documentId) {
        return Promise.reject('No document ID provided');
      }
      return fetchPdfContent(documentId);
    },
    enabled: !!documentId,
  });

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
  };

  if (!documentId) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-lg">PDF preview</CardTitle>
          <CardDescription>Select a document to load the PDF preview.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">PDF preview</CardTitle>
          <CardDescription>Loading PDF…</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            Fetching PDF from the server…
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">PDF preview</CardTitle>
          <CardDescription>Error loading PDF</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">
            {(error as Error).message}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">PDF preview</CardTitle>
        <CardDescription>Navigate between pages using the controls below.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex justify-center overflow-hidden rounded-lg border bg-muted/40">
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={(err) => console.error('Failed to load PDF:', err)}
          >
            <Page pageNumber={pageNumber} width={640} renderTextLayer renderAnnotationLayer />
          </Document>
        </div>
      </CardContent>
      <CardFooter className="items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Page {pageNumber} of {numPages ?? '…'}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPageNumber((prevPage) => Math.max(prevPage - 1, 1))}
            disabled={pageNumber <= 1}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setPageNumber((prevPage) =>
                Math.min(prevPage + 1, numPages ?? prevPage + 1)
              )
            }
            disabled={numPages !== null && pageNumber >= numPages}
          >
            Next
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
};

export default PdfViewer;