import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/ProfilePage.css';

const ProfilePage = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('listings');
  const [myListings, setMyListings] = useState([]);
  const [myBids, setMyBids] = useState([]);
  const [wonAuctions, setWonAuctions] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const navigate = useNavigate();
  
  // Check if user is logged in
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('userToken');
      
      if (!token) {
        navigate('/login');
        return;
      }
      
      // In a real app, would validate token with backend
      fetchUserData();
    };
    
    checkAuth();
  }, [navigate]);
  
  const fetchUserData = async () => {
    try {
      // In a real app, fetch user profile from API
      // const response = await axios.get('/api/users/profile');
      // setUser(response.data);
      
      // Mock user data
      const mockUser = {
        id: 1001,
        name: 'John Smith',
        email: 'john.smith@example.com',
        avatar: 'https://picsum.photos/id/64/200/200',
        address: '123 Main St, New York, NY 10001',
        phone: '(555) 123-4567',
        rating: 4.7,
        joinedDate: '2021-06-15',
        bio: 'Passionate collector of vintage items and antiques. Always looking for unique pieces to add to my collection.'
      };
      
      // Mock listings data
      const mockListings = [
        {
          id: 101,
          title: 'Vintage Camera',
          currentBid: 250,
          image: 'https://picsum.photos/id/36/300/200',
          endsAt: new Date(Date.now() + 172800000).toISOString(),
          status: 'active',
          bidCount: 5
        },
        {
          id: 102,
          title: 'Antique Chair',
          currentBid: 400,
          image: 'https://picsum.photos/id/42/300/200',
          endsAt: new Date(Date.now() - 86400000).toISOString(),
          status: 'ended',
          bidCount: 8
        },
        {
          id: 103,
          title: 'Rare Book Collection',
          currentBid: 180,
          image: 'https://picsum.photos/id/24/300/200',
          endsAt: new Date(Date.now() + 432000000).toISOString(),
          status: 'active',
          bidCount: 3
        }
      ];
      
      // Mock bids data
      const mockBids = [
        {
          id: 201,
          auctionId: 301,
          auctionTitle: 'Vintage Watch Collection',
          bidAmount: 1200,
          bidTime: new Date(Date.now() - 3600000).toISOString(),
          auctionImage: 'https://picsum.photos/id/28/300/200',
          endsAt: new Date(Date.now() + 86400000).toISOString(),
          currentBid: 1250,
          status: 'outbid'
        },
        {
          id: 202,
          auctionId: 302,
          auctionTitle: 'Gaming Console Bundle',
          bidAmount: 450,
          bidTime: new Date(Date.now() - 172800000).toISOString(),
          auctionImage: 'https://picsum.photos/id/96/300/200',
          endsAt: new Date(Date.now() + 172800000).toISOString(),
          currentBid: 450,
          status: 'winning'
        },
        {
          id: 203,
          auctionId: 303,
          auctionTitle: 'Collectible Action Figures',
          bidAmount: 120,
          bidTime: new Date(Date.now() - 259200000).toISOString(),
          auctionImage: 'https://picsum.photos/id/20/300/200',
          endsAt: new Date(Date.now() - 86400000).toISOString(),
          currentBid: 150,
          status: 'lost'
        }
      ];
      
      // Mock won auctions
      const mockWonAuctions = [
        {
          id: 401,
          title: 'Antique Pocket Watch',
          finalBid: 560,
          image: 'https://picsum.photos/id/27/300/200',
          endedAt: new Date(Date.now() - 604800000).toISOString(),
          paymentStatus: 'completed',
          shippingStatus: 'delivered'
        },
        {
          id: 402,
          title: 'Vinyl Record Collection',
          finalBid: 320,
          image: 'https://picsum.photos/id/145/300/200',
          endedAt: new Date(Date.now() - 1209600000).toISOString(),
          paymentStatus: 'completed',
          shippingStatus: 'shipped'
        }
      ];
      
      // Mock watchlist
      const mockWatchlist = [
        {
          id: 501,
          title: 'Rare Coin Set',
          currentBid: 780,
          image: 'https://picsum.photos/id/30/300/200',
          endsAt: new Date(Date.now() + 345600000).toISOString(),
          bidCount: 12
        },
        {
          id: 502,
          title: 'Vintage Turntable',
          currentBid: 290,
          image: 'https://picsum.photos/id/146/300/200',
          endsAt: new Date(Date.now() + 172800000).toISOString(),
          bidCount: 7
        },
        {
          id: 503,
          title: 'Art Deco Lamp',
          currentBid: 150,
          image: 'https://picsum.photos/id/129/300/200',
          endsAt: new Date(Date.now() + 86400000).toISOString(),
          bidCount: 4
        }
      ];
      
      setUser(mockUser);
      setMyListings(mockListings);
      setMyBids(mockBids);
      setWonAuctions(mockWonAuctions);
      setWatchlist(mockWatchlist);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching user data:', error);
      setLoading(false);
    }
  };
  
  const handleLogout = () => {
    localStorage.removeItem('userToken');
    navigate('/login');
  };
  
  // Format date for display
  const formatDate = (dateString) => {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };
  
  // Format time remaining
  const formatTimeRemaining = (endDateString) => {
    const endDate = new Date(endDateString);
    const now = new Date();
    const timeRemaining = endDate - now;
    
    if (timeRemaining <= 0) return 'Ended';
    
    const days = Math.floor(timeRemaining / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeRemaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    
    return `${days}d ${hours}h remaining`;
  };
  
  if (loading) {
    return <div className="loading-container">Loading profile data...</div>;
  }

  return (
    <div className="profile-page">
      <div className="container">
        <div className="profile-header">
          <div className="profile-avatar">
            <img src={user.avatar} alt={user.name} />
          </div>
          
          <div className="profile-info">
            <h1>{user.name}</h1>
            <div className="profile-meta">
              <p>Member since: {formatDate(user.joinedDate)}</p>
              <p>Rating: {user.rating}/5</p>
            </div>
            <p className="profile-bio">{user.bio}</p>
          </div>
          
          <div className="profile-actions">
            <Link to="/profile/edit" className="btn btn-outline">Edit Profile</Link>
            <button onClick={handleLogout} className="btn btn-secondary">Log Out</button>
          </div>
        </div>
        
        <div className="profile-tabs">
          <div className="tabs-header">
            <button 
              className={`tab-btn ${activeTab === 'listings' ? 'active' : ''}`}
              onClick={() => setActiveTab('listings')}
            >
              My Listings
            </button>
            <button 
              className={`tab-btn ${activeTab === 'bids' ? 'active' : ''}`}
              onClick={() => setActiveTab('bids')}
            >
              My Bids
            </button>
            <button 
              className={`tab-btn ${activeTab === 'won' ? 'active' : ''}`}
              onClick={() => setActiveTab('won')}
            >
              Won Auctions
            </button>
            <button 
              className={`tab-btn ${activeTab === 'watchlist' ? 'active' : ''}`}
              onClick={() => setActiveTab('watchlist')}
            >
              Watchlist
            </button>
            <button 
              className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
              onClick={() => setActiveTab('settings')}
            >
              Account Settings
            </button>
          </div>
          
          <div className="tab-content">
            {/* My Listings Tab */}
            {activeTab === 'listings' && (
              <div className="tab-pane">
                <div className="tab-header">
                  <h2>My Listings</h2>
                  <Link to="/create-auction" className="btn btn-primary">Create New Listing</Link>
                </div>
                
                {myListings.length === 0 ? (
                  <div className="empty-state">
                    <p>You haven't listed any items for auction yet.</p>
                    <Link to="/create-auction" className="btn btn-primary">Create Your First Listing</Link>
                  </div>
                ) : (
                  <div className="listings-grid">
                    {myListings.map(listing => (
                      <div key={listing.id} className="listing-card">
                        <div className="listing-image">
                          <img src={listing.image} alt={listing.title} />
                          <div className={`listing-status ${listing.status}`}>
                            {listing.status === 'active' ? 'Active' : 'Ended'}
                          </div>
                        </div>
                        <div className="listing-details">
                          <h3>{listing.title}</h3>
                          <p className="current-bid">Current Bid: ${listing.currentBid}</p>
                          <p className="bid-count">{listing.bidCount} bids</p>
                          <p className="time-remaining">{formatTimeRemaining(listing.endsAt)}</p>
                          <div className="listing-actions">
                            <Link to={`/auction/${listing.id}`} className="btn btn-small">View</Link>
                            {listing.status === 'active' && (
                              <Link to={`/edit-auction/${listing.id}`} className="btn btn-small btn-outline">Edit</Link>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* My Bids Tab */}
            {activeTab === 'bids' && (
              <div className="tab-pane">
                <h2>My Bids</h2>
                
                {myBids.length === 0 ? (
                  <div className="empty-state">
                    <p>You haven't placed any bids yet.</p>
                    <Link to="/auctions" className="btn btn-primary">Browse Auctions</Link>
                  </div>
                ) : (
                  <div className="bids-list">
                    {myBids.map(bid => (
                      <div key={bid.id} className={`bid-card ${bid.status}`}>
                        <div className="bid-image">
                          <img src={bid.auctionImage} alt={bid.auctionTitle} />
                        </div>
                        <div className="bid-details">
                          <h3>{bid.auctionTitle}</h3>
                          <div className="bid-info">
                            <p>Your Bid: <span className="bold">${bid.bidAmount}</span></p>
                            <p>Current Bid: <span className="bold">${bid.currentBid}</span></p>
                            <p>Bid Status: 
                              <span className={`bid-status ${bid.status}`}>
                                {bid.status === 'winning' ? 'Winning' : 
                                 bid.status === 'outbid' ? 'Outbid' : 'Lost'}
                              </span>
                            </p>
                          </div>
                          <p className="bid-time">Bid placed on {formatDate(bid.bidTime)}</p>
                          <p className="time-remaining">{formatTimeRemaining(bid.endsAt)}</p>
                          <div className="bid-actions">
                            <Link to={`/auction/${bid.auctionId}`} className="btn btn-small">View Auction</Link>
                            {bid.status === 'outbid' && new Date(bid.endsAt) > new Date() && (
                              <Link to={`/auction/${bid.auctionId}`} className="btn btn-small btn-primary">Bid Again</Link>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* Won Auctions Tab */}
            {activeTab === 'won' && (
              <div className="tab-pane">
                <h2>Won Auctions</h2>
                
                {wonAuctions.length === 0 ? (
                  <div className="empty-state">
                    <p>You haven't won any auctions yet.</p>
                    <Link to="/auctions" className="btn btn-primary">Browse Auctions</Link>
                  </div>
                ) : (
                  <div className="won-auctions-grid">
                    {wonAuctions.map(auction => (
                      <div key={auction.id} className="won-auction-card">
                        <div className="won-auction-image">
                          <img src={auction.image} alt={auction.title} />
                        </div>
                        <div className="won-auction-details">
                          <h3>{auction.title}</h3>
                          <p className="final-bid">Final Bid: ${auction.finalBid}</p>
                          <p className="won-date">Won on {formatDate(auction.endedAt)}</p>
                          <div className="status-indicators">
                            <div className={`status-indicator ${auction.paymentStatus}`}>
                              Payment: {auction.paymentStatus}
                            </div>
                            <div className={`status-indicator ${auction.shippingStatus}`}>
                              Shipping: {auction.shippingStatus}
                            </div>
                          </div>
                          <div className="won-auction-actions">
                            <Link to={`/auction/${auction.id}`} className="btn btn-small">View Details</Link>
                            {auction.paymentStatus !== 'completed' && (
                              <Link to={`/payment/${auction.id}`} className="btn btn-small btn-primary">Complete Payment</Link>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* Watchlist Tab */}
            {activeTab === 'watchlist' && (
              <div className="tab-pane">
                <h2>Watchlist</h2>
                
                {watchlist.length === 0 ? (
                  <div className="empty-state">
                    <p>Your watchlist is empty.</p>
                    <Link to="/auctions" className="btn btn-primary">Browse Auctions</Link>
                  </div>
                ) : (
                  <div className="watchlist-grid">
                    {watchlist.map(item => (
                      <div key={item.id} className="watchlist-card">
                        <div className="watchlist-image">
                          <img src={item.image} alt={item.title} />
                        </div>
                        <div className="watchlist-details">
                          <h3>{item.title}</h3>
                          <p className="current-bid">Current Bid: ${item.currentBid}</p>
                          <p className="bid-count">{item.bidCount} bids</p>
                          <p className="time-remaining">{formatTimeRemaining(item.endsAt)}</p>
                          <div className="watchlist-actions">
                            <Link to={`/auction/${item.id}`} className="btn btn-small">View Auction</Link>
                            <button className="btn btn-small btn-outline">Remove</button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* Account Settings Tab */}
            {activeTab === 'settings' && (
              <div className="tab-pane">
                <h2>Account Settings</h2>
                
                <div className="settings-form">
                  <div className="form-section">
                    <h3>Personal Information</h3>
                    <div className="form-group">
                      <label>Full Name</label>
                      <input type="text" value={user.name} readOnly />
                    </div>
                    
                    <div className="form-group">
                      <label>Email Address</label>
                      <input type="email" value={user.email} readOnly />
                    </div>
                    
                    <div className="form-group">
                      <label>Phone Number</label>
                      <input type="tel" value={user.phone} readOnly />
                    </div>
                    
                    <div className="form-group">
                      <label>Address</label>
                      <input type="text" value={user.address} readOnly />
                    </div>
                    
                    <Link to="/profile/edit" className="btn btn-primary">Edit Information</Link>
                  </div>
                  
                  <div className="form-section">
                    <h3>Change Password</h3>
                    
                    <div className="form-group">
                      <label>Current Password</label>
                      <input type="password" placeholder="Enter current password" />
                    </div>
                    
                    <div className="form-group">
                      <label>New Password</label>
                      <input type="password" placeholder="Enter new password" />
                    </div>
                    
                    <div className="form-group">
                      <label>Confirm New Password</label>
                      <input type="password" placeholder="Confirm new password" />
                    </div>
                    
                    <button className="btn btn-primary">Update Password</button>
                  </div>
                  
                  <div className="form-section">
                    <h3>Notification Settings</h3>
                    
                    <div className="form-check">
                      <input type="checkbox" id="emailBids" checked />
                      <label htmlFor="emailBids">Email notifications for new bids</label>
                    </div>
                    
                    <div className="form-check">
                      <input type="checkbox" id="emailOutbid" checked />
                      <label htmlFor="emailOutbid">Email notifications when outbid</label>
                    </div>
                    
                    <div className="form-check">
                      <input type="checkbox" id="emailEnding" checked />
                      <label htmlFor="emailEnding">Email notifications when watched auctions are ending</label>
                    </div>
                    
                    <button className="btn btn-primary">Save Notification Preferences</button>
                  </div>
                  
                  <div className="danger-zone">
                    <h3>Danger Zone</h3>
                    <button className="btn btn-danger">Delete Account</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;