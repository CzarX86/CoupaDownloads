import React from 'react';

interface WarningsPanelProps {
  warnings: string[];
}

const WarningsPanel: React.FC<WarningsPanelProps> = ({ warnings }) => {
  if (warnings.length === 0) {
    return null;
  }

  return (
    <div style={{ border: '1px solid orange', padding: '10px', margin: '10px' }}>
      <h3>Warnings</h3>
      <ul>
        {warnings.map((warning, index) => (
          <li key={index}>{warning}</li>
        ))}
      </ul>
    </div>
  );
};

export default WarningsPanel;