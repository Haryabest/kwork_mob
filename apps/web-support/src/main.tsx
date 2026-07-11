import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import TicketsPage from './pages/TicketsPage';
import TicketDetailPage from './pages/TicketDetailPage';
import FaqEditorPage from './pages/FaqEditorPage';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<TicketsPage />} />
        <Route path="/tickets/:id" element={<TicketDetailPage />} />
        <Route path="/faq" element={<FaqEditorPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
