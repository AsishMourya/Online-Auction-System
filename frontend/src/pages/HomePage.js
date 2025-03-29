import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import '../styles/HomePage.css';

// Create an API base URL - in production, use environment variable
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Update the API service with the endpoints that are working
const api = {
  getFeaturedAuctions: () => {
    const token = localStorage.getItem('token');
    console.log('Token for featured auctions API call:', token ? 'Found' : 'Not found');
    
    // Use the endpoint that we know works from the database check
    return axios.get(`${API_URL}/api/v1/auctions/api/test/`, { 
      headers: token ? {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      } : {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
  },
  
  // Use the same working endpoint for categories to avoid 404
  getCategories: () => {
    const token = localStorage.getItem('token');
    
    // Use the same test endpoint since it returns both auctions and categories
    return axios.get(`${API_URL}/api/v1/auctions/api/test/`, {
      headers: token ? {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      } : {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
  }
};

const HomePage = () => {
  const [featuredAuctions, setFeaturedAuctions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('token'));

  // Check authentication status whenever auth state changes
  useEffect(() => {
    const checkAuthStatus = () => {
      setIsLoggedIn(!!localStorage.getItem('token'));
    };
    
    // Check on component mount
    checkAuthStatus();
    
    // Add event listener for auth state changes
    window.addEventListener('authStateChanged', checkAuthStatus);
    
    // Add event listener for storage changes (in case token is removed in another tab)
    window.addEventListener('storage', (event) => {
      if (event.key === 'token') {
        checkAuthStatus();
      }
    });
    
    return () => {
      window.removeEventListener('authStateChanged', checkAuthStatus);
      window.removeEventListener('storage', checkAuthStatus);
    };
  }, []);

  // Update your fetchData function
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        console.log('Making API request to test endpoint');
        
        // Only make a single API call to the test endpoint
        const apiResponse = await api.getFeaturedAuctions();
        console.log('API test response:', apiResponse.data);
        
        // Extract both auctions and categories from the same response
        let auctionsData = [];
        let categoriesData = [];
        
        if (apiResponse.data?.data?.auctions && Array.isArray(apiResponse.data.data.auctions)) {
          auctionsData = apiResponse.data.data.auctions;
          console.log('Found auctions in test endpoint response:', auctionsData.length);
        }
        
        if (apiResponse.data?.data?.categories && Array.isArray(apiResponse.data.data.categories)) {
          categoriesData = apiResponse.data.data.categories;
          console.log('Found categories in test endpoint response:', categoriesData.length);
        }
        
        // Process auctions data
        const processedAuctions = auctionsData.map(auction => ({
          id: auction.id,
          title: auction.title || 'Untitled Auction',
          currentBid: auction.current_price || auction.starting_price || 0,
          image: getAuctionImage(auction),
          endsAt: auction.end_time || new Date(Date.now() + 86400000).toISOString()
        }));
        
        // Process categories data
        const processedCategories = categoriesData.map(category => ({
          id: category.id,
          name: category.name || 'Unnamed Category',
          description: category.description || '',
          icon: getCategoryIcon(category.name || ''),
          image: category.image || `https://picsum.photos/id/${(parseInt(category.id) % 100) + 20}/300/200`
        }));
        
        setFeaturedAuctions(processedAuctions);
        setCategories(processedCategories);
        setLoading(false);
        setError(null);
      } catch (error) {
        console.error('Error fetching data:', error);
        
        let errorMessage = 'Could not load data from the server. Showing sample data instead.';
        
        if (error.response) {
          console.error('Error response data:', error.response.data);
          console.error('Error response status:', error.response.status);
          
          if (error.response.status === 401) {
            errorMessage = 'Authentication required. Please log in.';
          } else if (error.response.data?.message) {
            errorMessage = `Server error: ${error.response.data.message}`;
          } else if (error.response.data?.detail) {
            errorMessage = `Server error: ${error.response.data.detail}`;
          } else if (typeof error.response.data === 'string') {
            errorMessage = `Server error: ${error.response.data}`;
          } else {
            errorMessage = `Server error (${error.response.status}): The server returned an error response`;
          }
        } else if (error.request) {
          errorMessage = 'No response from server. Please check your connection.';
        } else {
          errorMessage = `Error: ${error.message}`;
        }
        
        setError(errorMessage);
        
        // Continue with fallback data
        const mockAuctions = [
          { id: 1, title: 'Vintage Watch Collection', currentBid: 1200, image: 'https://picsum.photos/id/28/300/200', endsAt: new Date(Date.now() + 86400000).toISOString() },
          { id: 2, title: 'Gaming Console Bundle', currentBid: 450, image: 'https://picsum.photos/id/96/300/200', endsAt: new Date(Date.now() + 172800000).toISOString() },
          { id: 3, title: 'Antique Furniture Set', currentBid: 850, image: 'https://picsum.photos/id/116/300/200', endsAt: new Date(Date.now() + 259200000).toISOString() },
        ];
        
        const mockCategories = [
          { id: 1, name: 'Electronics', description: 'Devices and gadgets', icon: '💻', image: 'https://picsum.photos/id/21/300/200' },
          { id: 2, name: 'Collectibles', description: 'Rare and unique items', icon: '🏆', image: 'https://picsum.photos/id/22/300/200' },
          { id: 3, name: 'Fashion', description: 'Clothing and accessories', icon: '👕', image: 'https://picsum.photos/id/23/300/200' },
          { id: 4, name: 'Home & Garden', description: 'Furniture and decor', icon: '🏡', image: 'https://picsum.photos/id/24/300/200' },
          { id: 5, name: 'Vehicles', description: 'Cars and bikes', icon: '🚗', image: 'https://picsum.photos/id/25/300/200' },
        ];
        
        setFeaturedAuctions(mockAuctions);
        setCategories(mockCategories);
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  // Add these helper functions
  const getAuctionImage = (auction) => {
    if (auction.images && Array.isArray(auction.images) && auction.images.length > 0) {
      return auction.images[0];
    } else if (auction.item?.image_urls && Array.isArray(auction.item.image_urls) && auction.item.image_urls.length > 0) {
      return auction.item.image_urls[0];
    } else if (auction.image_url) {
      return auction.image_url;
    } else if (auction.image) {
      return auction.image;
    }
    return 'https://picsum.photos/id/28/300/200';
  };

  const getCategoryIcon = (categoryName) => {
    const lowerName = (categoryName || '').toLowerCase();
    if (lowerName.includes('electron')) return '💻';
    if (lowerName.includes('collect')) return '🏆';
    if (lowerName.includes('fashion') || lowerName.includes('cloth')) return '👕';
    if (lowerName.includes('home') || lowerName.includes('garden')) return '🏡';
    if (lowerName.includes('vehicle') || lowerName.includes('car')) return '🚗';
    if (lowerName.includes('sport')) return '⚽';
    if (lowerName.includes('jewelry')) return '💍';
    if (lowerName.includes('toy')) return '🧸';
    if (lowerName.includes('art')) return '🎨';
    if (lowerName.includes('book')) return '📚';
    return '📦';
  };

  // Helper function to format time remaining
  const formatTimeRemaining = (endDateString) => {
    const endDate = new Date(endDateString);
    const now = new Date();
    const timeRemaining = endDate - now;
    
    if (timeRemaining <= 0) return 'Ended';
    
    const days = Math.floor(timeRemaining / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeRemaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    
    return `${days}d ${hours}h remaining`;
  };

  return (
    <div className="homepage">
        <section className="hero">
          <div className="hero-content">
            <h1>Bid, Win, Celebrate!</h1>
            <p>Discover unique items and place your bids in our secure online auction platform.</p>
            <div className="hero-buttons">
              <Link to="/auctions" className="btn btn-primary">Browse Auctions</Link>
              {!isLoggedIn && (
                <Link to="/register" className="btn btn-secondary">Join Now</Link>
              )}
            </div>
          </div>
        </section>

        {/* Display error message if API call failed */}
        {error && (
          <div className="container error-banner">
            <p>{error}</p>
            <div className="error-actions">
              <button 
                className="btn btn-secondary"
                onClick={() => window.location.reload()}
              >
                Try Again
              </button>
              <button 
                className="btn btn-secondary"
                onClick={async () => {
                  try {
                    // Direct database query test endpoint
                    const response = await axios.get(`${API_URL}/api/v1/auctions/api/test/`);
                    console.log('Database test response:', response.data);
                    
                    if (response.data.data.auction_count === 0) {
                      alert('Your database contains 0 auctions. You need to add auctions to your database.');
                    } else {
                      alert(`Found ${response.data.data.auction_count} auctions and ${response.data.data.category_count} categories in database. Check console for details.`);
                    }
                  } catch (e) {
                    alert(`Could not check database content: ${e.message}. Make sure you added the test endpoint to your Django backend.`);
                  }
                }}
              >
                Check Database
              </button>
            </div>
            <div className="api-debug-info">
              <p>API URL: {API_URL}</p>
              <p>If you're seeing this error, please check:</p>
              <ul>
                <li>Django server is running and accessible at {API_URL}</li>
                <li>API endpoints are correctly configured in Django urls.py</li>
                <li>Django REST Framework is properly set up</li>
                <li>CORS headers are configured to allow requests from your frontend</li>
              </ul>
            </div>
          </div>
        )}

        {/* Featured auctions section */}
        <section className="featured-section">
          <div className="container">
            <h2>Featured Auctions</h2>
            {loading ? (
              <div className="loading-container">
                <p>Loading featured auctions...</p>
              </div>
            ) : (
              <>
                <div className="auction-grid">
                  {featuredAuctions.map(auction => (
                    <div key={auction.id} className="auction-card">
                      <div className="auction-image">
                        <img src={auction.image} alt={auction.title} />
                      </div>
                      <div className="auction-details">
                        <h3>{auction.title}</h3>
                        <p className="current-bid">Current Bid: ${(parseFloat(auction.currentBid) || 0).toFixed(2)}</p>
                        <p className="time-remaining">{formatTimeRemaining(auction.endsAt)}</p>
                        <Link to={`/auction/${auction.id.toString()}`} className="btn btn-outline">View Auction</Link>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="view-all-container">
                  <Link to="/auctions" className="view-all">View All Auctions →</Link>
                </div>
              </>
            )}
          </div>
        </section>

        {/* Categories section */}
        <section className="categories-section">
          <div className="container">
            <h2>Explore Categories</h2>
            {loading ? (
              <div className="loading-container">
                <p>Loading categories...</p>
              </div>
            ) : (
              <div className="categories-grid">
                {categories.map(category => (
                  <Link to={`/category/${category.id}`} key={category.id} className="category-card">
                    <div className="category-icon">{category.icon}</div>
                    <h3>{category.name}</h3>
                    {category.description && <p>{category.description}</p>}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* How it works section */}
        <section className="how-it-works">
          <div className="container">
            <h2>How It Works</h2>
            <div className="steps-container">
              <div className="step">
                <div className="step-number">1</div>
                <h3>Register</h3>
                <p>Create your free account to start bidding on items.</p>
              </div>
              <div className="step">
                <div className="step-number">2</div>
                <h3>Browse & Bid</h3>
                <p>Find interesting items and place your bids.</p>
              </div>
              <div className="step">
                <div className="step-number">3</div>
                <h3>Win & Pay</h3>
                <p>If you're the highest bidder, complete the payment.</p>
              </div>
              <div className="step">
                <div className="step-number">4</div>
                <h3>Receive Item</h3>
                <p>Get your item delivered to your doorstep.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Testimonials section */}
        <section className="testimonials-section">
          <div className="container">
            <h2>What Our Users Say</h2>
            <div className="testimonials-container">
              <div className="testimonial">
                <p>"I found a rare collector's item that I'd been searching for years. Great platform!"</p>
                <div className="user">
                  <strong>Sarah M.</strong>
                </div>
              </div>
              <div className="testimonial">
                <p>"The bidding process is smooth and transparent. I've both sold and purchased items here."</p>
                <div className="user">
                  <strong>Michael K.</strong>
                </div>
              </div>
              <div className="testimonial">
                <p>"Customer support was excellent when I had questions about a payment."</p>
                <div className="user">
                  <strong>Priya R.</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Call-to-action section */}
        <section className="cta-section">
          <div className="container">
            <h2>Ready to Start Bidding?</h2>
            <p>Join thousands of users finding great deals every day.</p>
            {!isLoggedIn ? (
              <Link to="/register" className="btn btn-primary">Sign Up Now</Link>
            ) : (
              <Link to="/auctions" className="btn btn-primary">Find Great Deals</Link>
            )}
          </div>
        </section>
    </div>
  );
};

export default HomePage;