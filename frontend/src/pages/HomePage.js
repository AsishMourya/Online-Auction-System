import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import '../styles/HomePage.css';

// Create an API base URL - in production, use environment variable
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create a simple API service for this component
const api = {
  getFeaturedAuctions: () => axios.get(`${API_URL}/api/v1/auctions/auctions/`, { 
    params: { featured: true, limit: 3 } 
  }),
  getCategories: () => axios.get(`${API_URL}/api/v1/auctions/categories/all/`)
};

const HomePage = () => {
  const [featuredAuctions, setFeaturedAuctions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Make parallel API requests
        const [auctionsResponse, categoriesResponse] = await Promise.all([
          api.getFeaturedAuctions(),
          api.getCategories()
        ]);
        
        // Process auction data from the API
        const auctionsData = auctionsResponse.data.data?.auctions || [];
        const processedAuctions = auctionsData.map(auction => ({
          id: auction.id,
          title: auction.title,
          currentBid: auction.current_price || auction.starting_price,
          image: auction.item_data?.image_urls?.[0] || 'https://picsum.photos/id/28/300/200',
          endsAt: auction.end_time
        }));
        
        // Process category data from the API
        const categoriesData = categoriesResponse.data.data?.categories || [];
        const categoryIcons = {
          'Electronics': '💻',
          'Collectibles': '🏆',
          'Fashion': '👕',
          'Home & Garden': '🏡',
          'Vehicles': '🚗',
          'Art': '🎨',
          'Jewelry': '💍',
          'Books': '📚',
          'Sports': '⚽',
          'Toys': '🧸'
        };
        
        const processedCategories = categoriesData.map(category => ({
          id: category.id,
          name: category.name,
          icon: categoryIcons[category.name] || '📦'
        }));
        
        setFeaturedAuctions(processedAuctions);
        setCategories(processedCategories);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching data:', error);
        setError('Could not load data from the server. Showing sample data instead.');
        
        // Mock data as fallback
        setFeaturedAuctions([
          { id: 1, title: 'Vintage Watch Collection', currentBid: 1200, image: 'https://picsum.photos/id/28/300/200', endsAt: new Date(Date.now() + 86400000).toISOString() },
          { id: 2, title: 'Gaming Console Bundle', currentBid: 450, image: 'https://picsum.photos/id/96/300/200', endsAt: new Date(Date.now() + 172800000).toISOString() },
          { id: 3, title: 'Antique Furniture Set', currentBid: 850, image: 'https://picsum.photos/id/116/300/200', endsAt: new Date(Date.now() + 259200000).toISOString() },
        ]);
        
        setCategories([
          { id: 1, name: 'Electronics', icon: '💻' },
          { id: 2, name: 'Collectibles', icon: '🏆' },
          { id: 3, name: 'Fashion', icon: '👕' },
          { id: 4, name: 'Home & Garden', icon: '🏡' },
          { id: 5, name: 'Vehicles', icon: '🚗' },
        ]);
        
        setLoading(false);
      }
    };

    // Call the function to fetch data
    fetchData();
  }, []);

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
      {/* Hero section */}
      <section className="hero">
        <div className="hero-content">
          <h1>Bid, Win, Celebrate!</h1>
          <p>Discover unique items and place your bids in our secure online auction platform.</p>
          <div className="hero-buttons">
            <Link to="/auctions" className="btn btn-primary">Browse Auctions</Link>
            <Link to="/register" className="btn btn-secondary">Join Now</Link>
          </div>
        </div>
      </section>

      {/* Display error message if API call failed */}
      {error && (
        <div className="container error-banner">
          <p>{error}</p>
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
                      <p className="current-bid">Current Bid: ${auction.currentBid.toFixed(2)}</p>
                      <p className="time-remaining">{formatTimeRemaining(auction.endsAt)}</p>
                      <Link to={`/auction/${auction.id}`} className="btn btn-outline">View Auction</Link>
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
          <Link to="/register" className="btn btn-primary">Sign Up Now</Link>
        </div>
      </section>
    </div>
  );
};

export default HomePage;