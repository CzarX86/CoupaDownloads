import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTrainingRuns, TrainingRun } from '../api/pdfTraining';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from './ui/card';

const statusColor: Record<TrainingRun['status'], string> = {
  running: 'text-amber-600 dark:text-amber-300',
  completed: 'text-emerald-600 dark:text-emerald-300',
  failed: 'text-rose-600 dark:text-rose-300',
};

const TrainingHistory: React.FC = () => {
  const { data: trainingRuns, isLoading } = useQuery({
    queryKey: ['trainingRuns'],
    queryFn: getTrainingRuns,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Training history</CardTitle>
        <CardDescription>Latest fine-tuning attempts and their status.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && (
          <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
            Loading training history…
          </div>
        )}

        {!isLoading && (trainingRuns?.length ?? 0) === 0 && (
          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            No training runs found yet. Upload a document and submit annotations to trigger a retraining job.
          </div>
        )}

        {trainingRuns?.map((run) => (
          <div
            key={run.id}
            className="rounded-lg border bg-muted/30 p-4 text-sm"
          >
            <div className="flex items-center justify-between">
              <p className="font-medium">Run {run.id}</p>
              <span className={`text-xs font-semibold uppercase tracking-wide ${statusColor[run.status]}`}>
                {run.status}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Started {new Date(run.started_at).toLocaleString()}
            </p>
            {Object.keys(run.metrics || {}).length > 0 && (
              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                {Object.entries(run.metrics).slice(0, 4).map(([key, value]) => (
                  <div key={key}>
                    <dt className="font-medium text-foreground">{key}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

export default TrainingHistory;