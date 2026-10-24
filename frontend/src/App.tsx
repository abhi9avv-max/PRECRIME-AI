import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { NewInvestigation } from './pages/NewInvestigation';
import { PipelineTrace } from './pages/PipelineTrace';
import { DiagnosisFix } from './pages/DiagnosisFix';
import { RetestReport } from './pages/RetestReport';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<NewInvestigation />} />
        <Route path="/investigations/:id/trace" element={<PipelineTrace />} />
        <Route path="/investigations/:id/diagnosis" element={<DiagnosisFix />} />
        <Route path="/investigations/:id/retest" element={<RetestReport />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
