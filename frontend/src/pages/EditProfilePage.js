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
  
  // Update the fetchUserData function to use your actual API
  const fetchUserData = async () => {
    try {
      setLoading(true);
      
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login?redirect=/profile/edit');
        return;
      }
      
      // Use your actual API endpoint
      const response = await axios.get(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/accounts/profile/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const userData = response.data.data || response.data;
      
      // Set form data with user data
      setFormData({
        first_name: userData.first_name || '',
        last_name: userData.last_name || '',
        email: userData.email || '',
        phone: userData.phone_number || '',
        address: userData.location || '',
        bio: userData.bio || '',
        avatar: null,
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
      
      // Set avatar preview
      setAvatarPreview(userData.avatar_url || null);
      
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
  
  // Update the handleSubmit function to use your actual API
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('You must be logged in to update your profile');
        setSaving(false);
        return;
      }
      
      // Prepare form data for API
      const apiFormData = {
        first_name: formData.first_name,
        last_name: formData.last_name,
        location: formData.address,
        bio: formData.bio,
        phone_number: formData.phone
      };
      
      // If avatar is changed, handle file upload
      if (formData.avatar) {
        // For file uploads, use FormData
        const imageFormData = new FormData();
        imageFormData.append('avatar', formData.avatar);
        
        await axios.post(
          `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/accounts/upload-avatar/`,
          imageFormData,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'multipart/form-data'
            }
          }
        );
      }
      
      // Update other profile information
      const response = await axios.put(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/accounts/profile/`,
        apiFormData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      setSuccess(true);
      
      // Update localStorage user data
      const updatedUser = response.data.data || response.data;
      const currentUser = JSON.parse(localStorage.getItem('user')) || {};
      localStorage.setItem('user', JSON.stringify({
        ...currentUser,
        ...updatedUser
      }));
      
      setSaving(false);
    } catch (error) {
      console.error('Error updating profile:', error);
      
      if (error.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError('Failed to update your profile. Please try again.');
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

  const handleDeleteAccount = async () => {
    // Show confirmation dialog
    const confirmed = window.confirm(
      'Are you sure you want to delete your account? This action cannot be undone and you will lose all your data, including auction history, bids, and personal information.'
    );
    
    if (!confirmed) {
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      
      const token = localStorage.getItem('token');
      if (!token) {
        setError('You must be logged in to delete your account');
        setSaving(false);
        return;
      }
      
      // Send delete request to backend
      await axios.delete(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/accounts/delete-account/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Clear all auth data
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      
      // Show success message and redirect
      alert('Your account has been successfully deleted. We\'re sorry to see you go!');
      
      // Notify other components about auth state change
      window.dispatchEvent(new Event('authStateChanged'));
      
      // Redirect to home page
      navigate('/');
    } catch (error) {
      console.error('Error deleting account:', error);
      
      if (error.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError('Failed to delete your account. Please try again later.');
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
                  <h4>Delete Account</h4>
                  <p>Permanently delete your account and all associated data. This action cannot be undone.</p>
                </div>
                <button 
                  type="button" 
                  className="btn btn-danger"
                  onClick={handleDeleteAccount}
                >
                  Delete Account
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EditProfilePage;