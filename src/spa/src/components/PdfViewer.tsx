import React, { useCallback, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { fetchEntities, fetchPdfContent } from '../api/pdfTraining';
import { Annotation, Entity, EntityLocation } from '../models';
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
  annotations?: Annotation[];
  onCreateFromSelection?: (data: { text: string; location: EntityLocation }) => void;
  onEntityClick?: (entity: Entity) => void;
  onAnnotationClick?: (annotation: Annotation) => void;
}

type PageMetrics = Record<number, { width: number; height: number; originalWidth: number; originalHeight: number }>;

const PdfViewer: React.FC<PdfViewerProps> = ({
  documentId,
  annotations,
  onCreateFromSelection,
  onEntityClick,
  onAnnotationClick,
}) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [pageMetrics, setPageMetrics] = useState<PageMetrics>({});
  const pageContainerRef = useRef<HTMLDivElement | null>(null);

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

  const { data: entities } = useQuery({
    queryKey: ['documentEntities', documentId],
    queryFn: () => {
      if (!documentId) {
        return Promise.reject('No document ID provided');
      }
      return fetchEntities(documentId);
    },
    enabled: !!documentId,
  });

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
    setPageMetrics({});
  };

  const handlePageRender = useCallback((page: pdfjs.PDFPageProxy) => {
    const originalWidth = page.view[2] - page.view[0];
    const originalHeight = page.view[3] - page.view[1];
    const renderedWidth = 640;
    const renderedHeight = (originalHeight / originalWidth) * renderedWidth;
    setPageMetrics((prev) => ({
      ...prev,
      [page.pageNumber]: {
        width: renderedWidth,
        height: renderedHeight,
        originalWidth,
        originalHeight,
      },
    }));
  }, []);

  const convertBoundingBox = useCallback(
    (bbox: [number, number, number, number], currentPage: number) => {
      const metrics = pageMetrics[currentPage];
      if (!metrics) {
        return null;
      }

      const { width, height, originalWidth, originalHeight } = metrics;
      const normalise = (value: number, dimension: number, originalDimension: number) => {
        if (value <= 1) {
          return value * dimension;
        }
        if (value <= 100) {
          return (value / 100) * dimension;
        }
        if (originalDimension > 0) {
          return (value / originalDimension) * dimension;
        }
        return (value / 100) * dimension;
      };

      const left = normalise(bbox[0], width, originalWidth);
      const top = normalise(bbox[1], height, originalHeight);
      const right = normalise(bbox[2], width, originalWidth);
      const bottom = normalise(bbox[3], height, originalHeight);

      return {
        left,
        top,
        width: Math.max(right - left, 2),
        height: Math.max(bottom - top, 2),
      };
    },
    [pageMetrics],
  );

  const overlayElements = useMemo(() => {
    if (!entities && !annotations) {
      return {} as Record<number, React.ReactNode[]>;
    }
    const grouped: Record<number, React.ReactNode[]> = {};

    const pushOverlay = (
      page: number,
      key: string,
      rect: { left: number; top: number; width: number; height: number },
      className: string,
      label: string,
      onClick?: () => void,
    ) => {
      if (!grouped[page]) {
        grouped[page] = [];
      }
      grouped[page].push(
        <div
          key={key}
          className={`absolute rounded border ${className}`}
          style={{
            left: rect.left,
            top: rect.top,
            width: rect.width,
            height: rect.height,
          }}
          title={label}
          onClick={(event) => {
            event.stopPropagation();
            onClick?.();
          }}
        />,
      );
    };

    entities?.forEach((entity, index) => {
      if (!entity.location) {
        return;
      }
      const rect = convertBoundingBox(entity.location.bbox, entity.location.page_num);
      if (!rect) {
        return;
      }
      pushOverlay(
        entity.location.page_num,
        `entity-${index}`,
        rect,
        'border-amber-500 bg-amber-400/30 pointer-events-auto',
        `${entity.type}: ${entity.value}`,
        () => onEntityClick?.(entity),
      );
    });

    annotations?.forEach((annotation) => {
      if (!annotation.location) {
        return;
      }
      const rect = convertBoundingBox(annotation.location.bbox, annotation.location.page_num);
      if (!rect) {
        return;
      }
      pushOverlay(
        annotation.location.page_num,
        `annotation-${annotation.id}`,
        rect,
        'border-emerald-500 bg-emerald-400/30 pointer-events-auto',
        `${annotation.type ?? 'Annotation'}: ${annotation.value ?? ''}`,
        () => onAnnotationClick?.(annotation),
      );
    });

    return grouped;
  }, [annotations, convertBoundingBox, entities, onAnnotationClick, onEntityClick]);

  const handleMouseUp = useCallback(() => {
    if (!onCreateFromSelection) {
      return;
    }
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) {
      return;
    }
    const text = selection.toString().trim();
    if (!text) {
      selection.removeAllRanges();
      return;
    }
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const containerRect = pageContainerRef.current?.getBoundingClientRect();
    if (!containerRect || rect.width === 0 || rect.height === 0) {
      selection.removeAllRanges();
      return;
    }

    const toPercent = (value: number, total: number) => Math.min(Math.max((value / total) * 100, 0), 100);
    const left = toPercent(rect.left - containerRect.left, containerRect.width);
    const top = toPercent(rect.top - containerRect.top, containerRect.height);
    const right = toPercent(rect.right - containerRect.left, containerRect.width);
    const bottom = toPercent(rect.bottom - containerRect.top, containerRect.height);

    onCreateFromSelection({
      text,
      location: {
        page_num: pageNumber,
        bbox: [left, top, right, bottom],
      },
    });
    selection.removeAllRanges();
  }, [onCreateFromSelection, pageNumber]);

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
          <p className="text-sm text-destructive">{(error as Error).message}</p>
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
        <div
          ref={pageContainerRef}
          className="relative flex justify-center overflow-hidden rounded-lg border bg-muted/40"
          onMouseUp={handleMouseUp}
        >
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={(err) => console.error('Failed to load PDF:', err)}
          >
            <div className="relative">
              <Page
                pageNumber={pageNumber}
                width={640}
                renderTextLayer
                renderAnnotationLayer
                onRenderSuccess={handlePageRender}
              />
              <div className="absolute inset-0">
                {overlayElements[pageNumber]?.map((node, index) => (
                  <React.Fragment key={index}>{node}</React.Fragment>
                ))}
              </div>
            </div>
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
                Math.min(prevPage + 1, numPages ?? prevPage + 1),
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
