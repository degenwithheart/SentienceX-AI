"use client";
import * as React from 'react';

const ThreatPanel = ({ threat }: { threat?: any }) => {
  return (
    <div>
      <h4 className="text-lg font-semibold text-red-300 mb-3">Threat Overview</h4>
      {threat ? (
        <pre className="text-xs text-gray-200 bg-black/20 p-3 rounded-md">{JSON.stringify(threat, null, 2)}</pre>
      ) : (
        <div className="text-sm text-gray-400">No threat data yet.</div>
      )}
    </div>
  );
};

export default ThreatPanel;