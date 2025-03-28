import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/ProfilePage.css';
import apiService from '../services/api';

// Define API_URL
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const ProfilePage = () => {
  const { id: sellerId } = useParams(); // Get sellerId from URL if present
  const navigate = useNavigate();
  const [userData, setUserData] = useState(null);
  const [userAuctions, setUserAuctions] = useState([]);
  const [userTransactions, setUserTransactions] = useState([]);
  const [autoBids, setAutoBids] = useState([]);
  const [activeTab, setActiveTab] = useState('auctions');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCurrentUser, setIsCurrentUser] = useState(false);
  
  // Helper function for currency formatting
  const formatCurrency = (value) => {
    const numValue = parseFloat(value);
    return isNaN(numValue) ? '0.00' : numValue.toFixed(2);
  };
  
  const fetchUserTransactions = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const headers = { 'Authorization': `Bearer ${token}` };
      const response = await axios.get(`${API_URL}/api/v1/transactions/transactions/`, { headers });
      
      const transactionsData = response.data.data || response.data || [];
      setUserTransactions(transactionsData);
    } catch (error) {
      console.error('Error fetching transactions:', error);
    }
  };

  const fetchAutoBids = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const response = await axios.get(`${API_URL}/api/v1/auctions/autobids/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const autobidsData = response.data?.data || response.data || [];
      setAutoBids(autobidsData);
    } catch (error) {
      console.error('Error fetching auto-bids:', error);
    }
  };

  const toggleAutoBid = async (bidId, activate) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const endpoint = activate ? 'activate' : 'deactivate';
      await axios.post(`${API_URL}/api/v1/auctions/autobids/${bidId}/${endpoint}/`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      // Refresh the auto-bids list
      fetchAutoBids();
    } catch (error) {
      console.error(`Error ${activate ? 'activating' : 'deactivating'} auto-bid:`, error);
      alert(`Failed to ${activate ? 'activate' : 'deactivate'} auto-bidding. Please try again.`);
    }
  };

  const handleProfileUpdate = (updatedData) => {
    setUserData({
      ...userData,
      ...updatedData
    });
  };

  useEffect(() => {
    const fetchUserData = async () => {
      console.log('Environment:', process.env.NODE_ENV);
      console.log('Seller ID from URL:', sellerId);
      console.log('API URL being used:', API_URL);

      try {
        setLoading(true);
        const token = localStorage.getItem('token');
        
        if (!token && !sellerId) {
          // Redirect to login if no token and not viewing a specific seller
          navigate('/login');
          return;
        }
        
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        let userResponse;
        
        if (sellerId) {
          // Fetching another seller's profile
          try {
            userResponse = await axios.get(`${API_URL}/api/v1/accounts/users/${sellerId}/`, { headers });
          } catch (userError) {
            // Try alternative endpoint
            userResponse = await axios.get(`${API_URL}/api/v1/accounts/seller/${sellerId}/`, { headers });
          }
          setIsCurrentUser(false);
        } else {
          // Fetching current user's profile
          userResponse = await axios.get(`${API_URL}/api/v1/accounts/profile/`, { headers });
          setIsCurrentUser(true);
        }
        
        // Extract user data from response depending on API structure
        const userData = userResponse.data.data || userResponse.data;
        setUserData(userData);
        
        // Fetch user's auctions using the updated API service
        try {
          let auctionsData = [];
          
          if (isCurrentUser) {
            // For current user, use the my_auctions endpoint
            const response = await apiService.getMyAuctions();
            auctionsData = response.data?.data || response.data || [];
          } else {
            // For other users, use the general endpoint with filtering
            const response = await apiService.getAuctions({ seller_id: sellerId });
            auctionsData = response.data?.data || response.data || [];
          }
          
          console.log('Auctions data:', auctionsData);
          
          // Ensure we handle all possible data structures
          if (!Array.isArray(auctionsData)) {
            if (auctionsData.auctions && Array.isArray(auctionsData.auctions)) {
              auctionsData = auctionsData.auctions;
            } else {
              auctionsData = [];
            }
          }
          
          setUserAuctions(auctionsData);
        } catch (auctionError) {
          console.error('Failed to fetch auctions:', auctionError);
          setUserAuctions([]);
        }
        
        setLoading(false);
      } catch (error) {
        console.error('Error fetching profile data:', error);
        
        // Always use mock data in development when API fails
        if (process.env.NODE_ENV === 'development') {
          console.log('Using mock data for development');
          const mockUser = {
            id: sellerId || '123',
            username: 'testuser',
            first_name: 'Test',
            last_name: 'User',
            email: 'test@example.com',
            date_joined: '2020-01-01T00:00:00Z',
            bio: 'This is a test user bio.',
            location: 'Test City, TS'
          };
          
          const mockAuctions = [
            {
              id: '1',
              title: 'Vintage Watch',
              current_price: 120.50,
              images: ['https://picsum.photos/id/28/800/600'],
              end_time: new Date(Date.now() + 86400000).toISOString()
            },
            {
              id: '2',
              title: 'Antique Chair',
              current_price: 350.75,
              images: ['https://picsum.photos/id/30/800/600'],
              end_time: new Date(Date.now() + 172800000).toISOString()
            }
          ];
          
          setUserData(mockUser);
          setUserAuctions(mockAuctions);
          setLoading(false);
          setError(''); // Clear the error so the mock data shows
          return; // Exit early to prevent showing the error
        }
        
        // Only show error if we're not in development or mock data isn't available
        setError('Failed to load profile. Please try again later.');
        setLoading(false);
      }
    };
    
    fetchUserData();
    
    if (isCurrentUser) {
      fetchUserTransactions();
      fetchAutoBids();
    }
  }, [sellerId, navigate, isCurrentUser]);
  
  if (loading) {
    return (
      <div className="loading-container">
        <p>Loading profile data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <p>{error}</p>
        <Link to="/" className="btn btn-primary">Back to Home</Link>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="container">
        <div className="profile-header">
          <div className="profile-avatar">
            {userData?.avatar_url ? (
              <img src={userData.avatar_url} alt="Profile avatar" />
            ) : (
              <div className="default-avatar">
                {userData?.first_name?.charAt(0) || userData?.username?.charAt(0) || '?'}
              </div>
            )}
          </div>
          
          <div className="profile-info">
            <h2>{userData?.first_name} {userData?.last_name}</h2>
            
            <div className="profile-details">
              <p>
                <strong>Username:</strong> {userData?.username}
              </p>
              
              <p>
                <strong>Email:</strong> {userData?.email}
              </p>
              
              <p>
                <strong>Member since:</strong> {
                  userData?.signup_datetime || userData?.date_joined 
                    ? new Date(userData?.signup_datetime || userData?.date_joined).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })
                    : 'N/A'
                }
              </p>
              
              <p>
                <strong>Location:</strong> {userData?.location || 'Not specified'}
              </p>
            </div>
            
            {isCurrentUser && (
              <div className="profile-actions">
                <Link 
                  to="/profile/edit" 
                  className="btn btn-primary"
                >
                  Edit Profile
                </Link>
                
                <button 
                  className="btn btn-secondary" 
                  onClick={() => navigate('/wallet')}
                >
                  Manage Wallet
                </button>
              </div>
            )}
          </div>
        </div>
        
        <div className="profile-content">
          <div className="user-info">
            <div className="user-details">
              {userData?.bio && (
                <div className="user-bio">
                  <h3>About</h3>
                  <p>{userData.bio}</p>
                </div>
              )}
            </div>
          </div>
          
          <div className="profile-tabs">
            <div className="tabs-header">
              <button 
                onClick={() => setActiveTab('auctions')} 
                className={`tab-btn ${activeTab === 'auctions' ? 'active' : ''}`}
              >
                {isCurrentUser ? 'My Auctions' : `${userData?.username}'s Auctions`}
              </button>
              
              {isCurrentUser && (
                <button 
                  onClick={() => setActiveTab('transactions')} 
                  className={`tab-btn ${activeTab === 'transactions' ? 'active' : ''}`}
                >
                  My Purchases
                </button>
              )}
              
              {isCurrentUser && (
                <button 
                  onClick={() => setActiveTab('autobids')} 
                  className={`tab-btn ${activeTab === 'autobids' ? 'active' : ''}`}
                >
                  My Auto-Bids
                </button>
              )}
            </div>
            
            {activeTab === 'auctions' && (
              <div className="user-auctions">
                <h2>{isCurrentUser ? 'My Auctions' : `${userData?.username || userData?.first_name}'s Auctions`}</h2>
                
                {userAuctions.length > 0 ? (
                  <div className="auctions-grid">
                    {userAuctions.map(auction => {
                      // Handle different property naming conventions
                      const auctionId = auction.id || auction._id;
                      const title = auction.title || auction.name;
                      const price = auction.current_price || auction.currentPrice || auction.starting_price || auction.startingPrice || 0;
                      const imageUrls = auction.images || auction.imageUrls || auction.item?.image_urls || auction.item?.imageUrls || [];
                      const imageUrl = Array.isArray(imageUrls) && imageUrls.length > 0 
                        ? imageUrls[0]
                        : 'https://via.placeholder.com/300x200?text=No+Image';
                        
                      return (
                        <div key={auctionId} className="auction-card">
                          <img src={imageUrl} alt={title} />
                          <div className="auction-card-info">
                            <h3>{title}</h3>
                            <p className="current-bid">${formatCurrency(price)}</p>
                            <Link 
                              to={`/auction/${auctionId}`} 
                              className="btn btn-primary btn-sm"
                            >
                              View Auction
                            </Link>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="no-auctions-message">
                    {isCurrentUser 
                      ? 'You have no active auctions. Why not create one?' 
                      : 'This seller has no active auctions.'}
                  </p>
                )}
                
                {isCurrentUser && (
                  <div className="create-auction-link">
                    <Link to="/create-auction" className="btn btn-secondary">
                      Create New Auction
                    </Link>
                  </div>
                )}
                
                {process.env.NODE_ENV === 'development' && isCurrentUser && (
                  <div className="debug-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '5px' }}>
                    <h3>Development Tools</h3>
                    <button 
                      className="btn btn-secondary" 
                      style={{ marginRight: '10px' }}
                      onClick={async () => {
                        try {
                          console.log('Testing auction endpoints...');
                          
                          // Define headers here since we're outside fetchUserData scope
                          const token = localStorage.getItem('token');
                          const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
                          
                          // Try various endpoints
                          const endpoints = [
                            '/api/v1/auctions/auctions/my_auctions/',
                            '/api/v1/auctions/auctions/?seller_id=' + userData.id,
                            '/api/v1/auctions/auctions/user/' + userData.id,
                          ];
                          
                          for (const endpoint of endpoints) {
                            try {
                              console.log(`Testing endpoint: ${endpoint}`);
                              const response = await axios.get(`${API_URL}${endpoint}`, { headers });
                              console.log(`Response from ${endpoint}:`, response.data);
                            } catch (error) {
                              console.error(`Error with ${endpoint}:`, error.response || error);
                            }
                          }
                          
                          alert('Check the console for details');
                        } catch (error) {
                          console.error('Error testing endpoints:', error);
                          alert('Error: ' + (error.message || 'Unknown error'));
                        }
                      }}
                    >
                      Test Auction Endpoints
                    </button>
                  </div>
                )}
              </div>
            )}
            
            {activeTab === 'transactions' && isCurrentUser && (
              <div className="user-transactions">
                <h2>My Purchases</h2>
                
                {userTransactions.length > 0 ? (
                  <div className="transactions-list">
                    {userTransactions.filter(tx => tx.transaction_type === 'purchase').map(transaction => (
                      <div key={transaction.id} className="transaction-card">
                        <div className="transaction-details">
                          <h3>{transaction.reference}</h3>
                          <p className="transaction-amount">Amount: ${formatCurrency(transaction.amount)}</p>
                          <p className="transaction-date">Date: {new Date(transaction.created_at).toLocaleDateString()}</p>
                          <p className="transaction-status">Status: {transaction.status}</p>
                        </div>
                        <Link to={`/auction/${transaction.reference_id}`} className="btn btn-outline-small">
                          View Auction
                        </Link>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>You haven't made any purchases yet.</p>
                )}
              </div>
            )}
            
            {activeTab === 'autobids' && isCurrentUser && (
              <div className="profile-section">
                <h2>Your Auto-Bidding</h2>
                
                {autoBids.length === 0 ? (
                  <p>You haven't set up auto-bidding on any auctions.</p>
                ) : (
                  <div className="auto-bids-list">
                    <table className="auto-bids-table">
                      <thead>
                        <tr>
                          <th>Auction</th>
                          <th>Max Bid</th>
                          <th>Current Price</th>
                          <th>Status</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {autoBids.map(bid => (
                          <tr key={bid.id}>
                            <td>
                              <Link to={`/auction/${bid.auction.id}`}>
                                {bid.auction.title}
                              </Link>
                            </td>
                            <td>${parseFloat(bid.max_amount).toFixed(2)}</td>
                            <td>${parseFloat(bid.auction.current_price).toFixed(2)}</td>
                            <td>
                              <span className={`status ${bid.is_active ? 'active' : 'inactive'}`}>
                                {bid.is_active ? 'Active' : 'Paused'}
                              </span>
                            </td>
                            <td>
                              <button 
                                onClick={() => toggleAutoBid(bid.id, !bid.is_active)}
                                className={`btn btn-sm ${bid.is_active ? 'btn-outline' : 'btn-primary'}`}
                              >
                                {bid.is_active ? 'Pause' : 'Resume'}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;