import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/WalletPage.css';
import { toNumber, formatCurrency } from '../utils/formatters';
import { useWallet } from '../contexts/WalletContext';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const WalletPage = () => {
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
  const [depositInProgress, setDepositInProgress] = useState(false);
  const navigate = useNavigate();

  const initialLoadComplete = useRef(false);
  const loadingDataRef = useRef(false);
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login?redirect=/wallet');
      return;
    }

    try {
      const storedUserInfo = localStorage.getItem('user_info');
      if (storedUserInfo) {
        const parsedInfo = JSON.parse(storedUserInfo);
        setUserInfo(parsedInfo);
        console.log('Loaded user info from localStorage:', parsedInfo);
      } else {
        const fetchUserInfo = async () => {
          try {
            const response = await axios.get(`${API_URL}/api/v1/accounts/user/`, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            });

            console.log('User API response:', response.data);

            if (response.data) {
              const userData = response.data.data || response.data;
              setUserInfo(userData);
              localStorage.setItem('user_info', JSON.stringify(userData));
            }
          } catch (error) {
            console.error('Error fetching user info:', error);
          }
        };

        fetchUserInfo();
      }
    } catch (e) {
      console.error('Error processing user info:', e);
    }

    if (loadingDataRef.current || initialLoadComplete.current) {
      console.log('Data already loading or loaded, skipping duplicate load');
      return;
    }

    setLoading(true);
    loadingDataRef.current = true;

    const loadData = async () => {
      try {
        console.log('Loading wallet data...');
        await fetchWalletBalance(true);
        await fetchTransactions();
        initialLoadComplete.current = true;
      } catch (error) {
        console.error('Error loading wallet data:', error);
        setError('Failed to load wallet data');
      } finally {
        setLoading(false);
        loadingDataRef.current = false;
      }
    };

    loadData();

    return () => {
      console.log('WalletPage - cleaning up');
    };
  }, [navigate]);

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

  const handleDeposit = async (e) => {
    e.preventDefault();

    if (depositInProgress) {
      console.log('Deposit already in progress, ignoring duplicate request');
      return;
    }

    if (!depositAmount || isNaN(parseFloat(depositAmount)) || parseFloat(depositAmount) <= 0) {
      setError('Please enter a valid amount greater than zero');
      return;
    }

    setError('');
    setSuccess('');
    setDepositInProgress(true);

    const amountToDeposit = parseFloat(depositAmount);
    console.log('Deposit amount:', amountToDeposit);
    console.log('Current wallet balance:', walletBalance);

    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('You must be logged in to make a deposit');
        setLoading(false);
        setDepositInProgress(false);
        return;
      }

      console.log('Sending deposit request to API:', { amount: amountToDeposit });
      const response = await axios.post(
        `${API_URL}/api/v1/transactions/deposit/`,
        { amount: amountToDeposit },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      console.log('Deposit API response:', response.data);

      if (response.status === 200 || response.status === 201) {
        setSuccess(`Successfully deposited $${amountToDeposit.toFixed(2)}`);
        setDepositAmount('');

        let serverBalance = null;

        if (response.data?.data?.balance !== undefined) {
          serverBalance = parseFloat(response.data.data.balance);
        } else if (response.data?.balance !== undefined) {
          serverBalance = parseFloat(response.data.balance);
        } else if (response.data?.data?.wallet?.balance !== undefined) {
          serverBalance = parseFloat(response.data.data.wallet.balance);
        } else if (response.data?.wallet?.balance !== undefined) {
          serverBalance = parseFloat(response.data.wallet.balance);
        }

        if (!isNaN(serverBalance) && serverBalance > 0) {
          console.log('Using server balance:', serverBalance);
          updateWalletBalance(serverBalance);
        } else {
          console.log('Server did not return balance, fetching once');
          await fetchWalletBalance(true);
        }

        fetchTransactions();
      } else {
        console.error('Deposit failed:', response.data);
        setError('Failed to process deposit. Please try again.');
      }
    } catch (error) {
      console.error('Error during deposit:', error);

      if (error.response) {
        console.error('API error response:', error.response.data);
        setError(error.response.data.message || error.response.data.detail || 'Server error');
      } else if (error.request) {
        setError('Network error. Please check your connection and try again.');
      } else {
        setError(error.message || 'An unexpected error occurred');
      }
    } finally {
      setLoading(false);
      setDepositInProgress(false);
    }
  };

  const resetWalletBalance = async () => {
    if (!window.confirm('Are you sure you want to reset your wallet balance? This will synchronize with the server.')) {
      return;
    }

    try {
      setLoading(true);
      setError('');
      setSuccess('');

      const token = localStorage.getItem('token');
      if (!token) {
        setError('You must be logged in to reset your wallet');
        setLoading(false);
        return;
      }

      console.log('Getting current server balance...');

      const response = await axios.get(
        `${API_URL}/api/v1/accounts/wallet/`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      console.log('Server wallet response:', response.data);

      let serverBalance = null;

      if (response.data?.data?.balance !== undefined) {
        serverBalance = response.data.data.balance;
      } else if (response.data?.balance !== undefined) {
        serverBalance = response.data.balance;
      } else if (response.data?.data?.wallet?.balance !== undefined) {
        serverBalance = response.data.data.wallet.balance;
      } else if (response.data?.wallet?.balance !== undefined) {
        serverBalance = response.data.wallet.balance;
      }

      serverBalance = parseFloat(serverBalance);

      if (isNaN(serverBalance)) {
        setError('Could not get a valid balance from the server');
        setLoading(false);
        return;
      }

      console.log('Parsed server balance:', serverBalance);

      updateWalletBalance(serverBalance);

      setSuccess(`Wallet balance has been reset to $${serverBalance.toFixed(2)}`);

      fetchTransactions();
    } catch (error) {
      console.error('Error resetting wallet balance:', error);
      setError(`Failed to reset wallet balance: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const walletDataFetchingRef = useRef(false);

  const fetchWalletData = async () => {
    if (walletDataFetchingRef.current) {
      console.log('Wallet data fetch already in progress, skipping duplicate');
      return walletBalance;
    }

    walletDataFetchingRef.current = true;
    setLoading(true);

    try {
      console.log('Fetching wallet data from server...');

      const token = localStorage.getItem('token');
      if (!token) {
        setError('You must be logged in to view your wallet');
        return walletBalance;
      }

      const response = await axios.get(
        `${API_URL}/api/v1/accounts/wallet/`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      console.log('Direct wallet API response:', response.data);

      let serverBalance = null;

      if (response.data?.data?.balance !== undefined) {
        serverBalance = response.data.data.balance;
      } else if (response.data?.balance !== undefined) {
        serverBalance = response.data.balance;
      } else if (response.data?.data?.wallet?.balance !== undefined) {
        serverBalance = response.data.data.wallet.balance;
      } else if (response.data?.wallet?.balance !== undefined) {
        serverBalance = response.data.wallet.balance;
      }

      serverBalance = parseFloat(serverBalance);

      if (isNaN(serverBalance)) {
        console.warn('Server returned invalid balance');
        return walletBalance;
      }

      console.log('Parsed server balance:', serverBalance);

      updateWalletBalance(serverBalance);

      return serverBalance;
    } catch (error) {
      console.error('Error fetching wallet data:', error);
      setError('Failed to refresh wallet balance');
      return walletBalance;
    } finally {
      setLoading(false);
      walletDataFetchingRef.current = false;
    }
  };

  const getUserIdentifier = () => {
    if (!userInfo) return 'User';

    return userInfo.username || 
           userInfo.email || 
           userInfo.name || 
           userInfo.id || 
           'User';
  };

  if (loading && !initialLoadComplete.current) {
    return (
      <div className="wallet-page">
        <div className="container">
          <h1>My Wallet</h1>

          <div className="wallet-balance-card">
            <div className="balance-info">
              <h2>Current Balance</h2>
              <div className="balance-amount skeleton-loading">Loading...</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="wallet-page">
      <div className="container">
        <h1>{getUserIdentifier()}'s Wallet</h1>

        <div className="wallet-balance-card">
          <div className="balance-info">
            <h2>Current Balance</h2>
            <div className="balance-amount">${formatCurrency(walletBalance)}</div>
            {userInfo && (
              <div className="user-info">
                Account: {getUserIdentifier()}
              </div>
            )}
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
              onClick={async () => {
                try {
                  setLoading(true);
                  const result = await fetchWalletData();
                  console.log('Wallet refreshed, new balance:', result);
                  setSuccess(`Wallet balance refreshed: $${formatCurrency(result)}`);
                  setLoading(false);
                } catch (error) {
                  console.error('Error refreshing balance:', error);
                  setError('Failed to refresh balance');
                  setLoading(false);
                }
              }}
            >
              Get Latest Balance
            </button>
            <button 
              className="btn btn-warning"
              onClick={resetWalletBalance}
            >
              Sync with Server
            </button>
          </div>
        </div>

        <div className="transactions-section">
          <h2>Transaction History</h2>

          {loading ? (
            <p>Loading transactions...</p>
          ) : transactions.length > 0 ? (
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