import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/CreateAuctionPage.css';

const CreateAuctionPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    startingBid: '',
    minBidIncrement: '',
    duration: '7',
    condition: 'new',
    location: '',
    images: [],
    shippingOptions: [{ method: 'Standard Shipping', cost: '' }],
    paymentMethods: ['Credit Card', 'PayPal'],
    returnPolicy: ''
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
    const updatedShipping = [...formData.shippingOptions];
    updatedShipping[index] = {
      ...updatedShipping[index],
      [field]: value
    };
    
    setFormData({
      ...formData,
      shippingOptions: updatedShipping
    });
  };
  
  // Add a new shipping option
  const addShippingOption = () => {
    setFormData({
      ...formData,
      shippingOptions: [
        ...formData.shippingOptions,
        { method: '', cost: '' }
      ]
    });
  };
  
  // Remove a shipping option
  const removeShippingOption = (index) => {
    const updatedShipping = [...formData.shippingOptions];
    updatedShipping.splice(index, 1);
    
    setFormData({
      ...formData,
      shippingOptions: updatedShipping
    });
  };
  
  // Handle payment method changes
  const handlePaymentChange = (method, checked) => {
    let updatedPayments;
    
    if (checked) {
      updatedPayments = [...formData.paymentMethods, method];
    } else {
      updatedPayments = formData.paymentMethods.filter(item => item !== method);
    }
    
    setFormData({
      ...formData,
      paymentMethods: updatedPayments
    });
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    // Validation
    if (parseFloat(formData.startingBid) <= 0) {
      setError('Starting bid must be greater than zero');
      setLoading(false);
      return;
    }
    
    if (parseFloat(formData.minBidIncrement) <= 0) {
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
      // In a real app, create form data and send to API
      const auctionData = new FormData();
      
      // Add text fields
      for (const key in formData) {
        if (key !== 'images' && key !== 'shippingOptions' && key !== 'paymentMethods') {
          auctionData.append(key, formData[key]);
        }
      }
      
      // Add JSON fields
      auctionData.append('shippingOptions', JSON.stringify(formData.shippingOptions));
      auctionData.append('paymentMethods', JSON.stringify(formData.paymentMethods));
      
      // Add image files
      formData.images.forEach(image => {
        auctionData.append('images', image);
      });
      
      // Call API (commented out for mock)
      // const response = await axios.post('/api/auctions', auctionData, {
      //   headers: {
      //     'Content-Type': 'multipart/form-data'
      //   }
      // });
      
      // Mock successful creation
      console.log('Auction created successfully', formData);
      
      // Redirect to auction page (in a real app, would redirect to the new auction page)
      setTimeout(() => {
        navigate('/auctions');
      }, 1000);
      
    } catch (error) {
      console.error('Error creating auction:', error);
      setError('Failed to create auction. Please try again.');
      setLoading(false);
    }
  };
  
  // Fetch categories on component mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        // In a real app, fetch from API
        // const response = await axios.get('/api/categories');
        // setCategories(response.data);
        
        // Mock categories
        const mockCategories = [
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
        ];
        
        setCategories(mockCategories);
      } catch (error) {
        console.error('Error fetching categories:', error);
      }
    };
    
    // Check if user is logged in
    const token = localStorage.getItem('userToken');
    if (!token) {
      navigate('/login');
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
                <label htmlFor="category">Category*</label>
                <select
                  id="category"
                  name="category"
                  value={formData.category}
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
          </div>
          
          <div className="form-section">
            <h2>Pricing & Duration</h2>
            
            <div className="form-row">
              <div className="form-group half">
                <label htmlFor="startingBid">Starting Bid*</label>
                <input
                  type="number"
                  id="startingBid"
                  name="startingBid"
                  value={formData.startingBid}
                  onChange={handleChange}
                  required
                  min="0.01"
                  step="0.01"
                  placeholder="Enter starting bid amount"
                />
              </div>
              
              <div className="form-group half">
                <label htmlFor="minBidIncrement">Minimum Bid Increment*</label>
                <input
                  type="number"
                  id="minBidIncrement"
                  name="minBidIncrement"
                  value={formData.minBidIncrement}
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
              {formData.shippingOptions.map((option, index) => (
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
                  <button type="button" onClick={() => removeShippingOption(index)}>
                    Remove
                  </button>
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
                    checked={formData.paymentMethods.includes(method)}
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
              <input type="file" multiple accept="image/*" onChange={handleImageChange} />
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
              id="returnPolicy"
              name="returnPolicy"
              value={formData.returnPolicy}
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