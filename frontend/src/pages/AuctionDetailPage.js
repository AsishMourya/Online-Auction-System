import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import '../styles/AuctionDetailPage.css';
import AutoBidding from '../components/AutoBidding';
import api from '../services/api';
import { useWallet } from '../contexts/WalletContext';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Helper function for currency formatting
const formatCurrency = (value) => {
  const numValue = parseFloat(value);
  return isNaN(numValue) ? '0.00' : numValue.toFixed(2);
};

const AuctionDetailPage = () => {
  const { id } = useParams();
  const [auction, setAuction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bidAmount, setBidAmount] = useState('');
  const [error, setError] = useState('');
  const [bidSuccess, setBidSuccess] = useState(false);
  const [bids, setBids] = useState([]);
  const [timeLeft, setTimeLeft] = useState('');
  const [activeTab, setActiveTab] = useState('Description');
  const [similarAuctions, setSimilarAuctions] = useState([]);
  const { walletBalance } = useWallet();
  const isLoggedIn = localStorage.getItem('token') !== null;

  // Move the API connectivity test inside the component
  useEffect(() => {
    console.log('Current API_URL:', API_URL);
    // Make a test request to check connectivity
    axios.get(`${API_URL}/api/v1/auctions/auctions/`)
      .then(response => {
        console.log('API connectivity test successful', 
          Array.isArray(response.data) ? `Found ${response.data.length} auctions` :
          response.data?.data ? `Found data with ${response.data.data.length} items` :
          'Received response but format is unexpected'
        );
      })
      .catch(error => {
        console.error('API connectivity test failed', error.message);
      });
  }, []);

  const fetchBids = async (auctionId) => {
    try {
      const token = localStorage.getItem('token');
      const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
      
      console.log(`Fetching bids for auction ID: ${auctionId}`);
      
      // Try multiple potential bid endpoints with and without auth
      const endpoints = [
        `/api/v1/auctions/auctions/${auctionId}/bids/`,
        `/api/v1/auctions/bids/?auction_id=${auctionId}`,
        `/api/v1/auctions/${auctionId}/bids/`,
        `/api/v1/auctions/public/auctions/${auctionId}/bids/`
      ];
      
      let bidsData = [];
      let succeeded = false;
      
      for (const endpoint of endpoints) {
        try {
          // Try with auth
          if (token) {
            console.log(`Trying bids endpoint with auth: ${API_URL}${endpoint}`);
            const authResponse = await axios.get(`${API_URL}${endpoint}`, { headers: authHeaders });
            
            if (authResponse.data) {
              console.log('Bids data found with auth at endpoint:', endpoint, authResponse.data);
              
              if (Array.isArray(authResponse.data)) {
                bidsData = authResponse.data;
              } else if (Array.isArray(authResponse.data.data)) {
                bidsData = authResponse.data.data;
              } else if (authResponse.data.bids && Array.isArray(authResponse.data.bids)) {
                bidsData = authResponse.data.bids;
              }
              
              if (bidsData.length > 0) {
                succeeded = true;
                break;
              }
            }
          }
          
          // Try without auth
          console.log(`Trying bids endpoint without auth: ${API_URL}${endpoint}`);
          const publicResponse = await axios.get(`${API_URL}${endpoint}`);
          
          if (publicResponse.data) {
            console.log('Bids data found without auth at endpoint:', endpoint, publicResponse.data);
            
            if (Array.isArray(publicResponse.data)) {
              bidsData = publicResponse.data;
            } else if (Array.isArray(publicResponse.data.data)) {
              bidsData = publicResponse.data.data;
            } else if (publicResponse.data.bids && Array.isArray(publicResponse.data.bids)) {
              bidsData = publicResponse.data.bids;
            }
            
            if (bidsData.length > 0) {
              succeeded = true;
              break;
            }
          }
        } catch (err) {
          console.warn(`Bids endpoint ${endpoint} failed:`, err.message);
        }
      }
      
      if (!succeeded) {
        console.warn('Could not fetch bids from any endpoint. Using empty array.');
      }
      
      // Format bids data for display
      const formattedBids = bidsData.map(bid => ({
        id: bid.id,
        bidder: bid.bidder?.username || bid.bidder_name || 'Anonymous',
        bidder_id: bid.bidder?.id || bid.bidder_id,
        amount: bid.amount || 0,
        time: bid.created_at || bid.timestamp || bid.time || new Date().toISOString()
      }));
      
      // Sort bids by amount in descending order
      formattedBids.sort((a, b) => parseFloat(b.amount) - parseFloat(a.amount));
      
      console.log('Formatted bids:', formattedBids);
      setBids(formattedBids);
    } catch (error) {
      console.error('Error fetching bids:', error);
      setBids([]);
    }
  };

  const fetchSimilarAuctions = async (categoryId) => {
    try {
      if (!categoryId) {
        console.warn('No category ID provided for similar auctions');
        setSimilarAuctions([]);
        return;
      }
      
      console.log(`Fetching similar auctions for category ID: ${categoryId}`);
      
      const token = localStorage.getItem('token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      
      // Try multiple potential endpoints for similar auctions
      const endpoints = [
        `/api/v1/auctions/auctions/?category_id=${categoryId}`,
        `/api/v1/auctions/auctions/?category=${categoryId}`,
        `/api/v1/auctions/categories/${categoryId}/auctions/`
      ];
      
      let auctionsData = [];
      let succeeded = false;
      
      for (const endpoint of endpoints) {
        try {
          console.log(`Trying similar auctions endpoint: ${API_URL}${endpoint}`);
          const response = await axios.get(`${API_URL}${endpoint}`, { headers });
          
          if (response.data) {
            console.log('Similar auctions data found at endpoint:', endpoint, response.data);
            
            // Extract auctions data, handling different response formats
            if (Array.isArray(response.data)) {
              auctionsData = response.data;
            } else if (Array.isArray(response.data.data)) {
              auctionsData = response.data.data;
            } else if (response.data.auctions && Array.isArray(response.data.auctions)) {
              auctionsData = response.data.auctions;
            }
            
            // If we got auctions data, break the loop
            if (auctionsData.length > 0) {
              succeeded = true;
              break;
            }
          }
        } catch (err) {
          console.warn(`Similar auctions endpoint ${endpoint} failed:`, err.message);
        }
      }
      
      if (!succeeded) {
        console.warn('Could not fetch similar auctions from any endpoint. Using empty array.');
        setSimilarAuctions([]);
        return;
      }
      
      // Filter out the current auction and limit to 4 similar auctions
      auctionsData = auctionsData
        .filter(a => a.id.toString() !== id.toString())
        .slice(0, 4);
      
      // Format similar auctions data for display
      const formattedAuctions = auctionsData.map(auction => {
        // Process images similar to main auction
        let images = [];
        if (auction.images && Array.isArray(auction.images)) {
          images = auction.images;
        } else if (auction.item?.image_urls && Array.isArray(auction.item.image_urls)) {
          images = auction.item.image_urls;
        } else if (auction.image_url) {
          images = [auction.image_url];
        } else {
          images = ['https://via.placeholder.com/400x300?text=No+Image'];
        }
        
        return {
          id: auction.id,
          title: auction.title || 'Untitled Auction',
          description: auction.description || 'No description available',
          currentBid: auction.current_price || auction.starting_price || 0,
          images: images,
          endsAt: auction.end_time || auction.end_date
        };
      });
      
      console.log('Formatted similar auctions:', formattedAuctions);
      setSimilarAuctions(formattedAuctions);
    } catch (error) {
      console.error('Error fetching similar auctions:', error);
      setSimilarAuctions([]);
    }
  };

  // Update the fetchAuctionDetails function to handle auth better:
  const fetchAuctionDetails = async () => {
    try {
      setLoading(true);
      setError(''); 
      
      console.log('Attempting to fetch auction with ID:', id);
      
      // Make sure we get the most up-to-date token
      const token = localStorage.getItem('token');
      
      // Try both authenticated and unauthenticated requests
      const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
      const auctionId = id.toString();
      
      // Try authenticated request first
      try {
        console.log(`Making authenticated request to: ${API_URL}/api/v1/auctions/auctions/${auctionId}/`);
        const response = await axios.get(`${API_URL}/api/v1/auctions/auctions/${auctionId}/`, {
          headers: authHeaders 
        });
        
        if (response.data) {
          console.log('Auction data found with auth!', response.data);
          const auctionData = response.data.data || response.data;
          processAuctionData(auctionData);
          return;
        }
      } catch (authError) {
        console.error('Authenticated API call failed:', authError.message);
        
        // If it's specifically a 401, try without auth
        if (authError.response?.status === 401) {
          try {
            console.log(`Making public request to: ${API_URL}/api/v1/auctions/auctions/${auctionId}/`);
            const publicResponse = await axios.get(`${API_URL}/api/v1/auctions/auctions/${auctionId}/`);
            
            if (publicResponse.data) {
              console.log('Auction data found without auth!', publicResponse.data);
              const auctionData = publicResponse.data.data || publicResponse.data;
              processAuctionData(auctionData);
              return;
            }
          } catch (publicError) {
            console.error('Public API call failed:', publicError.message);
          }
        }
      }
      
      // If direct requests fail, try other endpoints with both auth and non-auth
      const endpoints = [
        `/api/v1/auctions/auctions/${auctionId}/`,
        `/api/v1/auctions/auctions/${auctionId}`,
        `/api/v1/auctions/${auctionId}/`,
        `/api/v1/auctions/${auctionId}`,
        `/api/v1/auctions/detail/${auctionId}/`,
        `/api/v1/auctions/public/auctions/${auctionId}/`
      ];
      
      // Try each endpoint with and without auth
      for (const endpoint of endpoints) {
        try {
          // Try with auth first if token exists
          if (token) {
            console.log(`Trying endpoint with auth: ${API_URL}${endpoint}`);
            const authResponse = await axios.get(`${API_URL}${endpoint}`, { 
              headers: authHeaders 
            });
            
            if (authResponse.data) {
              console.log('Data found at endpoint with auth:', endpoint, authResponse.data);
              const auctionData = authResponse.data.data || authResponse.data;
              processAuctionData(auctionData);
              return;
            }
          }
          
          // Try without auth 
          console.log(`Trying endpoint without auth: ${API_URL}${endpoint}`);
          const publicResponse = await axios.get(`${API_URL}${endpoint}`);
          
          if (publicResponse.data) {
            console.log('Data found at endpoint without auth:', endpoint, publicResponse.data);
            const auctionData = publicResponse.data.data || publicResponse.data;
            processAuctionData(auctionData);
            return;
          }
        } catch (err) {
          console.warn(`Endpoint ${endpoint} failed:`, err.message);
        }
      }
      
      console.error('All API endpoints failed for auction ID:', auctionId);
      setError('Could not find the auction. Please check the ID or try again later.');
      setLoading(false);
    } catch (outerError) {
      console.error('Unhandled error in fetchAuctionDetails:', outerError);
      setError('An unexpected error occurred. Please try again later.');
      setLoading(false);
    }
  };

  const processAuctionData = (auctionData) => {
    if (!auctionData) {
      console.error('No auction data to process');
      setError('Invalid auction data received from server');
      setLoading(false);
      return;
    }
    
    console.log('Processing auction data:', auctionData);
    
    // Extract strictly what's available in the API response
    // No hardcoded fallbacks - only use the data provided by the API
    const normalizedAuction = {
      id: auctionData.id,
      title: auctionData.title || '',
      description: auctionData.description || '',
      currentBid: auctionData.current_price || auctionData.starting_price || 0,
      minBidIncrement: auctionData.min_bid_increment || 0,
      startingBid: auctionData.starting_price || 0,
      images: [],
      endsAt: auctionData.end_time || auctionData.end_date || null,
      status: auctionData.status || '',
      seller: {
        id: auctionData.seller?.id || auctionData.seller_id || '',
        name: auctionData.seller?.username || auctionData.seller?.name || auctionData.seller_name || '',
        rating: auctionData.seller?.rating || null,
        since: auctionData.seller?.date_joined || auctionData.seller_since || null
      },
      category: {
        id: auctionData.category?.id || auctionData.category_id || null,
        name: auctionData.category?.name || auctionData.category_name || ''
      },
      condition: auctionData.condition || auctionData.item?.condition || '',
      location: auctionData.location || auctionData.item?.location || '',
      shippingOptions: [],
      paymentMethods: [],
      returnPolicy: auctionData.return_policy || auctionData.item?.return_policy || ''
    };
    
    // Extract images - only if they exist in the API response
    if (auctionData.images && Array.isArray(auctionData.images) && auctionData.images.length > 0) {
      normalizedAuction.images = auctionData.images;
    } else if (auctionData.item?.image_urls && Array.isArray(auctionData.item.image_urls) && auctionData.item.image_urls.length > 0) {
      normalizedAuction.images = auctionData.item.image_urls;
    } else if (auctionData.image_url) {
      normalizedAuction.images = [auctionData.image_url];
    } else if (auctionData.image) {
      normalizedAuction.images = [auctionData.image];
    }
    
    // Extract shipping options - only if they exist in the API response
    if (auctionData.shipping_options && Array.isArray(auctionData.shipping_options)) {
      normalizedAuction.shippingOptions = auctionData.shipping_options;
    } else if (auctionData.item?.shipping_options && Array.isArray(auctionData.item.shipping_options)) {
      normalizedAuction.shippingOptions = auctionData.item.shipping_options;
    }
    
    // Extract payment methods - only if they exist in the API response
    if (auctionData.payment_methods && Array.isArray(auctionData.payment_methods)) {
      normalizedAuction.paymentMethods = auctionData.payment_methods;
    } else if (auctionData.item?.payment_methods && Array.isArray(auctionData.item.payment_methods)) {
      normalizedAuction.paymentMethods = auctionData.item.payment_methods;
    }
    
    console.log('Normalized auction object with NO hardcoded data:', normalizedAuction);
    setAuction(normalizedAuction);
    
    // Fetch bids only if we have a valid auction ID
    if (auctionData.id) {
      fetchBids(auctionData.id);
    } else {
      setBids([]);
    }
    
    // Set minimum bid amount if we have valid current bid and increment values
    if (normalizedAuction.currentBid !== null && normalizedAuction.minBidIncrement !== null) {
      const minBidAmount = (parseFloat(normalizedAuction.currentBid) + 
                         parseFloat(normalizedAuction.minBidIncrement)).toFixed(2);
      setBidAmount(minBidAmount);
    }
    
    // Fetch similar auctions only if we have a valid category ID
    if (normalizedAuction.category.id) {
      fetchSimilarAuctions(normalizedAuction.category.id);
    } else {
      setSimilarAuctions([]);
    }
    
    setLoading(false);
  };

  useEffect(() => {
    fetchAuctionDetails();
  }, [id]);

  useEffect(() => {
    if (!auction) return;

    const updateTimeLeft = () => {
      const endDate = new Date(auction.endsAt);
      const now = new Date();
      const timeRemaining = endDate - now;

      if (timeRemaining <= 0) {
        setTimeLeft('Auction ended');

        if (auction.status !== 'ended' && auction.status !== 'sold') {
          checkAuctionStatus();
        }
        return;
      }

      const days = Math.floor(timeRemaining / (1000 * 60 * 60 * 24));
      const hours = Math.floor((timeRemaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((timeRemaining % (1000 * 60)) / 1000);

      setTimeLeft(`${days}d ${hours}h ${minutes}m ${seconds}s`);
    };

    const checkAuctionStatus = async () => {
      try {
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const response = await axios.get(`${API_URL}/api/v1/auctions/auctions/${id}/`, {
          headers
        });

        const auctionData = response.data.data || response.data;

        if (auctionData) {
          setAuction(prevAuction => ({
            ...prevAuction,
            status: auctionData.status,
            currentBid: auctionData.current_price || auctionData.starting_price
          }));

          fetchBids(id);
        }
      } catch (error) {
        console.error('Error checking auction status:', error);
      }
    };

    updateTimeLeft();
    const interval = setInterval(updateTimeLeft, 1000);

    return () => clearInterval(interval);
  }, [auction, id]);

  const handlePlaceBid = async (e) => {
    e.preventDefault();

    try {
      const token = localStorage.getItem('token');

      if (!token) {
        setError('You must be logged in to place a bid');
        return;
      }

      const bidValue = parseFloat(bidAmount);
      const currentBid = parseFloat(auction.currentBid);
      const minIncrement = parseFloat(auction.minBidIncrement);
      const minimumBid = currentBid + minIncrement;

      console.log('Current bid:', currentBid);
      console.log('Min increment:', minIncrement);
      console.log('Calculated minimum bid:', minimumBid);
      console.log('User bid:', bidValue);
      console.log('Wallet balance:', walletBalance);

      // Validation checks
      if (isNaN(bidValue)) {
        setError('Please enter a valid amount');
        return;
      }

      const EPSILON = 0.001;

      if (bidValue <= currentBid) {
        setError(`Your bid must be higher than the current bid ($${formatCurrency(currentBid)})`);
        return;
      }

      if (bidValue < minimumBid - EPSILON) {
        setError(`Minimum bid increment is $${formatCurrency(minIncrement)}. Please bid at least $${formatCurrency(minimumBid)}`);
        return;
      }

      // Check if user has enough balance in wallet
      if (bidValue > parseFloat(walletBalance)) {
        setError(`Insufficient funds in your wallet. Your balance: $${formatCurrency(walletBalance)}`);
        return;
      }

      setError('');

      // Use the API service instead of direct axios calls
      try {
        const response = await api.placeBid(id, {
          amount: bidValue,
          auction_id: id
        });
        
        console.log('Bid response:', response);

        if (response.data && (response.data.success || response.status === 201 || response.status === 200)) {
          setAuction({
            ...auction,
            currentBid: bidValue
          });

          const newBid = {
            id: Date.now(),
            bidder: 'You',
            bidder_id: localStorage.getItem('user_id'),
            amount: bidValue,
            time: new Date().toISOString()
          };

          setBids([newBid, ...bids]);
          setBidSuccess(true);
          setBidAmount((bidValue + auction.minBidIncrement).toFixed(2));

          setTimeout(() => {
            setBidSuccess(false);
          }, 3000);
        } else {
          setError(response.data?.message || 'Failed to place bid');
        }
      } catch (apiError) {
        console.error('API service error during bid:', apiError);
        
        // Try direct axios calls as fallback
        try {
          const auctionBidEndpoint = `/api/v1/auctions/auctions/${id}/bid/`;
          console.log(`Sending bid to: ${API_URL}${auctionBidEndpoint}`);

          const response = await axios.post(`${API_URL}${auctionBidEndpoint}`, {
            amount: bidValue
          }, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
          
          console.log('Direct bid response:', response.data);
          
          if (response.data && (response.data.success || response.status === 201)) {
            setAuction({
              ...auction,
              currentBid: bidValue
            });

            const newBid = {
              id: Date.now(),
              bidder: 'You',
              bidder_id: localStorage.getItem('user_id'),
              amount: bidValue,
              time: new Date().toISOString()
            };

            setBids([newBid, ...bids]);
            setBidSuccess(true);
            setBidAmount((bidValue + auction.minBidIncrement).toFixed(2));

            setTimeout(() => {
              setBidSuccess(false);
            }, 3000);
          } else {
            setError(response.data?.message || 'Failed to place bid with specific endpoint');
          }
        } catch (error) {
          console.error('Error placing bid through direct endpoint:', error);
          handleBidError(error);
        }
      }
    } catch (error) {
      console.error('Error in bid function:', error);
      handleBidError(error);
    }
  };

  // Add this helper function for better error handling
  const handleBidError = (error) => {
    console.error('Detailed bid error:', error);
    
    if (error.response) {
      console.error('Error response status:', error.response.status);
      console.error('Error response data:', error.response.data);
      
      // Handle specific error cases
      if (error.response.status === 400) {
        if (error.response.data?.message) {
          setError(error.response.data.message);
        } else if (error.response.data?.detail) {
          setError(error.response.data.detail);
        } else if (error.response.data?.errors?.amount) {
          setError(error.response.data.errors.amount);
        } else {
          setError('Invalid bid. Please check your bid amount and try again.');
        }
      } else if (error.response.status === 401) {
        setError('Your session has expired. Please log in again.');
      } else if (error.response.status === 403) {
        setError('You are not authorized to bid on this auction.');
      } else if (error.response.status === 404) {
        setError('Auction not found or bidding endpoint not available.');
      } else {
        setError(`Error ${error.response.status}: ${error.response.data?.message || 'Failed to place bid'}`);
      }
    } else if (error.request) {
      setError('Network error. Please check your connection and try again.');
    } else {
      setError('Error: ' + error.message);
    }
  };

  const formatDate = (dateString) => {
    const options = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading auction details...</p>
        <p className="loading-detail">Auction ID: {id}</p>
      </div>
    );
  }

  if (!auction && !loading) {
    return (
      <div className="error-container">
        <h2>Auction Not Found</h2>
        <p>We couldn't find the auction you're looking for. It may have been removed or the ID is incorrect.</p>
        <div className="error-actions">
          <Link to="/auctions" className="btn btn-primary">Browse Auctions</Link>
          <Link to="/" className="btn btn-secondary">Return Home</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auction-detail-page">
      <div className="container">
        <div className="breadcrumb">
          <Link to="/">Home</Link> / <Link to="/auctions">Auctions</Link> / {auction.title}
        </div>

        <div className="auction-detail-container">
          <div className="auction-images">
            {auction.images && auction.images.length > 0 ? (
              <>
                <div className="main-image">
                  <img src={auction.images[0]} alt={auction.title} />
                </div>
                {auction.images.length > 1 && (
                  <div className="thumbnail-images">
                    {auction.images.map((image, index) => (
                      <div key={index} className="thumbnail">
                        <img src={image} alt={`${auction.title} - view ${index + 1}`} />
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="no-images">
                <p>No images available for this auction</p>
              </div>
            )}
          </div>

          <div className="auction-info">
            <h1>{auction.title}</h1>

            <div className="auction-meta">
              {auction.category.name && <p>Category: <span>{auction.category.name}</span></p>}
              {auction.condition && <p>Condition: <span>{auction.condition}</span></p>}
              {auction.location && <p>Location: <span>{auction.location}</span></p>}
            </div>

            <div className="bid-section">
              <div className="current-bid-info">
                <h3>Current Bid</h3>
                <p className="current-bid-amount">${formatCurrency(auction.currentBid)}</p>
                <p className="bid-count">{bids.length} bids</p>
                <p className="time-remaining">{timeLeft}</p>
                {new Date(auction.endsAt) <= new Date() && (
                  <button
                    onClick={async () => {
                      try {
                        setLoading(true);
                        await fetchAuctionDetails();
                        setLoading(false);
                      } catch (error) {
                        console.error('Error refreshing auction details:', error);
                        setLoading(false);
                      }
                    }}
                    className="btn btn-outline-small refresh-btn"
                  >
                    <span>↻</span> Refresh Status
                  </button>
                )}
              </div>

              {new Date(auction.endsAt) > new Date() ? (
                <div className="place-bid">
                  {error && <div className="error-message">{error}</div>}
                  {bidSuccess && <div className="success-message">Your bid was placed successfully!</div>}

                  <form onSubmit={handlePlaceBid}>
                    <div className="bid-input-group">
                      <label htmlFor="bidAmount">Your Bid ($)</label>
                      <input
                        type="text"
                        id="bidAmount"
                        pattern="\d+(\.\d{1,2})?"
                        value={bidAmount}
                        onChange={(e) => {
                          const value = e.target.value;
                          if (/^\d*\.?\d{0,2}$/.test(value) || value === '') {
                            setBidAmount(value);
                          }
                        }}
                        required
                      />
                    </div>

                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={!isLoggedIn}
                    >
                      {isLoggedIn ? 'Place Bid' : 'Login to Bid'}
                    </button>

                    {!isLoggedIn && (
                      <p className="login-notice">
                        <Link to="/login">Login</Link> or <Link to="/register">Register</Link> to place a bid
                      </p>
                    )}
                  </form>

                  <div className="bid-notes">
                    <p>Minimum bid: ${formatCurrency(parseFloat(auction.currentBid) + parseFloat(auction.minBidIncrement))}</p>
                    <p>Bid increment: ${formatCurrency(auction.minBidIncrement)}</p>
                  </div>

                  <div className="bid-preview">
                    <h4>Bid Summary</h4>
                    <div className="bid-summary">
                      <div className="summary-row">
                        <span>Your bid amount:</span>
                        <span>${bidAmount ? formatCurrency(parseFloat(bidAmount)) : '0.00'}</span>
                      </div>
                      <div className="summary-row">
                        <span>Your wallet balance:</span>
                        <span>${formatCurrency(parseFloat(walletBalance))}</span>
                      </div>
                      <div className="summary-row balance-after">
                        <span>Balance after bid:</span>
                        <span>${formatCurrency(Math.max(0, parseFloat(walletBalance) - (parseFloat(bidAmount) || 0)))}</span>
                      </div>
                    </div>
                    
                    {parseFloat(bidAmount) > parseFloat(walletBalance) && (
                      <div className="insufficient-funds-warning">
                        ⚠️ Warning: Your bid amount exceeds your wallet balance. 
                        <Link to="/wallet" className="add-funds-link">Add Funds</Link>
                      </div>
                    )}
                  </div>

                  {isLoggedIn && auction.seller.id !== localStorage.getItem('user_id') && (
                    <AutoBidding 
                      auctionId={auction.id} 
                      currentPrice={auction.currentBid} 
                      minBidIncrement={auction.minBidIncrement}
                    />
                  )}
                </div>
              ) : (
                <div className="auction-ended">
                  <p>This auction has ended</p>
                  {bids.length > 0 ? (
                    <>
                      <p className="winning-bid">
                        Winning bid: ${formatCurrency(bids[0].amount)} by {bids[0].bidder}
                      </p>

                      {isLoggedIn && bids[0].bidder_id === localStorage.getItem('user_id') && (
                        <div className="winner-info">
                          <p className="winner-badge">🏆 Congratulations! You won this auction!</p>
                          <p>The seller will contact you with shipping details.</p>
                          <Link to="/profile" className="btn btn-primary btn-sm">
                            View My Purchases
                          </Link>
                        </div>
                      )}

                      {isLoggedIn && auction.seller.id === localStorage.getItem('user_id') && (
                        <div className="seller-info-panel">
                          <p className="seller-notice">Your item has been sold!</p>
                          <p>Please arrange shipping details with the winner.</p>
                          <Link to="/profile" className="btn btn-primary btn-sm">
                            View My Sales
                          </Link>
                        </div>
                      )}
                    </>
                  ) : (
                    <p>No bids were placed on this auction</p>
                  )}
                </div>
              )}
            </div>

            <div className="seller-info">
              <h3>Seller Information</h3>
              {auction.seller.name ? (
                <p>Seller: {auction.seller.name}</p>
              ) : (
                <p>Seller information not available</p>
              )}
              {auction.seller.rating !== null && (
                <p>Rating: {auction.seller.rating > 0 ? `${auction.seller.rating}/5` : 'No ratings yet'}</p>
              )}
              {auction.seller.since && (
                <p>Member since: {new Date(auction.seller.since).getFullYear()}</p>
              )}
              {auction.seller.id && (
                <Link to={`/seller/${auction.seller.id}`} className="btn btn-outline-small">View Seller Profile</Link>
              )}
            </div>
          </div>
        </div>

        <div className="auction-tabs">
          <div className="tabs-header">
            <button onClick={() => { setActiveTab("Description") }} className={`tab-btn ${activeTab === "Description" ? "active" : ""}`}>Description</button>
            <button onClick={() => { setActiveTab("Shipping & Payment") }} className={`tab-btn ${activeTab === "Shipping & Payment" ? "active" : ""}`}>Shipping & Payment</button>
            <button onClick={() => { setActiveTab("Bid History") }} className={`tab-btn ${activeTab === "Bid History" ? "active" : ""}`}>Bid History</button>
          </div>

          {activeTab === "Description" && <div className="tab-content">
            <div className="tab-pane active">
              <p>{auction.description}</p>
            </div>
          </div>}

          {activeTab === "Shipping & Payment" && (
            <div className="shipping-payment">
              {auction.shippingOptions && auction.shippingOptions.length > 0 ? (
                <>
                  <h3>Shipping Options</h3>
                  <ul className="shipping-list">
                    {auction.shippingOptions.map((option, index) => (
                      <li key={index}>
                        {option.method}: ${formatCurrency(option.cost)}
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p>No shipping information provided by seller</p>
              )}

              {auction.paymentMethods && auction.paymentMethods.length > 0 ? (
                <>
                  <h3>Payment Methods</h3>
                  <ul className="payment-list">
                    {auction.paymentMethods.map((method, index) => (
                      <li key={index}>{method}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p>No payment method information provided by seller</p>
              )}

              {auction.returnPolicy ? (
                <>
                  <h3>Return Policy</h3>
                  <p>{auction.returnPolicy}</p>
                </>
              ) : (
                <p>No return policy information provided by seller</p>
              )}
            </div>
          )}

          {activeTab === "Bid History" && <div className="bid-history">
            {bids.length === 0 ? (
              <p>No bids have been placed yet.</p>
            ) : (
              <table className="bid-table">
                <thead>
                  <tr>
                    <th>Bidder</th>
                    <th>Amount</th>
                    <th>Date & Time</th>
                  </tr>
                </thead>
                <tbody>
                  {bids.map(bid => (
                    <tr key={bid.id}>
                      <td>{bid.bidder}</td>
                      <td>${formatCurrency(bid.amount)}</td>
                      <td>{formatDate(bid.time)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>}
        </div>

        {similarAuctions.length > 0 && (
          <div className="similar-auctions">
            <h2>Similar {auction.category.name || ''} Auctions</h2>
            <div className="similar-grid">
              {similarAuctions.map(similarAuction => (
                <div key={similarAuction.id} className="auction-card-small">
                  <img
                    src={similarAuction.images[0]}
                    alt={similarAuction.title}
                  />
                  <div className="auction-card-info">
                    <h3>{similarAuction.title}</h3>
                    <p>${formatCurrency(similarAuction.currentBid)}</p>
                    <Link
                      to={`/auction/${similarAuction.id}`}
                      className="btn btn-small"
                    >
                      View
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuctionDetailPage;