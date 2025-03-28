import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import '../styles/EditProfilePage.css';

const EditProfilePage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    username: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    address: '',
    bio: '',
    avatar: null,
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  
  // Preview state for avatar
  const [avatarPreview, setAvatarPreview] = useState(null);
  
  // Check if user is logged in
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login?redirect=/profile/edit');
      return;
    }
    
    fetchUserData();
  }, [navigate]);
  
  // Fetch user data from API or localStorage
  const fetchUserData = async () => {
    try {
      setLoading(true);
      
      // In a real app, you would fetch the data from your API
      // const response = await axios.get('/api/v1/accounts/profile/', {
      //   headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      // });
      // const userData = response.data.data;
      
      // For now, use mock data or data from localStorage
      const userData = JSON.parse(localStorage.getItem('user')) || {};
      
      // Check if we have a complete user profile already
      // If not, simulate a more complete mock profile
      if (!userData.address || !userData.phone) {
        // Augment with mock data for fields your backend might not store yet
        Object.assign(userData, {
          username: userData.username || 'user123',
          first_name: userData.first_name || 'John',
          last_name: userData.last_name || 'Smith',
          email: userData.email || 'john.smith@example.com',
          phone: userData.phone || '(555) 123-4567',
          address: userData.address || '123 Main St, New York, NY 10001',
          bio: userData.bio || 'Passionate collector of vintage items and antiques. Always looking for unique pieces to add to my collection.',
          avatar: userData.avatar || 'https://picsum.photos/id/64/200/200'
        });
      }
      
      // Set form data with user data
      setFormData({
        username: userData.username || '',
        first_name: userData.first_name || '',
        last_name: userData.last_name || '',
        email: userData.email || '',
        phone: userData.phone || '',
        address: userData.address || '',
        bio: userData.bio || '',
        avatar: null,
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
      
      // Set avatar preview
      setAvatarPreview(userData.avatar);
      
      setLoading(false);
    } catch (error) {
      console.error('Error fetching user data:', error);
      setError('Failed to load your profile data. Please try again later.');
      setLoading(false);
    }
  };
  
  // Handle form input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };
  
  // Handle avatar file selection
  const handleAvatarChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({ ...prev, avatar: file }));
      
      // Create preview URL for the selected image
      const previewUrl = URL.createObjectURL(file);
      setAvatarPreview(previewUrl);
    }
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    
    // Validate form
    if (formData.new_password && formData.new_password !== formData.confirm_password) {
      setError('New password and confirm password do not match');
      setSaving(false);
      return;
    }
    
    try {
      // In a real app, you would send the data to your API
      // const formDataObj = new FormData();
      // Object.entries(formData).forEach(([key, value]) => {
      //   if (value !== null) {
      //     formDataObj.append(key, value);
      //   }
      // });
      
      // const response = await axios.put('/api/v1/accounts/profile/', formDataObj, {
      //   headers: { 
      //     Authorization: `Bearer ${localStorage.getItem('token')}`,
      //     'Content-Type': 'multipart/form-data' 
      //   }
      // });
      
      // For demo purposes, simulate a successful update
      // Update the user data in localStorage
      const currentUser = JSON.parse(localStorage.getItem('user')) || {};
      const updatedUser = {
        ...currentUser,
        username: formData.username,
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        phone: formData.phone,
        address: formData.address,
        bio: formData.bio,
        avatar: avatarPreview // In a real app, this would be a URL from your server
      };
      
      // Update localStorage
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSuccess(true);
      
      // Reset password fields
      setFormData(prev => ({
        ...prev,
        current_password: '',
        new_password: '',
        confirm_password: ''
      }));
      
      // Scroll to top to show success message
      window.scrollTo(0, 0);
      
      setSaving(false);
    } catch (error) {
      console.error('Error updating profile:', error);
      
      if (error.response) {
        // Handle specific API errors
        if (error.response.data?.message) {
          setError(error.response.data.message);
        } else if (error.response.data?.errors) {
          const errorMessages = [];
          Object.entries(error.response.data.errors).forEach(([field, msgs]) => {
            if (Array.isArray(msgs)) {
              errorMessages.push(`${field}: ${msgs.join(' ')}`);
            } else if (typeof msgs === 'string') {
              errorMessages.push(`${field}: ${msgs}`);
            }
          });
          setError(errorMessages.join('. '));
        } else {
          setError('Failed to update your profile. Please try again.');
        }
      } else {
        setError('Network error. Please check your internet connection.');
      }
      
      setSaving(false);
    }
  };
  
  // Handle password update
  const handlePasswordUpdate = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    
    // Validate passwords
    if (!formData.current_password) {
      setError('Current password is required');
      setSaving(false);
      return;
    }
    
    if (formData.new_password !== formData.confirm_password) {
      setError('New password and confirm password do not match');
      setSaving(false);
      return;
    }
    
    if (formData.new_password.length < 8) {
      setError('New password must be at least 8 characters long');
      setSaving(false);
      return;
    }
    
    try {
      // In a real app, you would send the password data to your API
      // const response = await axios.post('/api/v1/accounts/change-password/', {
      //   current_password: formData.current_password,
      //   new_password: formData.new_password
      // }, {
      //   headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      // });
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSuccess(true);
      
      // Reset password fields
      setFormData(prev => ({
        ...prev,
        current_password: '',
        new_password: '',
        confirm_password: ''
      }));
      
      // Scroll to top to show success message
      window.scrollTo(0, 0);
      
      setSaving(false);
    } catch (error) {
      console.error('Error updating password:', error);
      
      if (error.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError('Failed to update your password. Please check your current password and try again.');
      }
      
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="loading-container">Loading your profile...</div>;
  }

  return (
    <div className="edit-profile-page">
      <div className="container">
        <div className="page-header">
          <h1>Edit Profile</h1>
          <Link to="/profile" className="btn btn-outline">Back to Profile</Link>
        </div>
        
        {error && (
          <div className="alert alert-error">
            <i className="fas fa-exclamation-circle"></i> {error}
          </div>
        )}
        
        {success && (
          <div className="alert alert-success">
            <i className="fas fa-check-circle"></i> Your profile has been updated successfully!
          </div>
        )}
        
        <div className="edit-profile-container">
          <div className="profile-sections">
            <div className="section personal-info">
              <h2>Personal Information</h2>
              <form onSubmit={handleSubmit}>
                <div className="avatar-upload">
                  <div className="avatar-preview">
                    <img src={avatarPreview} alt="Profile" />
                  </div>
                  <div className="avatar-edit">
                    <label htmlFor="avatar-input" className="btn btn-secondary">
                      Change Photo
                    </label>
                    <input
                      type="file"
                      id="avatar-input"
                      accept="image/*"
                      onChange={handleAvatarChange}
                      className="hidden-input"
                    />
                    <p className="upload-hint">JPG, PNG or GIF, max 5MB</p>
                  </div>
                </div>
                
                <div className="form-group">
                  <label htmlFor="username">Username</label>
                  <input
                    type="text"
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    required
                  />
                </div>
                
                <div className="form-row">
                  <div className="form-group half">
                    <label htmlFor="first_name">First Name</label>
                    <input
                      type="text"
                      id="first_name"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  
                  <div className="form-group half">
                    <label htmlFor="last_name">Last Name</label>
                    <input
                      type="text"
                      id="last_name"
                      name="last_name"
                      value={formData.last_name}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label htmlFor="email">Email Address</label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    disabled // Email is typically not changeable without verification
                  />
                  <span className="input-note">Contact customer support to change your email address</span>
                </div>
                
                <div className="form-group">
                  <label htmlFor="phone">Phone Number</label>
                  <input
                    type="tel"
                    id="phone"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="address">Address</label>
                  <textarea
                    id="address"
                    name="address"
                    value={formData.address}
                    onChange={handleChange}
                    rows="3"
                  ></textarea>
                </div>
                
                <div className="form-group">
                  <label htmlFor="bio">Bio</label>
                  <textarea
                    id="bio"
                    name="bio"
                    value={formData.bio}
                    onChange={handleChange}
                    rows="4"
                    placeholder="Tell others a bit about yourself..."
                  ></textarea>
                </div>
                
                <div className="form-actions">
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? 'Saving Changes...' : 'Save Changes'}
                  </button>
                  <Link to="/profile" className="btn btn-outline">Cancel</Link>
                </div>
              </form>
            </div>
            
            <div className="section password-section">
              <h2>Change Password</h2>
              <form onSubmit={handlePasswordUpdate}>
                <div className="form-group">
                  <label htmlFor="current_password">Current Password</label>
                  <input
                    type="password"
                    id="current_password"
                    name="current_password"
                    value={formData.current_password}
                    onChange={handleChange}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="new_password">New Password</label>
                  <input
                    type="password"
                    id="new_password"
                    name="new_password"
                    value={formData.new_password}
                    onChange={handleChange}
                    required
                    minLength="8"
                  />
                  <span className="input-note">Password must be at least 8 characters long</span>
                </div>
                
                <div className="form-group">
                  <label htmlFor="confirm_password">Confirm New Password</label>
                  <input
                    type="password"
                    id="confirm_password"
                    name="confirm_password"
                    value={formData.confirm_password}
                    onChange={handleChange}
                    required
                  />
                </div>
                
                <div className="form-actions">
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? 'Updating Password...' : 'Update Password'}
                  </button>
                </div>
              </form>
            </div>
            
            <div className="section notification-section">
              <h2>Notification Preferences</h2>
              <form>
                <div className="toggle-group">
                  <div className="toggle-control">
                    <label className="toggle-switch">
                      <input type="checkbox" defaultChecked />
                      <span className="toggle-slider"></span>
                    </label>
                    <div className="toggle-label">
                      <h4>Email Notifications</h4>
                      <p>Receive emails about bids, outbids, and auction results</p>
                    </div>
                  </div>
                </div>
                
                <div className="toggle-group">
                  <div className="toggle-control">
                    <label className="toggle-switch">
                      <input type="checkbox" defaultChecked />
                      <span className="toggle-slider"></span>
                    </label>
                    <div className="toggle-label">
                      <h4>Auction Ending Reminders</h4>
                      <p>Get notified when watched auctions are about to end</p>
                    </div>
                  </div>
                </div>
                
                <div className="toggle-group">
                  <div className="toggle-control">
                    <label className="toggle-switch">
                      <input type="checkbox" defaultChecked />
                      <span className="toggle-slider"></span>
                    </label>
                    <div className="toggle-label">
                      <h4>Marketing Communications</h4>
                      <p>Receive newsletters and promotional offers</p>
                    </div>
                  </div>
                </div>
                
                <div className="form-actions">
                  <button type="button" className="btn btn-primary" disabled={saving}>
                    Save Preferences
                  </button>
                </div>
              </form>
            </div>
            
            <div className="section danger-zone">
              <h2>Account Management</h2>
              <div className="danger-action">
                <div className="danger-info">
                  <h4>Deactivate Account</h4>
                  <p>Temporarily disable your account. You can reactivate it at any time by logging in.</p>
                </div>
                <button className="btn btn-warning">Deactivate</button>
              </div>
              
              <div className="danger-action">
                <div className="danger-info">
                  <h4>Delete Account</h4>
                  <p>Permanently delete your account and all associated data. This action cannot be undone.</p>
                </div>
                <button className="btn btn-danger">Delete Account</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EditProfilePage;