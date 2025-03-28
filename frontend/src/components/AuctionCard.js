// Add a check for auto-bidding in your component
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const AuctionCard = ({ auction }) => {
  const [hasAutoBid, setHasAutoBid] = useState(false);
  const isLoggedIn = localStorage.getItem('token') !== null;
  
  useEffect(() => {
    // Check if user has auto-bidding set up for this auction
    const checkAutoBid = async () => {
      if (!isLoggedIn) return;
      
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${API_URL}/api/v1/auctions/autobids/`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        const autobids = response.data?.data || response.data || [];
        const hasActive = autobids.some(bid => 
          (bid.auction === auction.id || bid.auction?.id === auction.id) && 
          bid.is_active
        );
        
        setHasAutoBid(hasActive);
      } catch (error) {
        console.error('Error checking auto-bid status:', error);
      }
    };
    
    checkAutoBid();
  }, [auction.id, isLoggedIn]);
  
  // Rest of your component...
  
  // In your JSX, add an indicator for auto-bidding
  return (
    <div className="auction-card">
      {/* Existing card content */}
      
      {/* Add this indicator if auto-bidding is active */}
      {hasAutoBid && (
        <div className="auto-bid-indicator" title="You have auto-bidding enabled for this auction">
          🤖 Auto-bidding
        </div>
      )}
    </div>
  );
};