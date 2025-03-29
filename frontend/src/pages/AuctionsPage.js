import React, { useState, useEffect } from 'react';
import { Link, useParams, useLocation } from 'react-router-dom';
import axios from 'axios';
import '../styles/AuctionsPage.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
  const [error, setError] = useState('');
  const [debugInfo, setDebugInfo] = useState(null);
  const [backendStatus, setBackendStatus] = useState('unknown');

  useEffect(() => {
    if (categoryId) {
      setSelectedCategory(categoryId);
    }
  }, [categoryId, location.pathname]);

  // First check if backend is running
  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        // Just try to connect to the server root
        await axios.get(`${API_URL}`);
        setBackendStatus('online');
        console.log('Backend is online');
      } catch (error) {
        if (error.response) {
          // Even if we get an error response, the server is at least running
          setBackendStatus('online');
          console.log('Backend is online (received error response)');
        } else {
          setBackendStatus('offline');
          console.error('Backend appears to be offline:', error.message);
          setError(`Backend server appears to be offline: ${error.message}. Please make sure your Django server is running at ${API_URL}`);
        }
      }
    };
    
    checkBackendStatus();
  }, []);

  // Fetch categories from API
  useEffect(() => {
    if (backendStatus === 'offline') return;
    
    const fetchCategories = async () => {
      // Update your category endpoints:
      const categoryEndpoints = [
        `${API_URL}/api/v1/auctions/categories/all/`,
        `${API_URL}/api/v1/auctions/categories/`,
      ];
      
      let categoriesData = [];
      let success = false;
      
      for (const endpoint of categoryEndpoints) {
        try {
          console.log(`Trying to fetch categories from: ${endpoint}`);
          const response = await axios.get(endpoint);
          console.log(`Categories response from ${endpoint}:`, response.data);
          
          // Extract categories from response based on structure
          if (response.data?.categories && Array.isArray(response.data.categories)) {
            categoriesData = response.data.categories;
          } else if (response.data?.data && Array.isArray(response.data.data)) {
            categoriesData = response.data.data;
          } else if (Array.isArray(response.data)) {
            categoriesData = response.data;
          }
          
          if (categoriesData.length > 0) {
            success = true;
            break;
          }
        } catch (error) {
          console.warn(`Failed to fetch categories from ${endpoint}:`, error.message);
        }
      }
      
      if (!success || categoriesData.length === 0) {
        console.warn('Could not fetch categories from any endpoint, using fallbacks');
        // Use fallback categories for UI
        categoriesData = [
          { id: 1, name: 'Electronics' },
          { id: 2, name: 'Fashion' },
          { id: 3, name: 'Home & Garden' },
          { id: 4, name: 'Collectibles' },
          { id: 5, name: 'Art' }
        ];
      }
      
      // Map to consistent format
      const formattedCategories = categoriesData.map(cat => ({
        id: cat.id,
        name: cat.name,
        icon: cat.icon || getDefaultIconForCategory(cat.name)
      }));
      
      setCategories(formattedCategories);
    };
    
    fetchCategories();
  }, [backendStatus]);

  // Fetch auctions from multiple potential endpoints
  useEffect(() => {
    if (backendStatus === 'offline') return;
    
    const fetchAuctions = async () => {
      setLoading(true);
      setError('');
      setDebugInfo(null);
      
      try {
        // Prepare query parameters
        const params = {};
        
        if (selectedCategory) {
          params.category = selectedCategory;
        }
        
        if (searchTerm) {
          params.search = searchTerm;
        }
        
        // Replace the auctionEndpoints array with this:
        const auctionEndpoints = [
          // Add the test endpoint first
          `${API_URL}/api/v1/auctions/api/test/`,
          `${API_URL}/api/v1/auctions/test/`,
          // Then try your regular endpoints
          `${API_URL}/api/v1/auctions/featured/`,
          `${API_URL}/api/v1/auctions/auctions/`,
          `${API_URL}/api/v1/auctions/auctions/?featured=true`,
        ];
        
        let auctionsData = [];
        let successEndpoint = '';
        let responseData = null;
        
        for (const endpoint of auctionEndpoints) {
          try {
            console.log(`Trying to fetch auctions from: ${endpoint}`);
            const response = await axios.get(endpoint, { params });
            console.log(`Auctions response from ${endpoint}:`, response.data);
            responseData = response.data;
            
            // Log the structure of the response data
            console.log('Response data type:', typeof response.data);
            if (typeof response.data === 'object') {
              console.log('Top-level keys:', Object.keys(response.data));
              
              // Check common keys where auction data might be stored
              const possibleArrayKeys = ['auctions', 'data', 'results', 'items', 'objects'];
              for (const key of possibleArrayKeys) {
                if (response.data[key] && Array.isArray(response.data[key])) {
                  console.log(`Found array in response.data.${key} with ${response.data[key].length} items`);
                  if (response.data[key].length > 0) {
                    console.log(`First item structure:`, Object.keys(response.data[key][0]));
                  }
                }
              }
              
              // If the response is an array directly
              if (Array.isArray(response.data)) {
                console.log(`Response data is an array with ${response.data.length} items`);
                if (response.data.length > 0) {
                  console.log(`First item structure:`, Object.keys(response.data[0]));
                }
              }
            }
            
            // Extract auctions based on different possible response structures
            if (response.data?.success && response.data?.data && Array.isArray(response.data.data)) {
              // Handle the case where the data is directly in the "data" array
              auctionsData = response.data.data;
              console.log('Found auctions in response.data.data array');
            } else if (response.data?.success && response.data?.data?.auctions && Array.isArray(response.data.data.auctions)) {
              // Handle the case where data is in data.auctions
              auctionsData = response.data.data.auctions;
              console.log('Found auctions in response.data.data.auctions array');
            } else if (response.data?.auctions && Array.isArray(response.data.auctions)) {
              auctionsData = response.data.auctions;
              console.log('Found auctions in response.data.auctions array');
            } else if (Array.isArray(response.data)) {
              auctionsData = response.data;
              console.log('Response data is directly an array');
            } else if (response.data?.data && typeof response.data.data === 'object' && !Array.isArray(response.data.data)) {
              // Handle the case where data is an object with auction properties
              auctionsData = [response.data.data];
              console.log('Found a single auction object in response.data.data');
            }
            
            if (auctionsData.length > 0) {
              successEndpoint = endpoint;
              break;
            } else {
              console.log(`Endpoint ${endpoint} returned 0 auctions`);
            }
          } catch (error) {
            console.warn(`Failed to fetch auctions from ${endpoint}:`, error.message);
          }
        }
        
        // Save debug info with the endpoint that worked
        setDebugInfo({
          apiResponse: responseData,
          endpoint: successEndpoint,
          params: params
        });
        
        // If no auctions were found through any API endpoint, we won't use mocks - just show empty
        if (auctionsData.length === 0) {
          console.log('No auctions found from any API endpoint');
          setAuctions([]);
          setLoading(false);
          return;
        }
        
        // Transform the API data to our component's format
        const formattedAuctions = auctionsData.map(auction => ({
          id: auction.id,
          title: auction.title || 'Untitled Auction',
          description: auction.description || 'No description available',
          currentBid: auction.current_price || auction.starting_price || 0,
          image: getAuctionImage(auction),
          endsAt: auction.end_time || auction.end_date || new Date().toISOString(),
          bidCount: auction.bid_count || auction.bids?.length || 0,
          seller: auction.seller?.username || auction.seller?.name || auction.seller_name || 'Unknown',
          categoryId: auction.category?.id || auction.category_id || null,
          status: auction.status || 'active'
        }));
        
        console.log('Formatted auctions:', formattedAuctions);
        
        // Apply sorting
        let sortedAuctions = [...formattedAuctions];
        
        if (sort === 'endingSoon') {
          sortedAuctions.sort((a, b) => new Date(a.endsAt) - new Date(b.endsAt));
        } else if (sort === 'priceLowHigh') {
          sortedAuctions.sort((a, b) => a.currentBid - b.currentBid);
        } else if (sort === 'priceHighLow') {
          sortedAuctions.sort((a, b) => b.currentBid - a.currentBid);
        } else if (sort === 'mostBids') {
          sortedAuctions.sort((a, b) => b.bidCount - a.bidCount);
        }
        
        setAuctions(sortedAuctions);
      } catch (error) {
        console.error('Error in auction fetching process:', error);
        
        let errorMessage = 'Failed to load auctions';
        
        if (error.response) {
          errorMessage += `: ${error.response.status} - ${error.response.statusText}`;
          console.error('Error response data:', error.response.data);
        } else if (error.request) {
          errorMessage += ': No response from server. Is the backend running?';
        } else {
          errorMessage += `: ${error.message}`;
        }
        
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };
    
    fetchAuctions();
  }, [backendStatus, filter, sort, searchTerm, selectedCategory]);

  // Helper function to get the main image from an auction object
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
    return 'https://via.placeholder.com/300x200?text=No+Image';
  };

  // Helper function to generate default icons for categories
  const getDefaultIconForCategory = (categoryName) => {
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

  const formatTimeRemaining = (endDateString) => {
    const endDate = new Date(endDateString);
    const now = new Date();
    const timeRemaining = endDate - now;
    
    if (timeRemaining <= 0) return 'Ended';
    
    const days = Math.floor(timeRemaining / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeRemaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    
    return `${days}d ${hours}h remaining`;
  };
  
  // Helper function to format currency values
  const formatCurrency = (value) => {
    const numValue = parseFloat(value);
    return isNaN(numValue) ? '0.00' : numValue.toFixed(2);
  };

  return (
    <div className="auctions-page">
      <div className="container">
        <h1>
          {selectedCategory && categories.length > 0
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
                    {category.icon} {category.name}
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
        
        {backendStatus === 'offline' && (
          <div className="error-message">
            <h3>Backend Server Offline</h3>
            <p>The Django backend server appears to be offline or not responding.</p>
            <p>Please make sure your backend server is running at: {API_URL}</p>
            <button 
              className="btn btn-primary"
              onClick={() => window.location.reload()}
            >
              Retry Connection
            </button>
          </div>
        )}
        
        {backendStatus === 'online' && error && (
          <div className="error-message">
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
                    // Try a number of possible endpoints to find any that work
                    const potentialEndpoints = [
                      `${API_URL}/api/v1/`,
                      `${API_URL}/api/`,
                      `${API_URL}/api/v1/auctions/`,
                      `${API_URL}/api/auctions/`,
                      `${API_URL}/admin/`
                    ];
                    
                    let foundEndpoint = false;
                    
                    for (const endpoint of potentialEndpoints) {
                      try {
                        const response = await axios.get(endpoint);
                        console.log(`Found working endpoint at ${endpoint}:`, response.data);
                        alert(`Found working endpoint at ${endpoint} - check console for details`);
                        foundEndpoint = true;
                        break;
                      } catch (e) {
                        console.warn(`Endpoint ${endpoint} failed:`, e.message);
                      }
                    }
                    
                    if (!foundEndpoint) {
                      // If nothing works, try one more thing - basic admin page
                      try {
                        await axios.get(`${API_URL}/admin/login/`);
                        alert(`Django admin interface is available at ${API_URL}/admin/ but API endpoints are not working. Check your Django API configuration.`);
                      } catch (adminError) {
                        alert(`Could not find any working API endpoints or admin interface. Is your Django server configured correctly?`);
                      }
                    }
                  } catch (e) {
                    alert(`Debug process error: ${e.message}`);
                  }
                }}
              >
                Debug API
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
                      alert(`Found ${response.data.data.auction_count} auctions in database. Check console for details.`);
                    }
                  } catch (e) {
                    alert(`Could not check database content: ${e.message}`);
                  }
                }}
              >
                Check Database
              </button>
            </div>
            <div className="api-debug-info">
              <p>API URL: {API_URL}</p>
              <p>Backend Status: {backendStatus}</p>
              <p>If you're seeing this error, please check:</p>
              <ul>
                <li>Django server is running and accessible at {API_URL}</li>
                <li>API endpoints are correctly configured in Django urls.py</li>
                <li>Django REST Framework is properly set up</li>
                <li>CORS headers are configured to allow requests from your frontend</li>
                <li>Django views are handling requests correctly</li>
              </ul>
            </div>
          </div>
        )}
        
        {backendStatus === 'online' && loading && (
          <div className="loading">Loading auctions...</div>
        )}
        
        {backendStatus === 'online' && !loading && !error && auctions.length === 0 && (
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
        )}
        
        {backendStatus === 'online' && !loading && !error && auctions.length > 0 && (
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
                      <p className="current-bid">Current Bid: ${formatCurrency(auction.currentBid)}</p>
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
        
        {process.env.NODE_ENV === 'development' && debugInfo && (
          <div className="debug-section" style={{margin: '30px 0', padding: '15px', border: '1px dashed #ccc', borderRadius: '5px'}}>
            <h3>Debug Information</h3>
            <p><strong>API URL:</strong> {API_URL}</p>
            <p><strong>Backend Status:</strong> {backendStatus}</p>
            {debugInfo.endpoint && <p><strong>Endpoint Used:</strong> {debugInfo.endpoint}</p>}
            {debugInfo.params && <p><strong>Params:</strong> {JSON.stringify(debugInfo.params)}</p>}
            <div>
              <button 
                className="btn btn-small"
                onClick={() => console.log('Debug Info:', debugInfo)}
              >
                Log Full Debug Info to Console
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuctionsPage;