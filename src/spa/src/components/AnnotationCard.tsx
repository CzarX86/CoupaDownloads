import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Annotation } from '../models';
import {
  deleteAnnotation,
  sendModelFeedback,
} from '../api/pdfTraining';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from './ui/card';
import { Button } from './ui/button';
import { useToast } from './ui/use-toast';
import { cn } from '../lib/utils';

interface AnnotationCardProps {
  doc: { id: string; filename: string } | null;
  annotations: Annotation[];
  onCreateAnnotation: () => void;
  onEditAnnotation: (annotation: Annotation) => void;
}

const statusStyles: Record<Annotation['status'], string> = {
  PENDING: 'bg-amber-100 text-amber-900 dark:bg-amber-400/20 dark:text-amber-100',
  IN_REVIEW: 'bg-blue-100 text-blue-900 dark:bg-blue-400/20 dark:text-blue-100',
  COMPLETED: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-400/20 dark:text-emerald-100',
};

const AnnotationCard: React.FC<AnnotationCardProps> = ({
  doc,
  annotations,
  onCreateAnnotation,
  onEditAnnotation,
}) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const deleteMutation = useMutation({
    mutationFn: async (annotationId: string) => {
      await deleteAnnotation(annotationId);
    },
    onSuccess: () => {
      if (doc) {
        queryClient.invalidateQueries({ queryKey: ['documentDetail', doc.id] });
      }
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({
        title: 'Annotation removed',
        description: 'The annotation has been deleted.',
      });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Failed to delete annotation.';
      toast({ variant: 'destructive', title: 'Deletion failed', description: message });
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: async (documentId: string) => {
      const response = await sendModelFeedback(documentId);
      return response;
    },
    onSuccess: (response) => {
      toast({
        title: 'Feedback queued',
        description: `Job ${response.job_id} started to train the model.`,
      });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Failed to trigger model feedback.';
      toast({ variant: 'destructive', title: 'Feedback failed', description: message });
    },
  });

  if (!doc) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-lg">Awaiting document</CardTitle>
          <CardDescription>Select a document on the left to review annotations.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const handleDelete = (annotation: Annotation) => {
    deleteMutation.mutate(annotation.id);
  };

  const handleFeedback = () => {
    if (!doc) {
      return;
    }
    feedbackMutation.mutate(doc.id);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Annotations</CardTitle>
        <CardDescription>
          Manage annotations for <strong>{doc.filename}</strong> and send them for model feedback.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={onCreateAnnotation}>
            New annotation
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleFeedback}
            disabled={feedbackMutation.isPending}
          >
            {feedbackMutation.isPending ? 'Sending…' : 'Send feedback'}
          </Button>
        </div>

        {annotations.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No annotations captured yet. Select text in the PDF preview to create one.
          </p>
        ) : (
          <ul className="space-y-3">
            {annotations.map((annotation) => (
              <li
                key={annotation.id}
                className="flex flex-col gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex flex-col">
                    <span className="font-medium text-foreground">{annotation.type ?? 'Annotation'}</span>
                    <span className="text-muted-foreground">{annotation.value ?? '—'}</span>
                  </div>
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold',
                      statusStyles[annotation.status],
                    )}
                  >
                    {annotation.status.replace('_', ' ')}
                  </span>
                </div>
                {annotation.notes && (
                  <p className="text-xs text-muted-foreground">{annotation.notes}</p>
                )}
                <div className="flex items-center justify-end gap-2">
                  <Button size="xs" variant="outline" onClick={() => onEditAnnotation(annotation)}>
                    Edit
                  </Button>
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => handleDelete(annotation)}
                    disabled={deleteMutation.isPending}
                  >
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
      <CardFooter className="justify-end text-xs text-muted-foreground">
        {annotations.length > 0
          ? `${annotations.length} annotation${annotations.length === 1 ? '' : 's'} tracked`
          : 'No annotations yet'}
      </CardFooter>
    </Card>
  );
};

export default AnnotationCard;
