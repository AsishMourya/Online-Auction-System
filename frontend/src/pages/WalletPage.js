import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/WalletPage.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const WalletPage = () => {
  const [walletBalance, setWalletBalance] = useState(0);
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

    // Fetch wallet data
    fetchWalletData();
    fetchTransactions();
  }, [navigate]);

  const fetchWalletData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const response = await axios.get(`${API_URL}/api/v1/accounts/wallet/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Extra careful parsing to ensure we have a valid number
      let balanceValue = 0;
      
      if (response.data?.data?.balance !== undefined) {
        balanceValue = response.data.data.balance;
      } else if (response.data?.balance !== undefined) {
        balanceValue = response.data.balance;
      }
      
      // Convert to number and handle invalid inputs
      balanceValue = parseFloat(balanceValue);
      if (isNaN(balanceValue)) {
        balanceValue = 0;
      }
      
      setWalletBalance(balanceValue);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching wallet data:', error);
      setError('Failed to load wallet data. Please try again.');
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    try {
      const token = localStorage.getItem('token');
      
      const response = await axios.get(`${API_URL}/api/v1/transactions/transactions/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Properly handle the response data structure
      let transactionsData = [];
      if (Array.isArray(response.data)) {
        transactionsData = response.data;
      } else if (Array.isArray(response.data?.data)) {
        transactionsData = response.data.data;
      } else if (response.data && typeof response.data === 'object') {
        // If it's an object with transaction properties
        transactionsData = [response.data];
      } else {
        console.warn('Unexpected transactions data format:', response.data);
        transactionsData = [];
      }
      
      // Now filter the transactions safely
      setTransactions(
        transactionsData.filter(t => 
          t && (t.transaction_type === 'deposit' || t.transaction_type === 'withdrawal')
        )
      );
    } catch (error) {
      console.error('Error fetching transactions:', error);
      setTransactions([]);
    }
  };

  const handleDeposit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount <= 0) {
      setError('Please enter a valid amount');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      
      const data = { 
        amount: amount,
        transaction_type: 'deposit',
        description: 'Wallet deposit'
      };
      
      console.log("Making deposit request with data:", data);
      
      const response = await axios.post(
        `${API_URL}/api/v1/transactions/transactions/`, 
        data, 
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log("Deposit response:", response.data);
      
      setSuccess(`Successfully deposited $${amount.toFixed(2)} to your wallet`);
      setDepositAmount('');
      
      // Refresh wallet data
      fetchWalletData();
      fetchTransactions();
    } catch (error) {
      console.error('Error making deposit:', error);
      console.log('Error response:', error.response?.data);
      
      // Provide more detailed error message if available
      if (error.response?.data?.message) {
        setError(error.response.data.message);
      } else if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else if (error.response?.data?.error) {
        setError(error.response.data.error);
      } else if (error.response?.status === 405) {
        setError('This deposit method is currently unavailable. Please try a different method or contact support.');
      } else {
        setError('Failed to make deposit. Please try again later.');
      }
    }
  };

  const formatCurrency = (value) => {
    const numValue = parseFloat(value);
    return isNaN(numValue) ? '0.00' : numValue.toFixed(2);
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
      const token = localStorage.getItem('token');
      let response;
      
      const config = {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      };
      
      console.log(`Testing ${method} ${endpoint}`, data ? 'with data:' : '', data || '');
      
      if (method === 'GET') {
        response = await axios.get(`${API_URL}${endpoint}`, config);
      } else if (method === 'POST') {
        response = await axios.post(`${API_URL}${endpoint}`, data, {
          ...config,
          headers: {
            ...config.headers,
            'Content-Type': 'application/json'
          }
        });
      } else if (method === 'OPTIONS') {
        response = await axios.options(`${API_URL}${endpoint}`, config);
        console.log(`${endpoint} allows:`, response.headers['allow']);
        return `${endpoint} allows: ${response.headers['allow'] || 'unknown'}`;
      }
      
      console.log(`${method} ${endpoint} response:`, response.data);
      return `Success! Check console for response data`;
    } catch (error) {
      console.error(`${method} ${endpoint} error:`, error);
      if (error.response) {
        console.log('Error response:', error.response.data);
        return `Error ${error.response.status}: ${JSON.stringify(error.response.data)}`;
      }
      return `Error: ${error.message}`;
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
                <button onClick={() => testAPI('/api/v1/transactions/transactions/')}>
                  Test GET Transactions
                </button>
              </div>
              
              <h4>Deposit Endpoints (Test All)</h4>
              <div className="debug-buttons">
                <button onClick={async () => {
                  const data = { amount: 10, transaction_type: 'deposit', description: 'Test deposit' };
                  const results = [];
                  
                  // Test different endpoints
                  results.push(`/api/v1/transactions/transactions/: ${await testAPI('/api/v1/transactions/transactions/', 'POST', data)}`);
                  results.push(`/api/v1/accounts/wallet/deposit/: ${await testAPI('/api/v1/accounts/wallet/deposit/', 'POST', { amount: 10 })}`);
                  results.push(`/api/v1/accounts/deposit/: ${await testAPI('/api/v1/accounts/deposit/', 'POST', { amount: 10 })}`);
                  
                  alert('Tested multiple deposit endpoints, check console for results.\n\n' + results.join('\n\n'));
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

export default WalletPage;