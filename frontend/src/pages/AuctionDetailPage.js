import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import '../styles/AuctionDetailPage.css';

const AuctionDetailPage = () => {
  const { id } = useParams();
  const [auction, setAuction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bidAmount, setBidAmount] = useState('');
  const [error, setError] = useState('');
  const [bidSuccess, setBidSuccess] = useState(false);
  const [bids, setBids] = useState([]);
  const [timeLeft, setTimeLeft] = useState('');
  
  // Check if user is logged in (would use context in a real app)
  const isLoggedIn = localStorage.getItem('userToken') !== null;

  useEffect(() => {
    const fetchAuctionDetails = async () => {
      try {
        // In a real app, fetch from API
        // const response = await axios.get(`/api/auctions/${id}`);
        // setAuction(response.data);
        
        // Mock data for the selected auction
        const mockAuction = {
          id: parseInt(id),
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
        };
        
        // Mock bid history
        const mockBids = [
          { id: 201, bidder: 'WatchFan23', amount: 1200, time: new Date(Date.now() - 3600000).toISOString() },
          { id: 202, bidder: 'CollectiblesLover', amount: 1150, time: new Date(Date.now() - 7200000).toISOString() },
          { id: 203, bidder: 'VintageFinder', amount: 1100, time: new Date(Date.now() - 10800000).toISOString() },
          { id: 204, bidder: 'TimePiece', amount: 1000, time: new Date(Date.now() - 14400000).toISOString() },
          { id: 205, bidder: 'WristWatchMan', amount: 900, time: new Date(Date.now() - 18000000).toISOString() },
        ];
        
        setAuction(mockAuction);
        setBids(mockBids);
        setLoading(false);
        
        // Set initial minimum bid
        setBidAmount(mockAuction.currentBid + mockAuction.minBidIncrement);
      } catch (error) {
        console.error('Error fetching auction details:', error);
        setLoading(false);
        setError('Could not load auction details. Please try again later.');
      }
    };
    
    fetchAuctionDetails();
  }, [id]);
  
  // Update time remaining
  useEffect(() => {
    if (!auction) return;
    
    const updateTimeLeft = () => {
      const endDate = new Date(auction.endsAt);
      const now = new Date();
      const timeRemaining = endDate - now;
      
      if (timeRemaining <= 0) {
        setTimeLeft('Auction ended');
        return;
      }
      
      const days = Math.floor(timeRemaining / (1000 * 60 * 60 * 24));
      const hours = Math.floor((timeRemaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((timeRemaining % (1000 * 60)) / 1000);
      
      setTimeLeft(`${days}d ${hours}h ${minutes}m ${seconds}s`);
    };
    
    updateTimeLeft();
    const interval = setInterval(updateTimeLeft, 1000);
    
    return () => clearInterval(interval);
  }, [auction]);
  
  // Handle placing a bid
  const handlePlaceBid = async (e) => {
    e.preventDefault();
    
    if (!isLoggedIn) {
      setError('You must be logged in to place a bid');
      return;
    }
    
    const bidValue = parseFloat(bidAmount);
    
    if (isNaN(bidValue)) {
      setError('Please enter a valid amount');
      return;
    }
    
    if (bidValue <= auction.currentBid) {
      setError(`Your bid must be higher than the current bid ($${auction.currentBid})`);
      return;
    }
    
    if (bidValue < auction.currentBid + auction.minBidIncrement) {
      setError(`Minimum bid increment is $${auction.minBidIncrement}`);
      return;
    }
    
    setError('');
    
    try {
      // In a real app, send to API
      // await axios.post(`/api/auctions/${id}/bid`, {
      //   amount: bidValue
      // });
      
      // Mock successful bid
      console.log(`Placed bid of $${bidValue}`);
      
      // Update auction with new bid
      setAuction({
        ...auction,
        currentBid: bidValue
      });
      
      // Add new bid to history
      const newBid = {
        id: Date.now(),
        bidder: 'You',
        amount: bidValue,
        time: new Date().toISOString()
      };
      
      setBids([newBid, ...bids]);
      setBidSuccess(true);
      setBidAmount(bidValue + auction.minBidIncrement);
      
      // Reset success message after 3 seconds
      setTimeout(() => {
        setBidSuccess(false);
      }, 3000);
    } catch (error) {
      console.error('Error placing bid:', error);
      setError('Failed to place bid. Please try again.');
    }
  };
  
  // Format date for display
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
    return <div className="loading-container">Loading auction details...</div>;
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
                <p className="current-bid-amount">${auction.currentBid.toFixed(2)}</p>
                <p className="bid-count">{bids.length} bids</p>
                <p className="time-remaining">{timeLeft}</p>
              </div>
              
              {new Date(auction.endsAt) > new Date() ? (
                <div className="place-bid">
                  {error && <div className="error-message">{error}</div>}
                  {bidSuccess && <div className="success-message">Your bid was placed successfully!</div>}
                  
                  <form onSubmit={handlePlaceBid}>
                    <div className="bid-input-group">
                      <label htmlFor="bidAmount">Your Bid ($)</label>
                      <input
                        type="number"
                        id="bidAmount"
                        min={auction.currentBid + auction.minBidIncrement}
                        step="0.01"
                        value={bidAmount}
                        onChange={(e) => setBidAmount(e.target.value)}
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
                    <p>Minimum bid: ${(auction.currentBid + auction.minBidIncrement).toFixed(2)}</p>
                    <p>Bid increment: ${auction.minBidIncrement.toFixed(2)}</p>
                  </div>
                </div>
              ) : (
                <div className="auction-ended">
                  <p>This auction has ended</p>
                  {bids.length > 0 ? (
                    <p>Winning bid: ${bids[0].amount.toFixed(2)} by {bids[0].bidder}</p>
                  ) : (
                    <p>No bids were placed</p>
                  )}
                </div>
              )}
            </div>
            
            <div className="seller-info">
              <h3>Seller Information</h3>
              <p>Seller: {auction.seller.name}</p>
              <p>Rating: {auction.seller.rating}/5</p>
              <p>Member since: {new Date(auction.seller.since).getFullYear()}</p>
              <Link to={`/user/${auction.seller.id}`} className="btn btn-outline-small">View Seller Profile</Link>
            </div>
          </div>
        </div>
        
        <div className="auction-tabs">
          <div className="tabs-header">
            <button className="tab-btn active">Description</button>
            <button className="tab-btn">Shipping & Payment</button>
            <button className="tab-btn">Bid History</button>
          </div>
          
          <div className="tab-content">
            <div className="tab-pane active">
              <h3>Item Description</h3>
              <p>{auction.description}</p>
            </div>
          </div>
          
          <div className="shipping-payment">
            <h3>Shipping Options</h3>
            <ul className="shipping-list">
              {auction.shippingOptions.map((option, index) => (
                <li key={index}>
                  {option.method}: ${option.cost.toFixed(2)}
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
          </div>
          
          <div className="bid-history">
            <h3>Bid History</h3>
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
                      <td>${bid.amount.toFixed(2)}</td>
                      <td>{formatDate(bid.time)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
        
        <div className="similar-auctions">
          <h2>Similar Auctions</h2>
          <div className="similar-grid">
            <div className="auction-card-small">
              <img src="https://picsum.photos/id/29/300/200" alt="Similar auction" />
              <div className="auction-card-info">
                <h3>Another Vintage Collection</h3>
                <p>$950</p>
                <Link to="/auction/2" className="btn btn-small">View</Link>
              </div>
            </div>
            <div className="auction-card-small">
              <img src="https://picsum.photos/id/30/300/200" alt="Similar auction" />
              <div className="auction-card-info">
                <h3>Rare Coin Collection</h3>
                <p>$1,500</p>
                <Link to="/auction/3" className="btn btn-small">View</Link>
              </div>
            </div>
            <div className="auction-card-small">
              <img src="https://picsum.photos/id/31/300/200" alt="Similar auction" />
              <div className="auction-card-info">
                <h3>Vintage Camera Set</h3>
                <p>$750</p>
                <Link to="/auction/4" className="btn btn-small">View</Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuctionDetailPage;