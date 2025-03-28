import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/AutoBidding.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const AutoBidding = ({ auctionId, currentPrice, minBidIncrement }) => {
  const [maxAmount, setMaxAmount] = useState('');
  const [bidIncrement, setBidIncrement] = useState(minBidIncrement || 10);
  const [hasAutoBid, setHasAutoBid] = useState(false);
  const [autoBidActive, setAutoBidActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [walletBalance, setWalletBalance] = useState(0);

  useEffect(() => {
    // Check if user already has an autobid for this auction
    const checkAutoBid = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;

        const response = await axios.get(`${API_URL}/api/v1/auctions/autobids/`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        const autobids = response.data?.data || response.data || [];
        const existingAutoBid = autobids.find(bid => bid.auction === auctionId || bid.auction?.id === auctionId);
        
        if (existingAutoBid) {
          setHasAutoBid(true);
          setAutoBidActive(existingAutoBid.is_active);
          setMaxAmount(existingAutoBid.max_amount);
          setBidIncrement(existingAutoBid.bid_increment);
        }
      } catch (error) {
        console.error('Error checking autobid:', error);
      }
    };

    // Check wallet balance
    const checkWalletBalance = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;

        const response = await axios.get(`${API_URL}/api/v1/accounts/wallet/`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        const wallet = response.data?.data || response.data || {};
        setWalletBalance(wallet.balance || 0);
      } catch (error) {
        console.error('Error checking wallet balance:', error);
      }
    };

    checkAutoBid();
    checkWalletBalance();
  }, [auctionId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to use auto-bidding');
        setLoading(false);
        return;
      }

      const maxBid = parseFloat(maxAmount);
      if (isNaN(maxBid) || maxBid <= 0) {
        setError('Please enter a valid maximum amount');
        setLoading(false);
        return;
      }

      if (maxBid <= parseFloat(currentPrice)) {
        setError(`Maximum amount must be higher than current price (${currentPrice})`);
        setLoading(false);
        return;
      }

      if (maxBid > walletBalance) {
        setError(`Maximum amount exceeds your wallet balance (${walletBalance})`);
        setLoading(false);
        return;
      }

      const data = {
        auction: auctionId,
        max_amount: maxBid,
        bid_increment: parseFloat(bidIncrement)
      };

      const response = await axios.post(`${API_URL}/api/v1/auctions/autobids/`, data, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      setSuccess('Auto-bidding set up successfully!');
      setHasAutoBid(true);
      setAutoBidActive(true);
    } catch (error) {
      console.error('Error setting up auto-bidding:', error);
      if (error.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError('Failed to set up auto-bidding. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleAutoBid = async (activate) => {
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to use auto-bidding');
        setLoading(false);
        return;
      }

      // Get the autobids to find the ID of this auction's autobid
      const response = await axios.get(`${API_URL}/api/v1/auctions/autobids/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const autobids = response.data?.data || response.data || [];
      const existingAutoBid = autobids.find(bid => bid.auction === auctionId || bid.auction?.id === auctionId);
      
      if (!existingAutoBid) {
        setError('No auto-bid found for this auction');
        setLoading(false);
        return;
      }

      const endpoint = activate ? 'activate' : 'deactivate';
      await axios.post(`${API_URL}/api/v1/auctions/autobids/${existingAutoBid.id}/${endpoint}/`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      setSuccess(`Auto-bidding ${activate ? 'activated' : 'deactivated'} successfully!`);
      setAutoBidActive(activate);
    } catch (error) {
      console.error(`Error ${activate ? 'activating' : 'deactivating'} auto-bidding:`, error);
      if (error.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError(`Failed to ${activate ? 'activate' : 'deactivate'} auto-bidding. Please try again.`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auto-bidding-container">
      <h3>Automatic Bidding</h3>
      
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
      
      {!hasAutoBid ? (
        <form onSubmit={handleSubmit} className="auto-bid-form">
          <p className="auto-bid-description">
            Set up auto-bidding to automatically place bids for you up to a maximum amount.
          </p>
          
          <div className="form-group">
            <label htmlFor="maxAmount">Maximum Amount ($)</label>
            <input
              type="number"
              id="maxAmount"
              value={maxAmount}
              onChange={(e) => setMaxAmount(e.target.value)}
              step="0.01"
              min={currentPrice}
              required
              disabled={loading}
            />
            <p className="form-hint">This is the maximum amount you're willing to bid</p>
          </div>
          
          <div className="form-group">
            <label htmlFor="bidIncrement">Bid Increment ($)</label>
            <input
              type="number"
              id="bidIncrement"
              value={bidIncrement}
              onChange={(e) => setBidIncrement(e.target.value)}
              step="0.01"
              min={minBidIncrement}
              required
              disabled={loading}
            />
            <p className="form-hint">Amount to increase each time you're outbid (minimum: ${minBidIncrement})</p>
          </div>
          
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Setting up...' : 'Set Up Auto-Bidding'}
          </button>
          
          <div className="wallet-info">
            <p>Your wallet balance: <strong>${walletBalance.toFixed(2)}</strong></p>
          </div>
        </form>
      ) : (
        <div className="auto-bid-status">
          <p>
            You have set up auto-bidding for this auction.
            <br />
            Maximum bid: <strong>${parseFloat(maxAmount).toFixed(2)}</strong>
            <br />
            Bid increment: <strong>${parseFloat(bidIncrement).toFixed(2)}</strong>
            <br />
            Status: <strong>{autoBidActive ? 'Active' : 'Inactive'}</strong>
          </p>
          
          <div className="auto-bid-actions">
            {autoBidActive ? (
              <button 
                onClick={() => toggleAutoBid(false)} 
                className="btn btn-secondary"
                disabled={loading}
              >
                {loading ? 'Processing...' : 'Pause Auto-bidding'}
              </button>
            ) : (
              <button 
                onClick={() => toggleAutoBid(true)} 
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? 'Processing...' : 'Resume Auto-bidding'}
              </button>
            )}
            
            <p className="form-hint">
              You can pause and resume your auto-bidding at any time.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default AutoBidding;