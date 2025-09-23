import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTrainingRuns, TrainingRun } from '../api/pdfTraining';

const TrainingHistory: React.FC = () => {
  const { data: trainingRuns, isLoading } = useQuery({
    queryKey: ['trainingRuns'],
    queryFn: getTrainingRuns,
  });

  if (isLoading) {
    return <div>Loading training history...</div>;
  }

  return (
    <div>
      <h2>Training History</h2>
      {trainingRuns?.map((run: TrainingRun) => (
        <div key={run.id} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
          <p><strong>Run ID:</strong> {run.id}</p>
          <p><strong>Started At:</strong> {run.started_at}</p>
          <p><strong>Status:</strong> {run.status}</p>
          {/* Render metrics and artifacts as needed */}
        </div>
      ))}
    </div>
  );
};

export default TrainingHistory;