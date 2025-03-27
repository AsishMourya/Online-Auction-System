import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import AuctionsPage from './pages/AuctionsPage';
import AuctionDetailPage from './pages/AuctionDetailPage';
import AuthPage from './pages/AuthPage';
import ProfilePage from './pages/ProfilePage';
import CreateAuctionPage from './pages/CreateAuctionPage';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        {/* Home and Browse */}
        <Route path="/" element={<HomePage />} />
        <Route path="/auctions" element={<AuctionsPage />} />
        <Route path="/auction/:id" element={<AuctionDetailPage />} />
        <Route path="/category/:id" element={<AuctionsPage />} />
        
        {/* Authentication */}
        <Route path="/login" element={<AuthPage />} />
        <Route path="/register" element={<AuthPage />} />
        
        {/* User Account */}
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/profile/edit" element={<div>Edit Profile Page (Coming Soon)</div>} />
        <Route path="/user/:id" element={<div>Public User Profile (Coming Soon)</div>} />
        
        {/* Auction Management */}
        <Route path="/create-auction" element={<CreateAuctionPage />} />
        <Route path="/edit-auction/:id" element={<div>Edit Auction Page (Coming Soon)</div>} />
        
        {/* Payment and Processing */}
        <Route path="/payment/:id" element={<div>Payment Page (Coming Soon)</div>} />
        
        {/* 404 Not Found */}
        <Route path="*" element={
          <div style={{textAlign: 'center', marginTop: '100px'}}>
            <h1>404 - Page Not Found</h1>
            <p>The page you are looking for does not exist.</p>
          </div>
        } />
      </Routes>
    </Router>
  );
}

export default App;