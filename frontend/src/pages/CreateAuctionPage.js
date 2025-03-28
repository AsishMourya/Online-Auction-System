import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/CreateAuctionPage.css';

// API base URL from environment variable
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const CreateAuctionPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category_id: '',
    starting_price: '',
    min_bid_increment: '',
    duration: '7',
    condition: 'new',
    location: '',
    images: [],
    shipping_options: [{ method: 'Standard Shipping', cost: '' }],
    payment_methods: ['Credit Card', 'PayPal'],
    return_policy: ''
  });
  const [categories, setCategories] = useState([]);
  const [previewImages, setPreviewImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // For image preview
  const handleImageChange = (e) => {
    const files = Array.from(e.target.files);
    
    if (files.length > 5) {
      setError('You can upload a maximum of 5 images');
      return;
    }
    
    setFormData({
      ...formData,
      images: files
    });
    
    // Generate preview URLs
    const imagePreviews = files.map(file => URL.createObjectURL(file));
    setPreviewImages(imagePreviews);
  };
  
  // Handle form input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };
  
  // Handle shipping option changes
  const handleShippingChange = (index, field, value) => {
    const updatedShipping = [...formData.shipping_options];
    updatedShipping[index] = {
      ...updatedShipping[index],
      [field]: value
    };
    
    setFormData({
      ...formData,
      shipping_options: updatedShipping
    });
  };
  
  // Add a new shipping option
  const addShippingOption = () => {
    setFormData({
      ...formData,
      shipping_options: [
        ...formData.shipping_options,
        { method: '', cost: '' }
      ]
    });
  };
  
  // Remove a shipping option
  const removeShippingOption = (index) => {
    const updatedShipping = [...formData.shipping_options];
    updatedShipping.splice(index, 1);
    
    setFormData({
      ...formData,
      shipping_options: updatedShipping
    });
  };
  
  // Handle payment method changes
  const handlePaymentChange = (method, checked) => {
    let updatedPayments;
    
    if (checked) {
      updatedPayments = [...formData.payment_methods, method];
    } else {
      updatedPayments = formData.payment_methods.filter(item => item !== method);
    }
    
    setFormData({
      ...formData,
      payment_methods: updatedPayments
    });
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    // Validation
    if (parseFloat(formData.starting_price) <= 0) {
      setError('Starting bid must be greater than zero');
      setLoading(false);
      return;
    }
    
    if (parseFloat(formData.min_bid_increment) <= 0) {
      setError('Minimum bid increment must be greater than zero');
      setLoading(false);
      return;
    }
    
    if (formData.images.length === 0) {
      setError('Please upload at least one image');
      setLoading(false);
      return;
    }
    
    try {
      // Create form data for API
      const auctionData = new FormData();
      
      // Calculate end date based on duration
      const endDate = new Date();
      endDate.setDate(endDate.getDate() + parseInt(formData.duration));
      
      // Add text fields
      auctionData.append('title', formData.title);
      auctionData.append('description', formData.description);
      auctionData.append('category_id', formData.category_id);
      auctionData.append('starting_price', formData.starting_price);
      auctionData.append('min_bid_increment', formData.min_bid_increment);
      auctionData.append('condition', formData.condition);
      auctionData.append('location', formData.location);
      auctionData.append('end_time', endDate.toISOString());
      auctionData.append('return_policy', formData.return_policy);
      
      // Add JSON fields
      auctionData.append('shipping_options', JSON.stringify(formData.shipping_options));
      auctionData.append('payment_methods', JSON.stringify(formData.payment_methods));
      
      // Add image files
      formData.images.forEach((image, index) => {
        auctionData.append(`images[${index}]`, image);
      });
      
      // Get the authentication token
      const token = localStorage.getItem('token');
      
      if (!token) {
        navigate('/login?redirect=create-auction');
        return;
      }
      
      // Call API
      const response = await axios.post(`${API_URL}/api/v1/auctions/auctions/`, auctionData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Auction created successfully', response.data);
      
      // Redirect to the new auction page
      navigate(`/auction/${response.data.data.id}`);
      
    } catch (error) {
      console.error('Error creating auction:', error);
      
      // Handle different types of errors
      if (error.response) {
        // The request was made and the server responded with a status code outside of 2xx
        if (error.response.status === 401) {
          setError('You must be logged in to create an auction');
          navigate('/login?redirect=create-auction');
        } else if (error.response.data && error.response.data.message) {
          setError(error.response.data.message);
        } else {
          setError('Failed to create auction. Please try again.');
        }
      } else if (error.request) {
        // The request was made but no response was received
        setError('No response from server. Please check your internet connection and try again.');
      } else {
        // Something happened in setting up the request
        setError('Failed to create auction. Please try again.');
      }
      
      setLoading(false);
    }
  };
  
  // Fetch categories on component mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        // Real API call to fetch categories
        const response = await axios.get(`${API_URL}/api/v1/auctions/categories/all/`);
        
        // Check if data exists and has the expected structure
        if (response.data && response.data.data && response.data.data.categories) {
          setCategories(response.data.data.categories);
        } else {
          // Fallback to mock data if response format is unexpected
          console.warn('Unexpected API response format. Using mock data.');
          setCategories([
            { id: 1, name: 'Electronics' },
            { id: 2, name: 'Collectibles' },
            { id: 3, name: 'Fashion' },
            { id: 4, name: 'Home & Garden' },
            { id: 5, name: 'Vehicles' }
          ]);
        }
      } catch (error) {
        console.error('Error fetching categories:', error);
        // Use mock data as fallback
        setCategories([
          { id: 1, name: 'Electronics' },
          { id: 2, name: 'Collectibles' },
          { id: 3, name: 'Fashion' },
          { id: 4, name: 'Home & Garden' },
          { id: 5, name: 'Vehicles' },
          { id: 6, name: 'Art' },
          { id: 7, name: 'Jewelry & Watches' },
          { id: 8, name: 'Books & Magazines' },
          { id: 9, name: 'Sports Equipment' },
          { id: 10, name: 'Toys & Hobbies' }
        ]);
      }
    };
    
    // Check if user is logged in
    const token = localStorage.getItem('token');
    if (!token) {
      // Redirect to login with return URL
      navigate('/login?redirect=create-auction');
      return;
    }
    
    fetchCategories();
  }, [navigate]);

  return (
    <div className="create-auction-page">
      <div className="container">
        <h1>Create New Auction</h1>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit} className="auction-form">
          <div className="form-section">
            <h2>Basic Information</h2>
            
            <div className="form-group">
              <label htmlFor="title">Item Title*</label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                required
                maxLength="100"
                placeholder="Enter a descriptive title"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="description">Item Description*</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                required
                rows="6"
                placeholder="Provide detailed information about your item including condition, features, history, etc."
              ></textarea>
            </div>
            
            <div className="form-row">
              <div className="form-group half">
                <label htmlFor="category_id">Category*</label>
                <select
                  id="category_id"
                  name="category_id"
                  value={formData.category_id}
                  onChange={handleChange}
                  required
                >
                  <option value="">Select a category</option>
                  {categories.map(category => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="form-group half">
                <label htmlFor="condition">Item Condition*</label>
                <select
                  id="condition"
                  name="condition"
                  value={formData.condition}
                  onChange={handleChange}
                  required
                >
                  <option value="new">New</option>
                  <option value="like-new">Like New</option>
                  <option value="excellent">Excellent</option>
                  <option value="good">Good</option>
                  <option value="fair">Fair</option>
                  <option value="poor">Poor</option>
                </select>
              </div>
            </div>
            
            <div className="form-group">
              <label htmlFor="location">Item Location</label>
              <input
                type="text"
                id="location"
                name="location"
                value={formData.location}
                onChange={handleChange}
                placeholder="City, State or Country"
              />
            </div>
          </div>
          
          <div className="form-section">
            <h2>Pricing & Duration</h2>
            
            <div className="form-row">
              <div className="form-group half">
                <label htmlFor="starting_price">Starting Bid*</label>
                <input
                  type="number"
                  id="starting_price"
                  name="starting_price"
                  value={formData.starting_price}
                  onChange={handleChange}
                  required
                  min="0.01"
                  step="0.01"
                  placeholder="Enter starting bid amount"
                />
              </div>
              
              <div className="form-group half">
                <label htmlFor="min_bid_increment">Minimum Bid Increment*</label>
                <input
                  type="number"
                  id="min_bid_increment"
                  name="min_bid_increment"
                  value={formData.min_bid_increment}
                  onChange={handleChange}
                  required
                  min="0.01"
                  step="0.01"
                  placeholder="Enter minimum bid increment"
                />
              </div>
            </div>
            
            <div className="form-group">
              <label htmlFor="duration">Auction Duration (days)*</label>
              <select
                id="duration"
                name="duration"
                value={formData.duration}
                onChange={handleChange}
                required
              >
                {[1, 3, 5, 7, 10, 14].map(day => (
                  <option key={day} value={day}>{day} days</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="form-section">
            <h2>Shipping & Payment</h2>
            
            <div className="form-group">
              <label>Shipping Options</label>
              {formData.shipping_options.map((option, index) => (
                <div key={index} className="shipping-option">
                  <input
                    type="text"
                    placeholder="Shipping method"
                    value={option.method}
                    onChange={(e) => handleShippingChange(index, 'method', e.target.value)}
                  />
                  <input
                    type="number"
                    placeholder="Cost"
                    value={option.cost}
                    onChange={(e) => handleShippingChange(index, 'cost', e.target.value)}
                  />
                  {formData.shipping_options.length > 1 && (
                    <button type="button" onClick={() => removeShippingOption(index)}>
                      Remove
                    </button>
                  )}
                </div>
              ))}
              <button type="button" onClick={addShippingOption}>
                Add Shipping Option
              </button>
            </div>
            
            <div className="form-group">
              <label>Accepted Payment Methods</label>
              {['Credit Card', 'PayPal', 'Bank Transfer', 'Cash on Delivery'].map(method => (
                <div key={method}>
                  <input
                    type="checkbox"
                    checked={formData.payment_methods.includes(method)}
                    onChange={(e) => handlePaymentChange(method, e.target.checked)}
                  />
                  <label>{method}</label>
                </div>
              ))}
            </div>
          </div>
          
          <div className="form-section">
            <h2>Images</h2>
            
            <div className="form-group">
              <label>Upload Images (Max 5)*</label>
              <input 
                type="file" 
                multiple 
                accept="image/*" 
                onChange={handleImageChange} 
                required={previewImages.length === 0}
              />
              <p className="form-hint">First image will be used as the main image</p>
              <div className="image-preview">
                {previewImages.map((src, index) => (
                  <img key={index} src={src} alt={`Preview ${index}`} />
                ))}
              </div>
            </div>
          </div>
          
          <div className="form-section">
            <h2>Return Policy</h2>
            <textarea
              id="return_policy"
              name="return_policy"
              value={formData.return_policy}
              onChange={handleChange}
              rows="4"
              placeholder="Describe your return policy (if any)"
            ></textarea>
          </div>
          
          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Submitting...' : 'Create Auction'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default CreateAuctionPage;