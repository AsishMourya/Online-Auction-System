import React, { createContext, useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WalletContext = createContext();

export const WalletProvider = ({ children }) => {
  const [walletBalance, setWalletBalance] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Add refs to track API calls and prevent race conditions
  const fetchInProgressRef = useRef(false);
  const lastFetchTimeRef = useRef(0);
  
  // Get the current user ID/email for user-specific storage
  const getCurrentUserId = () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return null;
      
      // Try to get user info from localStorage
      const userInfo = localStorage.getItem('user_info');
      if (userInfo) {
        const parsed = JSON.parse(userInfo);
        return parsed.id || parsed.email || parsed.username || 'user';
      }
      
      // If no user info, use a hash of the token as identifier
      return `user_${token.substring(0, 10)}`;
    } catch (e) {
      console.error('Error getting user ID:', e);
      return 'anonymous';
    }
  };
  
  // Get user-specific storage key
  const getUserStorageKey = () => {
    const userId = getCurrentUserId();
    return userId ? `wallet_balance_${userId}` : null;
  };

  // Update wallet balance function with user-specific storage
  const updateWalletBalance = (newBalance) => {
    // Validate input is a proper number
    let validValue;
    
    if (typeof newBalance === 'string') {
      validValue = parseFloat(newBalance);
    } else if (typeof newBalance === 'number') {
      validValue = newBalance;
    } else {
      console.error('Invalid balance type:', typeof newBalance, newBalance);
      return walletBalance;
    }
    
    // Check if value is valid number
    if (isNaN(validValue)) {
      console.error('Invalid balance (NaN):', newBalance);
      return walletBalance;
    }
    
    // Ensure value is positive and round to 2 decimal places
    validValue = Math.max(0, Math.round(validValue * 100) / 100);
    
    const userId = getCurrentUserId();
    console.log(`WalletContext: Updating balance for user ${userId} from ${walletBalance} to ${validValue}`);
    
    // Update state
    setWalletBalance(validValue);
    
    // Save to localStorage with user-specific key
    try {
      const storageKey = getUserStorageKey();
      if (storageKey) {
        localStorage.setItem(storageKey, String(validValue));
        localStorage.setItem(`${storageKey}_updated`, new Date().toISOString());
        console.log(`Saved wallet balance for user ${userId} to localStorage:`, validValue);
      }
    } catch (e) {
      console.error('Failed to save wallet balance to localStorage:', e);
    }
    
    return validValue;
  };

  // Function to fetch wallet balance from API
  const fetchWalletBalance = async (forceReload = false) => {
    const token = localStorage.getItem('token');
    
    if (!token) {
      console.log('No token found, setting balance to 0');
      updateWalletBalance(0);
      setLoading(false);
      return 0;
    }
    
    // Get user ID for logging
    const userId = getCurrentUserId();
    
    // Prevent multiple simultaneous API calls
    if (fetchInProgressRef.current && !forceReload) {
      console.log(`Wallet fetch for user ${userId} already in progress, skipping duplicate call`);
      return walletBalance;
    }
    
    // Rate limiting (prevent rapid API calls)
    const now = Date.now();
    if (!forceReload && lastFetchTimeRef.current > 0 && now - lastFetchTimeRef.current < 5000) {
      console.log(`Rate limiting wallet fetch for user ${userId}, last call was`, 
        (now - lastFetchTimeRef.current) / 1000, 'seconds ago');
      return walletBalance;
    }
    
    // Set loading state
    fetchInProgressRef.current = true;
    setLoading(true);
    
    try {
      console.log(`Fetching wallet balance for user ${userId} from API...`);
      const response = await axios.get(`${API_URL}/api/v1/accounts/wallet/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log(`Wallet API response for user ${userId}:`, response.data);
      
      // Parse balance from response based on API structure
      let balanceValue = 0;
      
      if (response.data?.data?.balance !== undefined) {
        balanceValue = response.data.data.balance;
      } else if (response.data?.balance !== undefined) {
        balanceValue = response.data.balance;
      } else if (response.data?.data?.wallet?.balance !== undefined) {
        balanceValue = response.data.data.wallet.balance;
      } else if (response.data?.wallet?.balance !== undefined) {
        balanceValue = response.data.wallet.balance;
      }
      
      console.log(`Extracted balance value for user ${userId}:`, balanceValue);
      
      // Update wallet balance with the API value
      const updatedBalance = updateWalletBalance(balanceValue);
      
      // Update last fetch time
      lastFetchTimeRef.current = Date.now();
      
      return updatedBalance;
    } catch (error) {
      console.error(`Error fetching wallet balance for user ${userId}:`, error);
      
      // Try to load from localStorage as fallback
      try {
        const storageKey = getUserStorageKey();
        if (storageKey) {
          const storedBalance = localStorage.getItem(storageKey);
          if (storedBalance) {
            const parsedBalance = parseFloat(storedBalance);
            if (!isNaN(parsedBalance)) {
              console.log(`Using cached balance from localStorage for user ${userId}:`, parsedBalance);
              updateWalletBalance(parsedBalance);
            }
          }
        }
      } catch (e) {
        console.error('Error reading from localStorage:', e);
      }
      
      setError(error.message || 'Failed to fetch wallet balance');
      return walletBalance;
    } finally {
      setLoading(false);
      fetchInProgressRef.current = false;
    }
  };

  // Load wallet balance on initial mount and when user changes
  useEffect(() => {
    const loadUserWallet = () => {
      const userId = getCurrentUserId();
      console.log(`WalletContext mounted, fetching initial balance for user ${userId}`);
      
      if (!userId) {
        setWalletBalance(0);
        setLoading(false);
        return;
      }
      
      // Try to load from localStorage first for immediate display
      try {
        const storageKey = getUserStorageKey();
        if (storageKey) {
          const storedBalance = localStorage.getItem(storageKey);
          if (storedBalance) {
            const parsedBalance = parseFloat(storedBalance);
            if (!isNaN(parsedBalance)) {
              console.log(`Setting initial balance from localStorage for user ${userId}:`, parsedBalance);
              setWalletBalance(parsedBalance);
            }
          }
        }
      } catch (e) {
        console.error('Error reading from localStorage:', e);
      }
      
      // Then fetch from API
      fetchWalletBalance();
    };
    
    loadUserWallet();
    
    // Add event listener for user login/logout
    window.addEventListener('storage', (event) => {
      if (event.key === 'token' || event.key === 'user_info') {
        console.log('User auth changed, reloading wallet');
        loadUserWallet();
      }
    });
    
    // Set up refresh interval (every 5 minutes)
    const intervalId = setInterval(() => {
      fetchWalletBalance();
    }, 300000); // 5 minutes
    
    return () => {
      clearInterval(intervalId);
    };
  }, []);

  // Add a specialized function to sync with server on user change
  const syncBalanceToServer = async (balance) => {
    const token = localStorage.getItem('token');
    const userId = getCurrentUserId();
    
    if (!token || !userId) {
      console.error('No token or user ID available for sync');
      return false;
    }
    
    // Convert balance to a valid number
    const numBalance = parseFloat(balance);
    if (isNaN(numBalance)) {
      console.error('Invalid balance for sync:', balance);
      return false;
    }
    
    try {
      console.log(`Syncing balance for user ${userId} to server:`, numBalance);
      
      // Make direct call to update balance
      const response = await axios.post(
        `${API_URL}/api/v1/accounts/wallet/update_balance/`,
        { balance: numBalance },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log(`Sync response for user ${userId}:`, response.data);
      
      if (response.status === 200 || response.status === 201) {
        // Update local state with the synced value
        updateWalletBalance(numBalance);
        return true;
      } else {
        console.error('Server returned non-success status:', response.status);
        return false;
      }
    } catch (error) {
      console.error(`Error syncing balance for user ${userId}:`, error);
      return false;
    }
  };

  // Clear wallet on logout
  const clearWallet = () => {
    setWalletBalance(0);
    setLoading(false);
    setError(null);
  };

  return (
    <WalletContext.Provider 
      value={{ 
        walletBalance, 
        updateWalletBalance, 
        fetchWalletBalance,
        syncBalanceToServer,
        clearWallet,
        loading,
        error
      }}
    >
      {children}
    </WalletContext.Provider>
  );
};

export const useWallet = () => {
  const context = useContext(WalletContext);
  if (context === undefined) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
};

export default WalletContext;