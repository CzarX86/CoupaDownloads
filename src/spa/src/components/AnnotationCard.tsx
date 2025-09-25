
import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { submitAnnotation, Document } from '../api/pdfTraining';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { useToast } from './ui/use-toast';

interface AnnotationCardProps {
  doc: Document | null;
}

const AnnotationCard: React.FC<AnnotationCardProps> = ({ doc }) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [annotationFile, setAnnotationFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: async (annotationData: unknown) => {
      if (!doc) {
        throw new Error('No document selected');
      }
      await submitAnnotation(doc.id, annotationData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({
        title: 'Annotation submitted',
        description: 'Training data has been queued for review.',
      });
      setAnnotationFile(null);
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'Unexpected error submitting annotation.';
      toast({
        variant: 'destructive',
        title: 'Submission failed',
        description: message,
      });
    },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setAnnotationFile(event.target.files?.[0] || null);
  };

  const handleSubmit = () => {
    if (!annotationFile) {
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result;
      if (typeof content !== 'string') {
        toast({
          variant: 'destructive',
          title: 'Invalid file',
          description: 'The selected file could not be read as text.',
        });
        return;
      }

      try {
        const jsonData = JSON.parse(content);
        mutation.mutate(jsonData);
      } catch (error) {
        toast({
          variant: 'destructive',
          title: 'Invalid JSON',
          description: 'Ensure the file is a valid annotation export.',
        });
      }
    };
    reader.readAsText(annotationFile);
  };

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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Reviewing: {doc.filename}</CardTitle>
        <CardDescription>Upload a JSON export to update annotations.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Input type="file" accept="application/json" onChange={handleFileChange} />
        <p className="text-sm text-muted-foreground">
          The assistant will merge annotations into the training dataset immediately after upload.
        </p>
      </CardContent>
      <CardFooter className="justify-end">
        <Button
          onClick={handleSubmit}
          disabled={!annotationFile || mutation.isPending}
        >
          {mutation.isPending ? 'Submitting…' : 'Submit annotation'}
        </Button>
      </CardFooter>
    </Card>
  );
};

export default AnnotationCard;
