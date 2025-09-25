import React from 'react';
import { TriangleAlert } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';

interface WarningsPanelProps {
  warnings: string[];
}

const WarningsPanel: React.FC<WarningsPanelProps> = ({ warnings }) => {
  if (warnings.length === 0) {
    return null;
  }

  return (
    <Alert variant="warning" className="border-amber-300 bg-amber-50 dark:bg-amber-500/20">
      <TriangleAlert className="h-4 w-4" />
      <div>
        <AlertTitle>Warnings</AlertTitle>
        <AlertDescription>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm">
            {warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </AlertDescription>
      </div>
    </Alert>
  );
};

export default WarningsPanel;