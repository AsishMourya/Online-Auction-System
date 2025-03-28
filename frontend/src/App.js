import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './pages/Navbar';
import HomePage from './pages/HomePage';
import AuctionsPage from './pages/AuctionsPage';
import AuctionDetailPage from './pages/AuctionDetailPage';
import CreateAuctionPage from './pages/CreateAuctionPage';
import AuthPage from './pages/AuthPage';
import ProfilePage from './pages/ProfilePage';
import EditProfilePage from './pages/EditProfilePage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/auctions" element={<AuctionsPage />} />
            <Route path="/category/:categoryId" element={<AuctionsPage />} />
            <Route path="/auction/:id" element={<AuctionDetailPage />} />
            <Route path="/create-auction" element={<CreateAuctionPage />} />
            <Route path="/login" element={<AuthPage />} />
            <Route path="/register" element={<AuthPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/profile/edit" element={<EditProfilePage />} />
          </Routes>
        </main>
        {/* Footer component removed as requested */}
      </div>
    </Router>
  );
}

export default App;