import React, { createContext, useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create the context
const WalletContext = createContext();

// Create a provider component
export const WalletProvider = ({ children }) => {
  const [walletBalance, setWalletBalance] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Add these refs to track API calls
  const isLoadingRef = useRef(false);
  const lastFetchTimeRef = useRef(0);
  const fetchTimeoutRef = useRef(null);

  // Update wallet balance function
  const updateWalletBalance = (value) => {
    // Ensure we have a valid number
    const numValue = parseFloat(value);
    
    if (isNaN(numValue)) {
      console.error('Invalid balance value provided:', value);
      return walletBalance;
    }
    
    // Round to 2 decimal places for currency
    const validValue = Math.round(numValue * 100) / 100;
    
    console.log('WalletContext: Updating balance from', walletBalance, 'to', validValue);
    
    // Use a function update to ensure we're working with the latest state
    setWalletBalance(prevBalance => {
      // Only update if the value is different (accounting for floating point precision)
      if (Math.abs(prevBalance - validValue) > 0.001) {
        console.log('WalletContext: Balance updated to', validValue);
        
        // Save to localStorage for persistence
        try {
          localStorage.setItem('wallet_fallback', JSON.stringify({
            balance: validValue,
            lastUpdated: new Date().toISOString()
          }));
        } catch (e) {
          console.error('Error saving wallet to localStorage:', e);
        }
        
        return validValue;
      }
      
      return prevBalance;
    });
    
    return validValue;
  };

  // Modify fetchWalletBalance to prevent duplicate calls
  const fetchWalletBalance = async (forceReload = false) => {
    const token = localStorage.getItem('token');
    
    if (!token) {
      setWalletBalance(0);
      setLoading(false);
      return 0;
    }
    
    // Prevent multiple simultaneous calls
    if (isLoadingRef.current && !forceReload) {
      console.log('Wallet fetch already in progress, skipping duplicate call');
      return walletBalance;
    }
    
    // Rate limiting - don't fetch more than once every 5 seconds unless forced
    const now = Date.now();
    if (!forceReload && now - lastFetchTimeRef.current < 5000) {
      console.log('Wallet fetch rate limited, last fetch was', 
        Math.round((now - lastFetchTimeRef.current) / 1000), 'seconds ago');
      return walletBalance;
    }
    
    // Set loading state
    isLoadingRef.current = true;
    setLoading(true);
    
    try {
      // Try loading from localStorage first
      try {
        const storedFallback = localStorage.getItem('wallet_fallback');
        if (storedFallback) {
          const data = JSON.parse(storedFallback);
          if (data.balance !== undefined) {
            const localBalance = parseFloat(data.balance);
            if (!isNaN(localBalance)) {
              setWalletBalance(localBalance);
            }
          }
        }
      } catch (e) {
        console.error('Error reading wallet from localStorage:', e);
      }
      
      // Make API call
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/accounts/wallet/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Wallet API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Extract balance from response
      let balanceValue = 0;
      if (data?.data?.balance !== undefined) {
        balanceValue = data.data.balance;
      } else if (data?.balance !== undefined) {
        balanceValue = data.balance;
      }
      
      // Update state with API value
      balanceValue = parseFloat(balanceValue);
      if (!isNaN(balanceValue)) {
        setWalletBalance(balanceValue);
        
        // Also update localStorage
        localStorage.setItem('wallet_fallback', JSON.stringify({
          balance: balanceValue,
          lastUpdated: new Date().toISOString()
        }));
      }
      
      // Update last fetch time
      lastFetchTimeRef.current = Date.now();
      return balanceValue;
    } catch (error) {
      console.error('Error fetching wallet balance:', error);
      setError(error);
      return walletBalance;
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  };

  // Sync balance to server
  const syncBalanceToServer = async () => {
    const token = localStorage.getItem('token');
    if (!token) return false;
    
    try {
      await axios.post(
        `${API_URL}/api/v1/accounts/wallet/update_balance/`,
        { balance: walletBalance },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      return true;
    } catch (error) {
      console.error('Failed to sync balance with server:', error);
      return false;
    }
  };

  // Update your useEffect to prevent infinite loops
  useEffect(() => {
    // Only fetch on initial load, not on every render
    const initialFetch = async () => {
      await fetchWalletBalance();
    };
    
    // Clear any existing timeouts
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
    }
    
    // Initial fetch
    initialFetch();
    
    // Set up an interval to refresh wallet data periodically (every 5 minutes)
    const intervalId = setInterval(() => {
      // Only fetch if not already loading
      if (!isLoadingRef.current) {
        fetchWalletBalance();
      }
    }, 300000); // 5 minutes
    
    // Clean up interval on unmount
    return () => {
      clearInterval(intervalId);
      if (fetchTimeoutRef.current) {
        clearTimeout(fetchTimeoutRef.current);
      }
    };
  }, []); // Empty dependency array = only run on mount

  return (
    <WalletContext.Provider 
      value={{ 
        walletBalance, 
        updateWalletBalance, 
        fetchWalletBalance,
        syncBalanceToServer,
        loading,
        error
      }}
    >
      {children}
    </WalletContext.Provider>
  );
};

// Create a hook to use the wallet context
export const useWallet = () => {
  const context = useContext(WalletContext);
  if (context === undefined) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
};

export default WalletContext;