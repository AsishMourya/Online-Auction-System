import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import '../styles/AuctionDetailPage.css';
import AutoBidding from '../components/AutoBidding';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Add this helper function near the top, before the component
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
  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };
  const isLoggedIn = localStorage.getItem('token') !== null;

  const fetchBids = async (auctionId) => {
    try {
      const token = localStorage.getItem('token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      const response = await axios.get(`${API_URL}/api/v1/auctions/auctions/${auctionId}/bids/`, {
        headers
      });

      console.log('Bids API response:', response.data);

      if (response.data && (response.data.data || response.data)) {
        const bidsData = response.data.data?.bids || response.data.bids || response.data;

        if (Array.isArray(bidsData)) {
          const processedBids = bidsData.map(bid => ({
            id: bid.id,
            bidder: bid.bidder?.username || 'Anonymous',
            bidder_id: bid.bidder?.id || null,
            amount: bid.amount,
            time: bid.created_at || new Date().toISOString()
          }));

          setBids(processedBids);
        }
      }
    } catch (error) {
      console.error('Error fetching bids:', error);
    }
  };

  const fetchSimilarAuctions = async (categoryId) => {
    try {
      if (!categoryId) return;

      const response = await axios.get(`${API_URL}/api/v1/auctions/auctions/`, {
        params: {
          category: categoryId,
          exclude: id,
          limit: 3
        }
      });

      console.log('Similar auctions API response:', response.data);

      if (response.data && (response.data.data || response.data)) {
        const auctionsData = response.data.data?.auctions || response.data.auctions || response.data;

        if (Array.isArray(auctionsData)) {
          const processedAuctions = auctionsData.map(auction => ({
            id: auction.id,
            title: auction.title,
            currentBid: auction.current_price || auction.starting_price,
            images: auction.images || auction.item?.image_urls || ['https://picsum.photos/id/28/800/600']
          }));

          setSimilarAuctions(processedAuctions);
        }
      }
    } catch (error) {
      console.error('Error fetching similar auctions:', error);
    }
  };

  const fetchAuctionDetails = async () => {
    try {
      setLoading(true);
      setError(''); // Clear any previous errors

      console.log('Auction ID type:', typeof id);
      console.log('Auction ID value:', id);

      // If the ID might be a UUID that needs formatting
      const formattedId = id.includes('-') ? id : id;
      console.log('Using formatted ID:', formattedId);

      console.log('Fetching auction with ID:', id);

      const token = localStorage.getItem('token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      // Add this line - we were missing explicit loading = false at the end
      let setLoadingCalled = false;

      try {
        // First try with double auctions path
        const response = await axios.get(`${API_URL}/api/v1/auctions/auctions/${id}/`, {
          headers
        });
        console.log('Response from first endpoint attempt:', response);
        const auctionData = response.data.data || response.data;

        if (auctionData) {
          setAuction({
            id: auctionData.id,
            title: auctionData.title,
            description: auctionData.description,
            currentBid: auctionData.current_price || auctionData.starting_price,
            minBidIncrement: auctionData.min_bid_increment || 10,
            startingBid: auctionData.starting_price,
            images: auctionData.images || auctionData.item?.image_urls || ['https://picsum.photos/id/28/800/600'],
            endsAt: auctionData.end_time,
            status: auctionData.status || 'active', // Add the status
            seller: {
              id: auctionData.seller?.id || 101,
              name: auctionData.seller?.username || 'Unknown Seller',
              rating: auctionData.seller?.rating || 4.5,
              since: auctionData.seller?.date_joined || '2020-01-01'
            },
            category: {
              id: auctionData.category?.id || 1,
              name: auctionData.category?.name || 'Uncategorized'
            },
            condition: auctionData.item?.condition || 'Not specified',
            location: auctionData.item?.location || 'Not specified',
            shippingOptions: auctionData.item?.shipping_options || [
              { method: 'Standard Shipping', cost: 15 }
            ],
            paymentMethods: auctionData.item?.payment_methods || ['Credit Card', 'PayPal'],
            returnPolicy: auctionData.item?.return_policy || 'Contact seller'
          });

          fetchBids(auctionData.id);
          fetchSimilarAuctions(auctionData.category?.id);

          setBidAmount(
            (auctionData.current_price || auctionData.starting_price) +
            (auctionData.min_bid_increment || 10)
          );
        } else {
          console.warn('Unexpected API response format, falling back to mock data');
          fallbackToMockData();
        }

        setLoadingCalled = true;
        setLoading(false); // <-- ADD THIS LINE
      } catch (firstError) {
        console.log('First endpoint failed:', firstError.message);
        // Try alternative endpoint
        try {
          const alternativeResponse = await axios.get(`${API_URL}/api/v1/auctions/${id}/`, {
            headers
          });
          console.log('Response from alternative endpoint:', alternativeResponse);
          const auctionData = alternativeResponse.data.data || alternativeResponse.data;

          if (auctionData) {
            setAuction({
              id: auctionData.id,
              title: auctionData.title,
              description: auctionData.description,
              currentBid: auctionData.current_price || auctionData.starting_price,
              minBidIncrement: auctionData.min_bid_increment || 10,
              startingBid: auctionData.starting_price,
              images: auctionData.images || auctionData.item?.image_urls || ['https://picsum.photos/id/28/800/600'],
              endsAt: auctionData.end_time,
              status: auctionData.status || 'active', // Add the status
              seller: {
                id: auctionData.seller?.id || 101,
                name: auctionData.seller?.username || 'Unknown Seller',
                rating: auctionData.seller?.rating || 4.5,
                since: auctionData.seller?.date_joined || '2020-01-01'
              },
              category: {
                id: auctionData.category?.id || 1,
                name: auctionData.category?.name || 'Uncategorized'
              },
              condition: auctionData.item?.condition || 'Not specified',
              location: auctionData.item?.location || 'Not specified',
              shippingOptions: auctionData.item?.shipping_options || [
                { method: 'Standard Shipping', cost: 15 }
              ],
              paymentMethods: auctionData.item?.payment_methods || ['Credit Card', 'PayPal'],
              returnPolicy: auctionData.item?.return_policy || 'Contact seller'
            });

            fetchBids(auctionData.id);
            fetchSimilarAuctions(auctionData.category?.id);

            setBidAmount(
              (auctionData.current_price || auctionData.starting_price) +
              (auctionData.min_bid_increment || 10)
            );
          } else {
            console.warn('Unexpected API response format, falling back to mock data');
            fallbackToMockData();
          }

          setLoadingCalled = true;
          setLoading(false);
        } catch (secondError) {
          console.log('Alternative endpoint also failed:', secondError.message);
          fallbackToMockData();

          if (!setLoadingCalled) {
            setLoadingCalled = true;
            setLoading(false);
          }
        }
      } finally {
        // Ensure loading is false no matter what
        if (!setLoadingCalled) {
          setLoading(false);
        }
      }
    } catch (outerError) {
      console.error('Unhandled error in fetchAuctionDetails:', outerError);
      setError('An unexpected error occurred. Please try again later.');
      setLoading(false);
    }
  };

  const fallbackToMockData = () => {
    console.log('Using mock auction data');
    const mockAuctions = {
      1: {
        id: 1,
        title: 'Vintage Watch Collection',
        description: 'A rare collection of vintage watches from the 1950s, including pieces from top Swiss watchmakers. All watches are in working condition and have been professionally serviced within the last year. The collection includes 5 watches with original boxes and papers.',
        currentBid: 1200,
        minBidIncrement: 50,
        startingBid: 500,
        images: [
          'https://picsum.photos/id/28/800/600',
          'https://picsum.photos/id/29/800/600',
          'https://picsum.photos/id/30/800/600'
        ],
        endsAt: new Date(Date.now() + 86400000).toISOString(),
        seller: {
          id: 101,
          name: 'VintageCollector',
          rating: 4.8,
          since: '2020-05-15'
        },
        category: {
          id: 2,
          name: 'Collectibles'
        },
        condition: 'Excellent',
        location: 'New York, NY',
        shippingOptions: [
          { method: 'Standard Shipping', cost: 15 },
          { method: 'Express Shipping', cost: 25 }
        ],
        paymentMethods: ['Credit Card', 'PayPal'],
        returnPolicy: 'Returns accepted within 7 days if item not as described'
      }
    };

    const selectedAuction = mockAuctions[id] || mockAuctions[1];
    setAuction(selectedAuction);
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

        // Check if auction has been processed by the backend
        if (auction.status !== 'ended' && auction.status !== 'sold') {
          // Refresh auction details to see if backend has processed it
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

    // Add this function to check auction status when it ends
    const checkAuctionStatus = async () => {
      try {
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const response = await axios.get(`${API_URL}/api/v1/auctions/auctions/${id}/`, {
          headers
        });

        const auctionData = response.data.data || response.data;

        if (auctionData) {
          // Update auction with latest status
          setAuction(prevAuction => ({
            ...prevAuction,
            status: auctionData.status,
            currentBid: auctionData.current_price || auctionData.starting_price
          }));

          // Refresh bids to get winner information
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

      // For debugging
      console.log('Current bid:', currentBid);
      console.log('Min increment:', minIncrement);
      console.log('Calculated minimum bid:', minimumBid);
      console.log('User bid:', bidValue);

      if (isNaN(bidValue)) {
        setError('Please enter a valid amount');
        return;
      }

      // Use a small epsilon (0.001) to account for floating point imprecision
      const EPSILON = 0.001;

      if (bidValue <= currentBid) {
        setError(`Your bid must be higher than the current bid ($${formatCurrency(currentBid)})`);
        return;
      }

      // Check if bid is at least the minimum required amount (with a small tolerance)
      if (bidValue < minimumBid - EPSILON) {
        setError(`Minimum bid increment is $${formatCurrency(minIncrement)}. Please bid at least $${formatCurrency(minimumBid)}`);
        return;
      }

      setError('');

      // Try the specific auction bid endpoint
      let response;
      try {
        const auctionBidEndpoint = `/api/v1/auctions/auctions/${id}/bid/`;
        console.log(`Sending bid to: ${API_URL}${auctionBidEndpoint}`);

        response = await axios.post(`${API_URL}${auctionBidEndpoint}`, {
          amount: bidValue
        }, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
      } catch (auctionEndpointError) {
        // Try the general bids endpoint
        const generalBidEndpoint = `/api/v1/auctions/bids/`;
        console.log(`Sending bid to: ${API_URL}${generalBidEndpoint}`);

        response = await axios.post(`${API_URL}${generalBidEndpoint}`, {
          amount: bidValue,
          auction_id: id
        }, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
      }

      // Handle the response
      console.log('Bid response:', response.data);

      if (response.data && response.data.success) {
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
        setBidAmount(bidValue + auction.minBidIncrement);

        setTimeout(() => {
          setBidSuccess(false);
        }, 3000);
      } else {
        setError(response.data?.message || 'Failed to place bid');
      }
    } catch (error) {
      console.error('Error placing bid:', error);

      if (error.response) {
        setError(`Error ${error.response.status}: ${error.response.data?.message || 'Failed to place bid'}`);
      } else if (error.request) {
        setError('Network error. Please check your connection and try again.');
      } else {
        setError('Error: ' + error.message);
      }
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
        <p>Loading auction details...</p>
        <p className="loading-detail">Auction ID: {id}</p>
        <p className="loading-detail">Please wait while we fetch the auction information</p>
      </div>
    );
  }

  if (!auction && !loading) {
    return <div className="error-container">Auction not found</div>;
  }

  return (
    <div className="auction-detail-page">
      <div className="container">
        <div className="breadcrumb">
          <Link to="/">Home</Link> / <Link to="/auctions">Auctions</Link> / {auction.title}
        </div>

        <div className="auction-detail-container">
          <div className="auction-images">
            <div className="main-image">
              <img src={auction.images[0]} alt={auction.title} />
            </div>
            <div className="thumbnail-images">
              {auction.images.map((image, index) => (
                <div key={index} className="thumbnail">
                  <img src={image} alt={`${auction.title} - view ${index + 1}`} />
                </div>
              ))}
            </div>
          </div>

          <div className="auction-info">
            <h1>{auction.title}</h1>

            <div className="auction-meta">
              <p>Category: <span>{auction.category.name}</span></p>
              <p>Condition: <span>{auction.condition}</span></p>
              <p>Location: <span>{auction.location}</span></p>
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
                        type="text" // Change from "number" to "text"
                        id="bidAmount"
                        pattern="\d+(\.\d{1,2})?" // Use pattern to validate format
                        value={bidAmount}
                        onChange={(e) => {
                          // Only allow numeric input with up to 2 decimal places
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

                  {/* Add the AutoBidding component here */}
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

                      {/* Show this if current user is the winner */}
                      {isLoggedIn && bids[0].bidder_id === localStorage.getItem('user_id') && (
                        <div className="winner-info">
                          <p className="winner-badge">🏆 Congratulations! You won this auction!</p>
                          <p>The seller will contact you with shipping details.</p>
                          <Link to="/profile" className="btn btn-primary btn-sm">
                            View My Purchases
                          </Link>
                        </div>
                      )}

                      {/* Show this if current user is the seller */}
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
              <p>Seller: {auction.seller.name}</p>
              <p>Rating: {auction.seller.rating}/5</p>
              <p>Member since: {new Date(auction.seller.since).getFullYear()}</p>
              <Link to={`/seller/${auction.seller.id}`} className="btn btn-outline-small">View Seller Profile</Link>
            </div>
          </div>
        </div>

        <div className="auction-tabs">
          <div className="tabs-header">
            <button onClick={() => { handleTabChange("Description") }} className={`tab-btn ${activeTab === "Description" ? "active" : ""}`}>Description</button>
            <button onClick={() => { handleTabChange("Shipping & Payment") }} className={`tab-btn ${activeTab === "Shipping & Payment" ? "active" : ""}`}>Shipping & Payment</button>
            <button onClick={() => { handleTabChange("Bid History") }} className={`tab-btn ${activeTab === "Bid History" ? "active" : ""}`}>Bid History</button>
          </div>

          {activeTab === "Description" && <div className="tab-content">
            <div className="tab-pane active">
              <p>{auction.description}</p>
            </div>
          </div>}

          {activeTab === "Shipping & Payment" && <div className="shipping-payment">
            <h3>Shipping Options</h3>
            <ul className="shipping-list">
              {auction.shippingOptions.map((option, index) => (
                <li key={index}>
                  {option.method}: ${formatCurrency(option.cost)}
                </li>
              ))}
            </ul>

            <h3>Payment Methods</h3>
            <ul className="payment-list">
              {auction.paymentMethods.map((method, index) => (
                <li key={index}>{method}</li>
              ))}
            </ul>

            <h3>Return Policy</h3>
            <p>{auction.returnPolicy}</p>
          </div>}

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

        <div className="similar-auctions">
          <h2>Similar {auction.category.name} Auctions</h2>
          <div className="similar-grid">
            {similarAuctions.length > 0 ? (
              similarAuctions.map(similarAuction => (
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
              ))
            ) : (
              <p>No similar {auction.category.name} auctions found</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuctionDetailPage;