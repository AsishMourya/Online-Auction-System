import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/CreateAuctionPage.css';
import { FaBell, FaEnvelope } from 'react-icons/fa';

// API base URL from environment variable
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const CreateAuctionPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category_id: '',
    starting_price: '',
    min_bid_increment: '10.00',
    duration: '7',
    condition: 'new',
    location: '',
    images: [],
    shipping_options: [{ method: 'Standard Shipping', cost: '15.00' }],
    payment_methods: ['Credit Card', 'PayPal'],
    return_policy: 'Returns accepted within 7 days if item not as described',
    auction_type: 'standard' // Add this line
  });
  const [categories, setCategories] = useState([]);
  const [previewImages, setPreviewImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [notificationPreferences, setNotificationPreferences] = useState({
    bid_notifications: true,
    outbid_notifications: true,
    auction_won_notifications: true,
    auction_ended_notifications: true,
    payment_notifications: true,
    admin_notifications: true,
    preferred_channels: ['email', 'in_app']
  });
  
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
    const newShippingOptions = [...formData.shipping_options];
    newShippingOptions[index] = {
      ...newShippingOptions[index],
      [field]: value
    };
    
    setFormData({
      ...formData,
      shipping_options: newShippingOptions
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
    const newShippingOptions = [...formData.shipping_options];
    newShippingOptions.splice(index, 1);
    
    setFormData({
      ...formData,
      shipping_options: newShippingOptions
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

  const handleNotificationChange = (field) => {
    setNotificationPreferences({
      ...notificationPreferences,
      [field]: !notificationPreferences[field]
    });
  };

  const handleChannelChange = (channel, checked) => {
    let updatedChannels;
    
    if (checked) {
      updatedChannels = [...notificationPreferences.preferred_channels, channel];
    } else {
      updatedChannels = notificationPreferences.preferred_channels.filter(c => c !== channel);
    }
    
    setNotificationPreferences({
      ...notificationPreferences,
      preferred_channels: updatedChannels
    });
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
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
    
    // Move these variables outside try-catch so they're accessible everywhere
    const token = localStorage.getItem('token');
    
    if (!token) {
      setError('Authentication required. You will be redirected to login.');
      setTimeout(() => navigate('/login?redirect=/create-auction'), 1500);
      setLoading(false);
      return;
    }
    
    // Calculate end date based on duration
    const endDate = new Date();
    endDate.setDate(endDate.getDate() + parseInt(formData.duration));
    
    // Add current date as start_time
    const startDate = new Date();
    
    // Add this special formatting for item_data - this is key
    const item_data = {
      name: formData.title, // Item name is required by ItemSerializer
      description: formData.description,
      condition: formData.condition,
      location: formData.location || "Not specified",
      shipping_options: formData.shipping_options,
      payment_methods: formData.payment_methods,
      return_policy: formData.return_policy || "No returns accepted",
      category: formData.category_id // Category is needed for the item
    };

    try {
      // Create form data for API
      const auctionData = new FormData();
      
      // Add basic fields
      auctionData.append('title', formData.title);
      auctionData.append('description', formData.description);
      auctionData.append('category_id', formData.category_id);
      auctionData.append('starting_price', formData.starting_price);
      auctionData.append('min_bid_increment', formData.min_bid_increment);
      auctionData.append('start_time', startDate.toISOString());
      auctionData.append('end_time', endDate.toISOString());
      auctionData.append('auction_type', formData.auction_type); // Add this line
      
      auctionData.append('item_data', JSON.stringify(item_data));

      // Debug logs
      console.log('FormData contents:');
      for (let [key, value] of auctionData.entries()) {
        console.log(`${key}: ${typeof value === 'object' ? 'File or Object' : value}`);
      }
      
      // Add image files only if there are any
      if (formData.images.length > 0) {
        formData.images.forEach((image, index) => {
          auctionData.append('image', image);
        });
      }
      
      // Call API
      const response = await axios.post(`${API_URL}/api/v1/auctions/auctions/`, auctionData, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Auction created successfully', response.data);
      
      // Show success message
      setSuccessMessage('Auction created successfully! Redirecting...');
      
      // Wait a moment to show the success message
      setTimeout(() => {
        // Redirect to the new auction page
        if (response.data?.data?.id) {
          navigate(`/auction/${response.data.data.id}`);
        } else if (response.data?.id) {
          navigate(`/auction/${response.data.id}`);
        } else {
          console.warn('Auction created but no ID returned. Redirecting to profile.');
          navigate('/profile');
        }
      }, 1500);

      try {
        const prefResponse = await axios.put(`${API_URL}/api/v1/notifications/preferences/`, notificationPreferences, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        console.log('Notification preferences updated successfully', prefResponse.data);
      } catch (notificationError) {
        console.error('Failed to update notification preferences:', notificationError);
        // Don't show error to user since auction was created successfully
      }
      
    } catch (error) {
      console.error('Error creating auction:', error);
      
      // Handle different types of errors
      if (error.response) {
        console.error('Error status:', error.response.status);
        console.error('Error data:', error.response.data);
        
        if (error.response.status === 401) {
          setError('Your session has expired. Please login again.');
          localStorage.removeItem('token');
          setTimeout(() => {
            navigate('/login?redirect=/create-auction');
          }, 1500);
        } 
        else if (error.response.status === 400) {
          // Format field-specific errors
          const errorMessages = [];
          if (error.response.data?.errors) {
            Object.entries(error.response.data.errors).forEach(([field, errors]) => {
              if (Array.isArray(errors)) {
                errorMessages.push(`${field}: ${errors.join(' ')}`);
              } else if (typeof errors === 'string') {
                errorMessages.push(`${field}: ${errors}`);
              }
            });
          }
          
          if (errorMessages.length > 0) {
            setError(errorMessages.join('. '));
          } else {
            setError(error.response.data?.message || 'Validation error');
          }
        }
        else {
          setError(`Error ${error.response.status}: ${error.response.data?.message || 'Failed to create auction.'}`);
        }
      } 
      else if (error.request) {
        setError('No response from server. Please check your internet connection.');
      } 
      else {
        setError('Failed to create auction. Please try again.');
      }
      
      // Now this section will have access to startDate, endDate, itemData, and token
      if (error.response && error.response.data?.errors?.item_data) {
        console.log('First attempt failed. Trying alternative format...');
        
        // Try a direct JSON submission instead of FormData
        const jsonPayload = {
          title: formData.title,
          description: formData.description,
          category_id: parseInt(formData.category_id),
          starting_price: parseFloat(formData.starting_price),
          min_bid_increment: parseFloat(formData.min_bid_increment),
          start_time: startDate.toISOString(),
          end_time: endDate.toISOString(),
          auction_type: formData.auction_type, // Add this line
          item_data: item_data // Use the properly formatted item_data
        };
        
        console.log('Sending direct JSON payload:', jsonPayload);
        
        try {
          // This now has access to token
          const response = await axios.post(`${API_URL}/api/v1/auctions/auctions/`, jsonPayload, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
          
          console.log('Alternative approach succeeded:', response.data);
          // Add success handling for alternative approach
          setSuccessMessage('Auction created successfully! Redirecting...');
          
          // Wait a moment to show the success message
          setTimeout(() => {
            // Redirect to the new auction page
            if (response.data?.data?.id) {
              navigate(`/auction/${response.data.data.id}`);
            } else if (response.data?.id) {
              navigate(`/auction/${response.data.id}`);
            } else {
              console.warn('Auction created but no ID returned. Redirecting to profile.');
              navigate('/profile');
            }
          }, 1500);
          
          return; // Stop further error handling
          
        } catch (alternativeError) {
          console.error('Alternative approach also failed:', alternativeError);
          console.error('Alternative approach detailed error:', 
            alternativeError.response?.data?.errors || 
            alternativeError.response?.data?.detail || 
            alternativeError.response?.data || 
            alternativeError.message
          );
          // Continue with your existing error handling...
        }
      }
      
      setLoading(false);
    }
  };
  
  // Fetch categories on component mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        
        const response = await axios.get(`${API_URL}/api/v1/auctions/categories/`, {
          headers
        });
        
        if (response.data && response.data.data) {
          setCategories(response.data.data);
        } else if (Array.isArray(response.data)) {
          setCategories(response.data);
        } else {
          // Fallback to mock data
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
          { id: 5, name: 'Vehicles' }
        ]);
      }
    };
    
    fetchCategories();
  }, [navigate]);

  return (
    <div className="create-auction-page">
      <div className="container">
        <h1>Create New Auction</h1>
        
        {error && <div className="error-message">{error}</div>}
        {successMessage && <div className="success-message">{successMessage}</div>}
        
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
              <div className="payment-methods">
                {['Credit Card', 'PayPal', 'Bank Transfer', 'Cash on Delivery'].map(method => (
                  <div key={method} className="payment-method-option">
                    <input
                      type="checkbox"
                      id={`payment-${method}`}
                      checked={formData.payment_methods.includes(method)}
                      onChange={(e) => handlePaymentChange(method, e.target.checked)}
                    />
                    <label htmlFor={`payment-${method}`}>{method}</label>
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          <div className="form-section">
            <h2>Images</h2>
            
            <div className="form-group">
              <label>Upload Images (Max 5)</label>
              <div className="image-upload-container">
                <div className="image-upload-box">
                  <input 
                    type="file" 
                    id="images"
                    multiple 
                    accept="image/*" 
                    onChange={handleImageChange}
                    className="file-input" 
                  />
                  <label htmlFor="images" className="file-input-label">
                    <span className="upload-icon">+</span>
                    <span>Click to select images</span>
                  </label>
                </div>
                <p className="form-hint">Images are optional. First image will be used as the main image if provided.</p>
                
                <div className="image-previews">
                  {previewImages.map((src, index) => (
                    <div key={index} className="image-preview">
                      <img src={src} alt={`Preview ${index}`} />
                    </div>
                  ))}
                </div>
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

          <div className="form-section">
            <h2>Notification Preferences</h2>
            <p className="form-hint">Choose when you want to receive notifications about this auction</p>
            
            <div className="notification-channels">
              <h3>Notification Channels</h3>
              <div className="channel-options">
                <div className="channel-option">
                  <input
                    type="checkbox"
                    id="channel-email"
                    checked={notificationPreferences.preferred_channels.includes('email')}
                    onChange={(e) => handleChannelChange('email', e.target.checked)}
                  />
                  <label htmlFor="channel-email">
                    <FaEnvelope className="channel-icon" />
                    Email Notifications
                  </label>
                </div>
                <div className="channel-option">
                  <input
                    type="checkbox"
                    id="channel-inapp"
                    checked={notificationPreferences.preferred_channels.includes('in_app')}
                    onChange={(e) => handleChannelChange('in_app', e.target.checked)}
                  />
                  <label htmlFor="channel-inapp">
                    <FaBell className="channel-icon" />
                    In-App Notifications
                  </label>
                </div>
              </div>
            </div>
            
            <div className="notification-types">
              <h3>Notification Types</h3>
              
              <div className="notification-option">
                <input
                  type="checkbox"
                  id="bid-notifications"
                  checked={notificationPreferences.bid_notifications}
                  onChange={() => handleNotificationChange('bid_notifications')}
                />
                <label htmlFor="bid-notifications">Bids placed on my auctions</label>
              </div>
              
              <div className="notification-option">
                <input
                  type="checkbox"
                  id="outbid-notifications"
                  checked={notificationPreferences.outbid_notifications}
                  onChange={() => handleNotificationChange('outbid_notifications')}
                />
                <label htmlFor="outbid-notifications">When I'm outbid on an auction</label>
              </div>
              
              <div className="notification-option">
                <input
                  type="checkbox"
                  id="auction-won-notifications"
                  checked={notificationPreferences.auction_won_notifications}
                  onChange={() => handleNotificationChange('auction_won_notifications')}
                />
                <label htmlFor="auction-won-notifications">When I win an auction</label>
              </div>
              
              <div className="notification-option">
                <input
                  type="checkbox"
                  id="auction-ended-notifications"
                  checked={notificationPreferences.auction_ended_notifications}
                  onChange={() => handleNotificationChange('auction_ended_notifications')}
                />
                <label htmlFor="auction-ended-notifications">When my auction ends</label>
              </div>
              
              <div className="notification-option">
                <input
                  type="checkbox"
                  id="payment-notifications"
                  checked={notificationPreferences.payment_notifications}
                  onChange={() => handleNotificationChange('payment_notifications')}
                />
                <label htmlFor="payment-notifications">Payment updates</label>
              </div>
            </div>
          </div>
          
          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Submitting...' : 'Create Auction'}
          </button>

          {/* Replace your test button with this final diagnostic version */}
          <button 
            type="button" 
            className="submit-button" 
            style={{marginTop: '10px', backgroundColor: '#d43f3a'}}
            onClick={async () => {
              try {
                const token = localStorage.getItem('token');
                
                if (!token) {
                  alert('Please login first');
                  return;
                }
                
                console.log('Running API diagnosis...');
                
                // 1. Test if API is reachable at all with a GET request
                try {
                  console.log('1. Testing API connectivity...');
                  const connectivityTest = await axios.get(
                    `${API_URL}/api/v1/auctions/auctions/`,
                    {
                      headers: {
                        'Authorization': `Bearer ${token}`
                      }
                    }
                  );
                  console.log('API connection successful:', connectivityTest.status);
                } catch (connectError) {
                  console.error('API connectivity test failed:', connectError);
                  alert('Cannot connect to API. Please check if backend server is running.');
                  return;
                }
                
                // 2. Try to create auction with minimal data and native fetch
                console.log('2. Testing with browser fetch API...');
                const minimalData = {
                  title: "Minimal Test " + new Date().getTime(),
                  description: "Testing with fetch API",
                  category_id: categories[0]?.id || 1,
                  starting_price: 100,
                  min_bid_increment: 10,
                  start_time: new Date().toISOString(),
                  end_time: new Date(Date.now() + 86400000).toISOString(),
                  item_data: {
                    condition: "new"
                  }
                };
                
                try {
                  const fetchResponse = await fetch(`${API_URL}/api/v1/auctions/auctions/`, {
                    method: 'POST',
                    headers: {
                      'Authorization': `Bearer ${token}`,
                      'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(minimalData)
                  });
                  
                  const fetchData = await fetchResponse.json();
                  
                  if (fetchResponse.ok) {
                    console.log('Fetch API succeeded:', fetchData);
                    alert('Created auction using fetch! Check console.');
                    return;
                  } else {
                    console.error('Fetch API failed:', fetchData);
                    console.log('Status:', fetchResponse.status);
                  }
                } catch (fetchError) {
                  console.error('Fetch execution error:', fetchError);
                }
                
                // 3. Check backend version/info if available
                try {
                  console.log('3. Checking API information...');
                  const infoResponse = await axios.get(
                    `${API_URL}/api/v1/info/`,
                    {
                      headers: {
                        'Authorization': `Bearer ${token}`
                      }
                    }
                  );
                  console.log('API info:', infoResponse.data);
                } catch (infoError) {
                  console.error('Could not get API info:', infoError);
                }
                
                // 4. Try OPTIONS request to get allowed methods and requirements
                try {
                  console.log('4. Checking API options...');
                  const optionsResponse = await axios.options(
                    `${API_URL}/api/v1/auctions/auctions/`,
                    {
                      headers: {
                        'Authorization': `Bearer ${token}`
                      }
                    }
                  );
                  console.log('API options:', optionsResponse.data);
                  console.log('Allowed methods:', optionsResponse.headers?.allow);
                } catch (optionsError) {
                  console.error('Could not get API options:', optionsError);
                }
                
                // 5. Final diagnostic information
                console.log('\n--- DIAGNOSTIC INFORMATION ---');
                console.log('API URL:', API_URL);
                console.log('Browser:', navigator.userAgent);
                console.log('React version:', React.version);
                console.log('Axios version:', axios.VERSION || 'unknown');
                
                alert('Diagnosis complete. Please check console and send to backend developer.');
                
              } catch (error) {
                console.error('Overall diagnosis error:', error);
                alert('Diagnosis failed: ' + error.message);
              }
            }}
          >
            Run API Diagnosis
          </button>
        </form>
      </div>
    </div>
  );
};

export default CreateAuctionPage;