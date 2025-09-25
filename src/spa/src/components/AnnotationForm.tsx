import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Annotation,
  AnnotationStatus,
  EntityLocation,
} from '../models';
import {
  AnnotationCreatePayload,
  AnnotationUpdatePayload,
  createAnnotation,
  updateAnnotation,
} from '../api/pdfTraining';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { useToast } from './ui/use-toast';

interface AnnotationFormProps {
  documentId: string;
  open: boolean;
  mode: 'create' | 'edit';
  selection?: { text: string; location: EntityLocation } | null;
  prefill?: { type?: string; value?: string; location?: EntityLocation } | null;
  annotation?: Annotation | null;
  onClose: () => void;
}

const STATUS_OPTIONS: AnnotationStatus[] = ['PENDING', 'IN_REVIEW', 'COMPLETED'];

const AnnotationForm: React.FC<AnnotationFormProps> = ({
  documentId,
  open,
  mode,
  selection,
  prefill,
  annotation,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const initialLocation = useMemo(() => {
    if (selection?.location) {
      return selection.location;
    }
    if (prefill?.location) {
      return prefill.location;
    }
    return annotation?.location ?? null;
  }, [annotation?.location, prefill?.location, selection?.location]);

  const [type, setType] = useState('');
  const [value, setValue] = useState('');
  const [notes, setNotes] = useState('');
  const [reviewer, setReviewer] = useState('');
  const [status, setStatus] = useState<AnnotationStatus>('IN_REVIEW');

  useEffect(() => {
    if (!open) {
      return;
    }
    if (mode === 'edit' && annotation) {
      setType(annotation.type ?? '');
      setValue(annotation.value ?? '');
      setNotes(annotation.notes ?? '');
      setReviewer(annotation.reviewer ?? '');
      setStatus(annotation.status);
      return;
    }
    setType(prefill?.type ?? '');
    setValue(prefill?.value ?? selection?.text ?? '');
    setNotes('');
    setReviewer('');
    setStatus('IN_REVIEW');
  }, [annotation, mode, open, prefill, selection]);

  const createMutation = useMutation({
    mutationFn: async (payload: AnnotationCreatePayload) => {
      await createAnnotation(documentId, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documentDetail', documentId] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({
        title: 'Annotation saved',
        description: 'The annotation has been created successfully.',
      });
      onClose();
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Failed to create annotation.';
      toast({ variant: 'destructive', title: 'Creation failed', description: message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (payload: AnnotationUpdatePayload) => {
      if (!annotation) {
        throw new Error('Missing annotation to update');
      }
      await updateAnnotation(annotation.id, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documentDetail', documentId] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({
        title: 'Annotation updated',
        description: 'Changes have been saved.',
      });
      onClose();
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Failed to update annotation.';
      toast({ variant: 'destructive', title: 'Update failed', description: message });
    },
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!type.trim() || !value.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing information',
        description: 'Type and value are required.',
      });
      return;
    }

    if (mode === 'create') {
      createMutation.mutate({
        type: type.trim(),
        value: value.trim(),
        notes: notes.trim() || undefined,
        reviewer: reviewer.trim() || undefined,
        location: initialLocation ?? undefined,
      });
      return;
    }

    updateMutation.mutate({
      type: type.trim(),
      value: value.trim(),
      notes: notes.trim() || undefined,
      reviewer: reviewer.trim() || undefined,
      status,
      location: initialLocation ?? undefined,
    });
  };

  const actionLabel = mode === 'create' ? 'Create annotation' : 'Save changes';
  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && !isSubmitting && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{mode === 'create' ? 'New annotation' : 'Edit annotation'}</DialogTitle>
          <DialogDescription>
            Provide the details below. Location is captured automatically from your selection.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground" htmlFor="annotation-type">
              Type
            </label>
            <Input
              id="annotation-type"
              value={type}
              onChange={(event) => setType(event.target.value)}
              placeholder="e.g. Amount"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground" htmlFor="annotation-value">
              Value
            </label>
            <textarea
              id="annotation-value"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Captured text from the PDF"
              required
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground" htmlFor="annotation-notes">
                Notes
              </label>
              <textarea
                id="annotation-notes"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground" htmlFor="annotation-reviewer">
                Reviewer
              </label>
              <Input
                id="annotation-reviewer"
                value={reviewer}
                onChange={(event) => setReviewer(event.target.value)}
                placeholder="Reviewer name"
              />
              {mode === 'edit' && (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-muted-foreground" htmlFor="annotation-status">
                    Status
                  </label>
                  <select
                    id="annotation-status"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={status}
                    onChange={(event) => setStatus(event.target.value as AnnotationStatus)}
                  >
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option.replace('_', ' ')}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>

          {initialLocation && (
            <div className="rounded-md border border-dashed bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
              Page {initialLocation.page_num} — bbox {initialLocation.bbox.map((coord) => coord.toFixed(1)).join(', ')}
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving…' : actionLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default AnnotationForm;
