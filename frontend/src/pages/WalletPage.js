import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/WalletPage.css';
import { toNumber, formatCurrency } from '../utils/formatters';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const WalletPage = () => {
  // Initialize wallet balance as a number
  const [walletBalance, setWalletBalance] = useState(0);
  
  // Always convert to number when setting wallet balance
  const updateWalletBalance = (value) => {
    const numValue = Number(value);
    setWalletBalance(isNaN(numValue) ? 0 : numValue);
  };

  const [depositAmount, setDepositAmount] = useState('');
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  console.log('Wallet Balance Type:', typeof walletBalance, walletBalance);

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login?redirect=/wallet');
      return;
    }

    // Fetch wallet data
    fetchWalletData();
    fetchTransactions();
  }, [navigate]);

  const fetchWalletData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Try to get from API first
      try {
        console.log('Fetching wallet data from server...');
        const response = await axios.get(`${API_URL}/api/v1/accounts/wallet/`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        // Extract the balance from the response
        let balanceValue = 0;
        if (response.data?.data?.balance !== undefined) {
          balanceValue = response.data.data.balance;
        } else if (response.data?.balance !== undefined) {
          balanceValue = response.data.balance;
        }
        
        // Convert to number and validate
        balanceValue = parseFloat(balanceValue);
        if (isNaN(balanceValue)) {
          balanceValue = 0;
        }
        
        console.log('Server returned balance:', balanceValue);
        
        // Check if the server balance seems to be reset/incorrect
        try {
          const fallbackData = JSON.parse(localStorage.getItem('wallet_fallback') || '{}');
          if (fallbackData.balance && parseFloat(fallbackData.balance) > balanceValue) {
            console.warn('Server balance appears to be reset. Using localStorage fallback.');
            
            // Try to update the server with our local balance
            try {
              await axios.post(
                `${API_URL}/api/v1/accounts/wallet/update_balance/`,
                { balance: fallbackData.balance },
                {
                  headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                  }
                }
              );
              console.log('Updated server with localStorage balance');
              balanceValue = parseFloat(fallbackData.balance);
            } catch (updateError) {
              console.error('Failed to update server with localStorage balance:', updateError);
            }
          }
        } catch (e) {
          console.error('Error checking localStorage fallback:', e);
        }
        
        updateWalletBalance(balanceValue);
        setLoading(false);
      } catch (apiError) {
        console.error('Error fetching wallet from API:', apiError);
        
        // Try to use localStorage as fallback
        try {
          const fallbackData = JSON.parse(localStorage.getItem('wallet_fallback') || '{}');
          if (fallbackData.balance) {
            console.log('Using localStorage fallback for wallet balance:', fallbackData);
            updateWalletBalance(fallbackData.balance);
            setError('Using locally stored balance (server unavailable)');
          } else {
            throw new Error('No fallback data available');
          }
        } catch (fallbackError) {
          console.error('Error using fallback data:', fallbackError);
          setError('Failed to load wallet data. Please try again.');
          updateWalletBalance(0);
        }
        
        setLoading(false);
      }
    } catch (error) {
      console.error('Unhandled error in fetchWalletData:', error);
      setError('Failed to load wallet data. Please try again.');
      setLoading(false);
      updateWalletBalance(0);
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

  const handleDeposit = async (e) => {
    e.preventDefault();
    
    if (!depositAmount || parseFloat(depositAmount) <= 0) {
      setError('Please enter a valid amount');
      return;
    }
    
    setError('');
    setSuccess('');
    
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('access_token');
      
      // Use the correct URL with API prefix
      const response = await fetch(`${API_URL}/api/v1/transactions/deposit/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ amount: parseFloat(depositAmount) })
      });

      // Check if response is OK before parsing JSON
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error Response:', errorText);
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        // Update UI with new balance
        updateWalletBalance(data.wallet.balance);
        setSuccess(`Successfully deposited $${depositAmount}`);
        setDepositAmount('');
        
        // Update transaction history
        fetchTransactions();
        
        // Also backup to localStorage
        try {
          localStorage.setItem('wallet_fallback', JSON.stringify({
            balance: data.wallet.balance,
            lastUpdated: new Date().toISOString()
          }));
        } catch (e) {
          console.error('Error saving to localStorage:', e);
        }
      } else {
        setError(data.message || 'Error adding funds to wallet');
      }
    } catch (error) {
      console.error('Error during deposit:', error);
      setError(`Network error during deposit: ${error.message}`);
    }
  };

  const quickDeposit = async (amount) => {
    try {
      // Use the consistent token (use the same one that works in fetchWalletData)
      const token = localStorage.getItem('token');
      
      const response = await fetch(`${API_URL}/api/v1/transactions/quick-deposit/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ amount: amount })
      });
      
      // Check if response is OK before parsing JSON
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error Response:', errorText);
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        // Update UI with new balance
        updateWalletBalance(data.wallet.balance);
        setSuccess(`Added $${amount} to your wallet`);
        
        // Update transaction history
        fetchTransactions();
        
        // Also update localStorage backup
        try {
          const walletData = {
            balance: data.wallet.balance,
            lastUpdated: new Date().toISOString()
          };
          localStorage.setItem('wallet_fallback', JSON.stringify(walletData));
        } catch (e) {
          console.error('Error saving to localStorage:', e);
        }
        
        return true;
      } else {
        setError(data.message || 'Error adding funds to wallet');
        
        // Still update UI for better UX but mark as tentative
        updateWalletBalance(walletBalance + parseFloat(amount));
        setSuccess(`Server did not confirm the deposit. Your balance is updated locally but may not persist.`);
        return false;
      }
    } catch (error) {
      console.error('Error during quick deposit:', error);
      setError('Network error during deposit');
      
      // Update UI for better UX but mark as tentative
      updateWalletBalance(walletBalance + parseFloat(amount));
      setSuccess(`Server did not confirm the deposit. Your balance is updated locally but may not persist.`);
      return false;
    }
  };

  const formatNumber = (value) => {
    const num = Number(value);
    return isNaN(num) ? '0.00' : num.toFixed(2);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const testAPI = async (endpoint, method = 'GET', data = null) => {
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('access_token');
      
      const options = {
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      };
      
      if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(data);
        console.log(`Request body for ${endpoint}:`, options.body);
      }
      
      console.log(`Testing ${method} ${endpoint} with options:`, options);
      
      const response = await fetch(endpoint, options);
      
      let responseText;
      try {
        responseText = await response.text();
        console.log(`Raw response from ${endpoint}:`, responseText);
        
        const responseData = responseText ? JSON.parse(responseText) : {};
        console.log(`${method} ${endpoint} Parsed Response:`, responseData);
        
        if (response.ok) {
          return `Success ${response.status}: ${JSON.stringify(responseData).substring(0, 100)}...`;
        } else {
          return `Error ${response.status}: ${JSON.stringify(responseData).substring(0, 100)}...`;
        }
      } catch (parseError) {
        console.error(`Error parsing response from ${endpoint}:`, parseError);
        return `Error ${response.status}: Raw response (not JSON): ${responseText.substring(0, 100)}...`;
      }
    } catch (error) {
      console.error(`Error testing ${method} ${endpoint}:`, error);
      return `Exception: ${error.message}`;
    }
  };

  const checkBackendStorage = async () => {
    try {
      const token = localStorage.getItem('token');
      
      // First check if we can access the wallet
      const walletResponse = await axios.get(`${API_URL}/api/v1/accounts/wallet/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Backend wallet status:', walletResponse.data);
      
      // Check transaction history
      const transResponse = await axios.get(`${API_URL}/api/v1/transactions/transactions/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Backend transactions:', transResponse.data);
      
      // Test if the backend supports direct balance updates
      try {
        const testResponse = await axios.post(
          `${API_URL}/api/v1/accounts/wallet/update_balance/`, 
          { balance: walletBalance }, 
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );
        
        console.log('Direct balance update test:', testResponse.data);
      } catch (e) {
        console.log('Direct balance update not supported');
      }
      
      return {
        walletData: walletResponse.data,
        transactions: transResponse.data
      };
    } catch (error) {
      console.error('Backend storage check error:', error);
      return null;
    }
  };

  const updateWalletDirectly = async (amount) => {
    try {
      const token = localStorage.getItem('token');
      const newBalance = walletBalance + parseFloat(amount);
      
      console.log(`Trying direct wallet update to balance: ${newBalance}`);
      
      const response = await axios.post(
        `${API_URL}/api/v1/accounts/wallet/update_balance/`,
        { balance: newBalance },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log('Direct wallet update response:', response.data);
      
      // Create a record of this update
      setTransactions(prev => [{
        id: Date.now(),
        transaction_type: 'deposit',
        amount: amount,
        created_at: new Date().toISOString(),
        status: 'completed'
      }, ...prev]);
      
      return true;
    } catch (error) {
      console.error('Direct wallet update failed:', error);
      return false;
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

        {process.env.NODE_ENV === 'development' && (
          <div className="debug-section">
            <h3>API Debugging (Development Only)</h3>
            
            <div className="debug-panel">
              <h4>GET Endpoints (Read)</h4>
              <div className="debug-buttons">
                <button onClick={() => testAPI('/api/v1/accounts/wallet/')}>
                  Test GET Wallet
                </button>
                <button onClick={() => testAPI(`${API_URL}/api/v1/transactions/transactions/`)}>
                  Test GET Transactions
                </button>
              </div>
              
              <h4>Deposit Endpoints (Test All)</h4>
              <div className="debug-buttons">
                <button onClick={async () => {
                  const data = { amount: 10 };
                  const results = [];
                  
                  // Test endpoints with full URLs including API_URL
                  results.push(`/api/v1/transactions/deposit/: ${await testAPI(`${API_URL}/api/v1/transactions/deposit/`, 'POST', data)}`);
                  results.push(`/api/v1/transactions/quick-deposit/: ${await testAPI(`${API_URL}/api/v1/transactions/quick-deposit/`, 'POST', data)}`);
                  
                  alert('Tested deposit endpoints, check console for results.\n\n' + results.join('\n\n'));
                }}>
                  Test ALL Deposit Endpoints
                </button>
              </div>
              
              <h4>API Discovery (OPTIONS)</h4>
              <div className="debug-buttons">
                <button onClick={async () => {
                  const endpoints = [
                    '/api/v1/accounts/wallet/',
                    '/api/v1/transactions/transactions/',
                    '/api/v1/accounts/wallet/deposit/',
                    '/api/v1/transactions/deposit/'
                  ];
                  
                  const results = await Promise.all(endpoints.map(endpoint => 
                    testAPI(endpoint, 'OPTIONS')
                  ));
                  
                  alert('OPTIONS results:\n\n' + results.join('\n\n'));
                }}>
                  Discover API Methods
                </button>
              </div>
            </div>

            <div className="debug-panel">
              <h4>Local Storage Management</h4>
              <div className="debug-buttons">
                <button onClick={() => {
                  try {
                    // Create local storage entry
                    const walletData = {
                      balance: walletBalance,
                      lastUpdated: new Date().toISOString()
                    };
                    localStorage.setItem('wallet_fallback', JSON.stringify(walletData));
                    alert(`Saved current balance (${walletBalance}) to localStorage`);
                  } catch (e) {
                    alert(`Error saving to localStorage: ${e.message}`);
                  }
                }}>
                  Save Current Balance to LocalStorage
                </button>
                <button onClick={() => {
                  try {
                    const data = JSON.parse(localStorage.getItem('wallet_fallback') || '{}');
                    alert(`LocalStorage wallet data: ${JSON.stringify(data, null, 2)}`);
                  } catch (e) {
                    alert(`Error reading from localStorage: ${e.message}`);
                  }
                }}>
                  View LocalStorage Data
                </button>
              </div>
            </div>
            
            <div className="debug-panel">
              <h4>Quick Fix Deposit</h4>
              <div className="debug-buttons">
                <button onClick={async () => {
                  try {
                    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
                    
                    // Use the correct URL with API prefix
                    const response = await fetch(`${API_URL}/api/v1/transactions/quick-deposit/`, {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                      },
                      body: JSON.stringify({ amount: 10 })
                    });
                    
                    // Check if response is OK before parsing JSON
                    if (!response.ok) {
                      const errorText = await response.text();
                      console.error('API Error Response:', errorText);
                      throw new Error(`API error: ${response.status} ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                      // Update UI with new balance
                      updateWalletBalance(data.wallet.balance);
                      setSuccess(`Added $10 to your wallet`);
                      
                      // Update transaction history
                      fetchTransactions();
                    } else {
                      // Show error from server
                      setError(data.message || 'Error adding funds');
                      console.error('Server error:', data);
                      
                      // Still update UI for better UX, but mark it as tentative
                      updateWalletBalance(walletBalance + 10);
                      setSuccess(`Server did not confirm the deposit. Your balance is updated locally but may not persist.`);
                    }
                  } catch (error) {
                    console.error('Error during quick deposit:', error);
                    setError(`Network error during deposit: ${error.message}`);
                    
                    // Update UI anyway with warning
                    updateWalletBalance(walletBalance + 10);
                    setSuccess(`Server did not confirm the deposit. Your balance is updated locally but may not persist.`);
                  }
                }}>
                  Quick Add $10
                </button>
              </div>
            </div>
            
            <div className="debug-log">
              <h4>Manual API Test</h4>
              <div className="api-tester">
                <select id="apiMethod">
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="OPTIONS">OPTIONS</option>
                </select>
                <input 
                  type="text" 
                  id="apiEndpoint" 
                  placeholder="/api/v1/endpoint" 
                  defaultValue="/api/v1/accounts/wallet/"
                />
                <button onClick={() => {
                  const method = document.getElementById('apiMethod').value;
                  const endpoint = document.getElementById('apiEndpoint').value;
                  const dataEl = document.getElementById('apiData');
                  
                  let data = null;
                  if (method === 'POST' && dataEl.value) {
                    try {
                      data = JSON.parse(dataEl.value);
                    } catch (e) {
                      alert('Invalid JSON data');
                      return;
                    }
                  }
                  
                  testAPI(endpoint, method, data);
                }}>
                  Test
                </button>
              </div>
              <textarea 
                id="apiData" 
                placeholder="JSON data for POST requests"
                defaultValue={JSON.stringify({ amount: 10, transaction_type: 'deposit' }, null, 2)}
                rows="4"
              ></textarea>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const AutoBidding = ({ walletBalance, ...props }) => {
  console.log('AutoBidding received walletBalance:', typeof walletBalance, walletBalance);
  // Rest of your component
};

export default WalletPage;