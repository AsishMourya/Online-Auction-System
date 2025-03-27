import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        {/* Add more routes as you develop additional pages */}
        <Route path="/auctions" element={<div>Auctions Page (Coming Soon)</div>} />
        <Route path="/register" element={<div>Registration Page (Coming Soon)</div>} />
        <Route path="/auction/:id" element={<div>Single Auction Page (Coming Soon)</div>} />
        <Route path="/category/:id" element={<div>Category Page (Coming Soon)</div>} />
        <Route path="*" element={<div>404 Page Not Found</div>} />
      </Routes>
    </Router>
  );
}

export default App;