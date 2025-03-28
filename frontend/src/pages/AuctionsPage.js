import React, { useState, useEffect } from 'react';
import { Link, useParams, useLocation } from 'react-router-dom';
import axios from 'axios';
import '../styles/AuctionsPage.css';

const AuctionsPage = () => {
  const { categoryId } = useParams();
  const location = useLocation();

  const [auctions, setAuctions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState('endingSoon');
  const [searchTerm, setSearchTerm] = useState('');
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');

  useEffect(() => {
    if (categoryId) {
      setSelectedCategory(categoryId);
    }
  }, [categoryId, location.pathname]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const mockAuctions = [
          { 
            id: 1, 
            title: 'Vintage Watch Collection', 
            description: 'A collection of rare vintage watches from the 1950s.',
            currentBid: 1200, 
            image: 'https://picsum.photos/id/28/300/200', 
            endsAt: new Date(Date.now() + 86400000).toISOString(),
            bidCount: 15,
            seller: 'VintageCollector',
            categoryId: 2
          },
          { 
            id: 2, 
            title: 'Gaming Console Bundle', 
            description: 'Latest gaming console with 3 games and 2 controllers.',
            currentBid: 450, 
            image: 'https://picsum.photos/id/96/300/200', 
            endsAt: new Date(Date.now() + 172800000).toISOString(),
            bidCount: 7,
            seller: 'GameMaster',
            categoryId: 1
          },
          { 
            id: 3, 
            title: 'Antique Furniture Set', 
            description: 'Beautiful Victorian-era furniture set in excellent condition.',
            currentBid: 850, 
            image: 'https://picsum.photos/id/116/300/200', 
            endsAt: new Date(Date.now() + 259200000).toISOString(),
            bidCount: 10,
            seller: 'AntiqueLover',
            categoryId: 4
          },
          { 
            id: 4, 
            title: 'Designer Handbag', 
            description: 'Authentic designer handbag, barely used, comes with certificate.',
            currentBid: 550, 
            image: 'https://picsum.photos/id/21/300/200', 
            endsAt: new Date(Date.now() + 129600000).toISOString(),
            bidCount: 12,
            seller: 'FashionFinder',
            categoryId: 3
          },
          { 
            id: 5, 
            title: 'Classic Car Model Collection', 
            description: 'Set of 10 detailed classic car models from the 60s and 70s.',
            currentBid: 320, 
            image: 'https://picsum.photos/id/111/300/200', 
            endsAt: new Date(Date.now() + 345600000).toISOString(),
            bidCount: 5,
            seller: 'CarEnthusiast',
            categoryId: 2
          },
          { 
            id: 6, 
            title: 'High-End Laptop', 
            description: 'Powerful laptop with the latest specs, perfect for gaming and design work.',
            currentBid: 1100, 
            image: 'https://picsum.photos/id/119/300/200', 
            endsAt: new Date(Date.now() + 432000000).toISOString(),
            bidCount: 20,
            seller: 'TechDeals',
            categoryId: 1
          },
        ];
        
        const mockCategories = [
          { id: 1, name: 'Electronics', icon: '💻' },
          { id: 2, name: 'Collectibles', icon: '🏆' },
          { id: 3, name: 'Fashion', icon: '👕' },
          { id: 4, name: 'Home & Garden', icon: '🏡' },
          { id: 5, name: 'Vehicles', icon: '🚗' },
        ];
        
        setCategories(mockCategories);
        
        let filtered = mockAuctions;
        if (selectedCategory) {
          filtered = mockAuctions.filter(auction => auction.categoryId === parseInt(selectedCategory));
        }
        
        if (searchTerm) {
          filtered = filtered.filter(auction => 
            auction.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
            auction.description.toLowerCase().includes(searchTerm.toLowerCase())
          );
        }
        
        if (sort === 'endingSoon') {
          filtered.sort((a, b) => new Date(a.endsAt) - new Date(b.endsAt));
        } else if (sort === 'priceLowHigh') {
          filtered.sort((a, b) => a.currentBid - b.currentBid);
        } else if (sort === 'priceHighLow') {
          filtered.sort((a, b) => b.currentBid - a.currentBid);
        } else if (sort === 'mostBids') {
          filtered.sort((a, b) => b.bidCount - a.bidCount);
        }
        
        setAuctions(filtered);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching auctions:', error);
        setLoading(false);
      }
    };
    
    fetchData();
  }, [filter, sort, searchTerm, selectedCategory]);

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
    <div className="auctions-page">
      <div className="container">
        <h1>
          {selectedCategory 
            ? `${categories.find(c => c.id === parseInt(selectedCategory))?.name || ''} Auctions` 
            : 'Browse Auctions'
          }
        </h1>
        
        <div className="search-filter-container">
          <div className="search-bar">
            <input
              type="text"
              placeholder="Search for auctions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div className="filters">
            <div className="filter-group">
              <label>Category:</label>
              <select 
                value={selectedCategory} 
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <option value="">All Categories</option>
                {categories.map(category => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="filter-group">
              <label>Sort By:</label>
              <select 
                value={sort} 
                onChange={(e) => setSort(e.target.value)}
              >
                <option value="endingSoon">Ending Soon</option>
                <option value="priceLowHigh">Price: Low to High</option>
                <option value="priceHighLow">Price: High to Low</option>
                <option value="mostBids">Most Bids</option>
              </select>
            </div>
          </div>
        </div>
        
        {loading ? (
          <div className="loading">Loading auctions...</div>
        ) : auctions.length === 0 ? (
          <div className="no-results">
            <p>No auctions found matching your criteria.</p>
            <button 
              className="btn btn-secondary"
              onClick={() => {
                setSearchTerm('');
                setSelectedCategory('');
                setSort('endingSoon');
              }}
            >
              Clear Filters
            </button>
          </div>
        ) : (
          <div className="auctions-grid">
            {auctions.map(auction => (
              <div key={auction.id} className="auction-card">
                <div className="auction-image">
                  <img src={auction.image} alt={auction.title} />
                </div>
                <div className="auction-details">
                  <h3>{auction.title}</h3>
                  <p className="auction-description">{auction.description}</p>
                  <div className="auction-meta">
                    <div className="bid-info">
                      <p className="current-bid">Current Bid: ${auction.currentBid}</p>
                      <p className="bid-count">{auction.bidCount} bids</p>
                    </div>
                    <p className="time-remaining">{formatTimeRemaining(auction.endsAt)}</p>
                  </div>
                  <div className="auction-footer">
                    <p className="seller">Seller: {auction.seller}</p>
                    <Link to={`/auction/${auction.id}`} className="btn btn-outline">View Details</Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AuctionsPage;