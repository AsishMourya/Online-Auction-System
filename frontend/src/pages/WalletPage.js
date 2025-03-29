import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/WalletPage.css';
import { toNumber, formatCurrency } from '../utils/formatters';
import { useWallet } from '../contexts/WalletContext';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const WalletPage = () => {
  // Add this formatDate function
  const formatDate = (dateString) => {
    const options = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  const { walletBalance, updateWalletBalance, fetchWalletBalance, syncBalanceToServer } = useWallet();

  const [depositAmount, setDepositAmount] = useState('');
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login?redirect=/wallet');
      return;
    }

    // Only show loading if we don't already have a wallet balance
    if (walletBalance === 0 || walletBalance === null || walletBalance === undefined) {
      setLoading(true);
    }

    // Fetch wallet data and transactions
    fetchWalletData();
    fetchTransactions();
  }, [navigate, fetchWalletBalance]);

  const fetchWalletData = async () => {
    try {
      // This will update the global wallet context
      await fetchWalletBalance();
      setLoading(false);
    } catch (error) {
      console.error('Error in fetchWalletData:', error);
      setError('Failed to load wallet data. Please try again.');
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('access_token');

      if (!token) {
        console.error('No auth token found');
        setError('Authentication required');
        return;
      }

      const response = await fetch(`${API_URL}/api/v1/transactions/transactions/`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      // Check if response is OK before parsing JSON
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Transaction API Error Response:', errorText);
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success) {
        setTransactions(data.data || []);
      } else {
        console.error('Failed to fetch transactions:', data.message);
      }
    } catch (error) {
      console.error('Error fetching transactions:', error);
    }
  };

  // Update the handleDeposit function to prevent incorrect balance calculations
  const handleDeposit = async (e) => {
    e.preventDefault();
    
    if (!depositAmount || parseFloat(depositAmount) <= 0) {
      setError('Please enter a valid amount');
      return;
    }
    
    setError('');
    setSuccess('');
    
    // Parse the deposit amount correctly
    const numAmount = parseFloat(depositAmount);
    
    // Log current state for debugging
    console.log('Current wallet balance before deposit:', walletBalance);
    console.log('Deposit amount:', numAmount);
    
    // Calculate new balance precisely
    const currentBalance = parseFloat(walletBalance);
    const exactNewBalance = currentBalance + numAmount;
    
    console.log('Calculated new balance:', exactNewBalance);
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      if (!token) {
        setError('You must be logged in to make a deposit');
        setLoading(false);
        return;
      }
      
      // Make the API request to deposit funds
      const response = await axios.post(
        `${API_URL}/api/v1/transactions/deposit/`, 
        { amount: numAmount },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log('Deposit API response:', response.data);
      
      if (response.data.success || response.status === 200 || response.status === 201) {
        // If the API returns a balance, use that
        let updatedBalance = exactNewBalance;
        
        if (response.data?.data?.balance) {
          updatedBalance = parseFloat(response.data.data.balance);
        } else if (response.data?.balance) {
          updatedBalance = parseFloat(response.data.balance);
        } else if (response.data?.data?.wallet?.balance) {
          updatedBalance = parseFloat(response.data.data.wallet.balance);
        } else if (response.data?.wallet?.balance) {
          updatedBalance = parseFloat(response.data.wallet.balance);
        }
        
        // Ensure the balance is valid
        if (isNaN(updatedBalance)) {
          updatedBalance = exactNewBalance;
        }
        
        console.log('Final balance from API or calculation:', updatedBalance);
        
        // Update the wallet balance through the context
        updateWalletBalance(updatedBalance);
        
        // Update local state and UI
        setSuccess(`Successfully deposited $${numAmount.toFixed(2)}`);
        setDepositAmount('');
        
        // Fetch updated transactions
        fetchTransactions();
      } else {
        setError('Failed to process deposit. Please try again.');
      }
    } catch (error) {
      console.error('Error during deposit:', error);
      
      // Show a more specific error message
      if (error.response) {
        console.error('Error response:', error.response.data);
        setError(`Deposit failed: ${error.response.data.message || error.response.data.detail || 'Server error'}`);
      } else if (error.request) {
        setError('Network error. Please check your connection and try again.');
      } else {
        setError(`Error: ${error.message}`);
      }
      
      // Fall back to optimistic update if the API fails
      console.log('Falling back to optimistic update');
      updateWalletBalance(exactNewBalance);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <p>Loading wallet data...</p>
      </div>
    );
  }

  return (
    <div className="wallet-page">
      <div className="container">
        <h1>My Wallet</h1>

        <div className="wallet-balance-card">
          <div className="balance-info">
            <h2>Current Balance</h2>
            <div className="balance-amount">${formatCurrency(walletBalance)}</div>
          </div>

          <div className="wallet-actions">
            <form onSubmit={handleDeposit} className="deposit-form">
              <h3>Add Funds</h3>

              {error && <div className="error-message">{error}</div>}
              {success && <div className="success-message">{success}</div>}

              <div className="form-group">
                <label htmlFor="depositAmount">Amount ($)</label>
                <input
                  type="number"
                  id="depositAmount"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  min="0.01"
                  step="0.01"
                  placeholder="Enter amount"
                  required
                />
              </div>

              <button type="submit" className="btn btn-primary">Deposit</button>
            </form>
          </div>

          <div className="refresh-actions">
            <button 
              className="btn btn-secondary"
              onClick={() => fetchWalletData()}
            >
              Refresh Balance
            </button>
          </div>
        </div>

        <div className="transactions-section">
          <h2>Transaction History</h2>

          {transactions.length > 0 ? (
            <div className="transactions-table">
              <div className="transaction-header">
                <div className="transaction-cell">Type</div>
                <div className="transaction-cell">Amount</div>
                <div className="transaction-cell">Date</div>
                <div className="transaction-cell">Status</div>
              </div>

              {transactions.map(transaction => (
                <div key={transaction.id} className={`transaction-row ${transaction.transaction_type}`}>
                  <div className="transaction-cell">
                    {transaction.transaction_type === 'deposit' ? 'Deposit' : 'Withdrawal'}
                  </div>
                  <div className="transaction-cell amount">
                    ${formatCurrency(transaction.amount)}
                  </div>
                  <div className="transaction-cell">
                    {formatDate(transaction.created_at)}
                  </div>
                  <div className="transaction-cell status">
                    <span className={`status-badge ${transaction.status.toLowerCase()}`}>
                      {transaction.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-transactions">No transactions found.</p>
          )}
        </div>

        <div className="back-link">
          <Link to="/profile" className="btn btn-secondary">Back to Profile</Link>
        </div>
      </div>
    </div>
  );
};

export default WalletPage;