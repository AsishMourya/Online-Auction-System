import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/Navbar.css';
import NotificationCenter from '../components/NotificationCenter';
import { useWallet } from '../contexts/WalletContext';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const Navbar = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const { walletBalance } = useWallet();
  const navigate = useNavigate();
  const [userInfo, setUserInfo] = useState(null);

  // Check login status whenever the component mounts or token changes
  useEffect(() => {
    const checkAuthStatus = () => {
      const token = localStorage.getItem('token');
      if (token) {
        setIsLoggedIn(true);
      } else {
        setIsLoggedIn(false);
      }
    };

    checkAuthStatus();
    
    // Add event listener for storage changes (in case another tab logs out)
    window.addEventListener('storage', checkAuthStatus);
    
    // Create a custom event listener for auth state changes
    window.addEventListener('authStateChanged', checkAuthStatus);
    
    return () => {
      window.removeEventListener('storage', checkAuthStatus);
      window.removeEventListener('authStateChanged', checkAuthStatus);
    };
  }, []);

  // Log wallet balance changes
  useEffect(() => {
    console.log('Navbar: Current wallet balance:', walletBalance);
  }, [walletBalance]);

  // Add auth change listener
  useEffect(() => {
    const handleAuthChange = async (e) => {
      const isAuthenticated = e?.detail?.authenticated ?? !!localStorage.getItem('token');
      setIsLoggedIn(isAuthenticated);
      
      if (isAuthenticated) {
        // Get user info
        try {
          const storedUserInfo = localStorage.getItem('user_info');
          if (storedUserInfo) {
            setUserInfo(JSON.parse(storedUserInfo));
          } else {
            // Fetch user info
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API_URL}/api/v1/accounts/user/`, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            });
            
            if (response.data) {
              const userData = response.data.data || response.data;
              setUserInfo(userData);
              localStorage.setItem('user_info', JSON.stringify(userData));
            }
          }
        } catch (e) {
          console.error('Error processing user info:', e);
        }
      } else {
        // Clear user info on logout
        setUserInfo(null);
      }
    };
    
    // Listen for auth change events
    window.addEventListener('auth-change', handleAuthChange);
    
    // Check initial auth status
    handleAuthChange();
    
    return () => {
      window.removeEventListener('auth-change', handleAuthChange);
    };
  }, []);

  const handleLogout = () => {
    // Clear all auth-related data
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    localStorage.removeItem('user_info');
    
    // Update auth state
    setIsLoggedIn(false);
    setUserInfo(null);
    
    // Dispatch event to notify other components
    window.dispatchEvent(new Event('authStateChanged'));
    
    // Redirect to home
    navigate('/');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          Auction House
        </Link>

        <div className="menu-icon" onClick={() => setMenuOpen(!menuOpen)}>
          <i className={menuOpen ? 'fas fa-times' : 'fas fa-bars'} />
        </div>
        
        <ul className={menuOpen ? 'nav-menu active' : 'nav-menu'}>
          {/* Removed Home link since logo serves the same purpose */}
          <li className="nav-item">
            <Link to="/auctions" className="nav-link" onClick={() => setMenuOpen(false)}>
              Auctions
            </Link>
          </li>
          
          {isLoggedIn ? (
            <>
              <li className="nav-item">
                <Link to="/create-auction" className="nav-link" onClick={() => setMenuOpen(false)}>
                  Create Auction
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/profile" className="nav-link" onClick={() => setMenuOpen(false)}>
                  Profile
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/wallet" className="wallet-balance" onClick={(e) => {
                  // Prevent navigation if already on wallet page
                  if (window.location.pathname === '/wallet') {
                    e.preventDefault();
                  }
                }}>
                  <span className="wallet-icon">💰</span>
                  <span className="balance-amount">
                    ${walletBalance !== null && walletBalance !== undefined 
                      ? parseFloat(walletBalance).toFixed(2) 
                      : '0.00'}
                  </span>
                </Link>
              </li>
              <li className="nav-item">
                <button className="nav-link logout-btn" onClick={handleLogout}>
                  Logout
                </button>
              </li>
              <li className="nav-item nav-notifications">
                <NotificationCenter />
              </li>
              <li className="nav-item user-section">
                {userInfo && (
                  <span className="user-greeting">
                    Hello, {userInfo.username || userInfo.name || 'User'}
                  </span>
                )}
              </li>
            </>
          ) : (
            <>
              <li className="nav-item">
                <Link to="/login" className="nav-link" onClick={() => setMenuOpen(false)}>
                  Login
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/register" className="nav-link" onClick={() => setMenuOpen(false)}>
                  Register
                </Link>
              </li>
            </>
          )}
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;