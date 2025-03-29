import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './pages/Navbar';
import HomePage from './pages/HomePage';
import AuctionsPage from './pages/AuctionsPage';
import AuctionDetailPage from './pages/AuctionDetailPage';
import CreateAuctionPage from './pages/CreateAuctionPage';
import AuthPage from './pages/AuthPage';
import ProfilePage from './pages/ProfilePage';
import EditProfilePage from './pages/EditProfilePage';
import DebugPage from './pages/DebugPage'; // Import DebugPage
import WalletPage from './pages/WalletPage'; // Import WalletPage
import { WalletProvider } from './contexts/WalletContext'; // Add WalletProvider import
import './App.css';

function App() {
  // Add effect to handle auth changes
  useEffect(() => {
    // Function to handle authentication changes
    const handleAuthChange = () => {
      const token = localStorage.getItem('token');
      console.log('Auth status changed:', token ? 'logged in' : 'logged out');
      
      // Dispatch custom event for components to listen to
      window.dispatchEvent(new CustomEvent('auth-change', { 
        detail: { authenticated: !!token }
      }));
    };
    
    // Listen for storage events (login/logout in other tabs)
    window.addEventListener('storage', (e) => {
      if (e.key === 'token' || e.key === 'user_info') {
        handleAuthChange();
      }
    });
    
    // Check initial auth status
    handleAuthChange();
    
    return () => {
      window.removeEventListener('storage', handleAuthChange);
    };
  }, []);

  return (
    <WalletProvider> {/* Wrap the app content with WalletProvider */}
      <Router>
        <div className="app">
          <Navbar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/auctions" element={<AuctionsPage />} />
              <Route path="/category/:categoryId" element={<AuctionsPage />} /> {/* This is important */}
              <Route path="/auction/:id" element={<AuctionDetailPage />} />
              <Route path="/create-auction" element={<CreateAuctionPage />} />
              <Route path="/login" element={<AuthPage />} />
              <Route path="/register" element={<AuthPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/profile/edit" element={<EditProfilePage />} />
              <Route path="/wallet" element={<WalletPage />} /> {/* Add WalletPage route */}
              <Route path="/debug" element={<DebugPage />} /> {/* Add DebugPage route */}
              <Route path="/seller/:id" element={<ProfilePage />} /> {/* Use ProfilePage for seller profiles too */}
            </Routes>
          </main>
          {/* Footer component removed as requested */}
        </div>
      </Router>
    </WalletProvider>
  );
}

export default App;