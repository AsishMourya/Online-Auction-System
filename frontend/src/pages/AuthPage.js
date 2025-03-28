import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import '../styles/AuthPage.css';

// API base URL from environment variable
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const AuthPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get('redirect') || '/';
  
  // Initialize login state based on URL path
  const [isLogin, setIsLogin] = useState(location.pathname !== '/register');
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',  // Added for backend requirement
    last_name: ''    // Added for backend requirement
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Update isLogin state when URL changes
  useEffect(() => {
    setIsLogin(location.pathname !== '/register');
  }, [location.pathname]);

  // Check if user is already logged in
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      navigate(redirect);
    }
  }, [navigate, redirect]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      // Registration validation
      if (!isLogin) {
        if (formData.password !== formData.confirmPassword) {
          setError('Passwords do not match');
          setLoading(false);
          return;
        }
        
        if (formData.password.length < 8) {
          setError('Password must be at least 8 characters long');
          setLoading(false);
          return;
        }
      }
      
      // Debug output to console
      console.log('Sending request to:', isLogin ? 
        `${API_URL}/api/v1/accounts/login/` : 
        `${API_URL}/api/v1/accounts/register/`);
      
      let response;
      
      if (isLogin) {
        // Login request
        const loginData = {
          email: formData.email,
          password: formData.password
        };
        
        console.log('Login data:', loginData);
        
        response = await axios.post(`${API_URL}/api/v1/accounts/login/`, loginData, {
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        console.log('Login response:', response.data);
        
        // Check if the response has the expected structure based on your API
        if (response.data?.data?.access) {
          // Store tokens in localStorage
          localStorage.setItem('token', response.data.data.access);
          localStorage.setItem('refreshToken', response.data.data.refresh);
          localStorage.setItem('user', JSON.stringify(response.data.data.user));

          // Dispatch event to notify other components about the auth state change
          window.dispatchEvent(new Event('authStateChanged'));

          console.log('Login successful');
          navigate(redirect);
        } else if (response.data?.success === false) {
          // Handle unsuccessful login from your API
          setError(response.data.message || 'Login failed');
        } else {
          // If the response structure doesn't match what we expect
          console.error('Unexpected response structure:', response.data);
          setError('Login failed - unexpected server response');
        }
        
      } else {
        // Register request
        const registerData = {
          username: formData.username,
          email: formData.email,
          password: formData.password,
          confirm_password: formData.confirmPassword,  // Match backend field name
          first_name: formData.first_name,
          last_name: formData.last_name
        };
        
        console.log('Register data:', registerData);
        
        response = await axios.post(`${API_URL}/api/v1/accounts/register/`, registerData, {
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        console.log('Registration response:', response.data);
        
        // Check response structure
        if (response.data?.success === true) {
          console.log('Registration successful');
          
          // If tokens are returned immediately after registration
          if (response.data.data?.access) {
            localStorage.setItem('token', response.data.data.access);
            localStorage.setItem('refreshToken', response.data.data.refresh);
            localStorage.setItem('user', JSON.stringify(response.data.data.user));

            // Dispatch event to notify other components about the auth state change
            window.dispatchEvent(new Event('authStateChanged'));

            navigate(redirect);
          } else {
            // If not immediately logged in, redirect to login
            navigate('/login?registered=true');
          }
        } else if (response.data?.success === false) {
          // API returned an error message
          setError(response.data.message || 'Registration failed');
          
          // If there are field-specific errors
          if (response.data.errors) {
            const errorMessages = [];
            Object.entries(response.data.errors).forEach(([field, errors]) => {
              if (Array.isArray(errors)) {
                errorMessages.push(`${field}: ${errors.join(' ')}`);
              } else {
                errorMessages.push(`${field}: ${errors}`);
              }
            });
            
            if (errorMessages.length > 0) {
              setError(errorMessages.join('. '));
            }
          }
        } else {
          // If the response structure doesn't match what we expect
          console.error('Unexpected response structure:', response.data);
          setError('Registration failed - unexpected server response');
        }
      }
    } catch (err) {
      console.error('Auth error:', err);
      
      // Detailed error logging
      if (err.response) {
        console.error('Error response data:', err.response.data);
        console.error('Error response status:', err.response.status);
        console.error('Error response headers:', err.response.headers);
        
        // Handle different error status codes
        if (err.response.status === 400) {
          // Bad Request - likely validation errors
          if (err.response.data?.errors) {
            const errorMessages = [];
            
            Object.entries(err.response.data.errors).forEach(([field, errors]) => {
              if (Array.isArray(errors)) {
                errorMessages.push(`${field}: ${errors.join(' ')}`);
              } else if (typeof errors === 'string') {
                errorMessages.push(`${field}: ${errors}`);
              } else {
                errorMessages.push(`${field}: Invalid input`);
              }
            });
            
            if (errorMessages.length > 0) {
              setError(errorMessages.join('. '));
            } else {
              setError(err.response.data.message || 'Validation error');
            }
          } else {
            setError(err.response.data.message || 'Invalid request data');
          }
        } else if (err.response.status === 401) {
          // Unauthorized - wrong credentials
          setError('Invalid email or password');
        } else if (err.response.status === 403) {
          // Forbidden - CSRF or permissions issue
          setError('Access denied. Please try again later.');
        } else if (err.response.status === 404) {
          // Not Found - wrong endpoint
          setError('Service unavailable. Please try again later.');
        } else if (err.response.status === 405) {
          // Method Not Allowed
          setError('Invalid request method. Please try again later.');
          console.error('You are likely using the wrong HTTP method (GET vs POST)');
        } else if (err.response.status === 500) {
          // Server Error
          setError('Server error. Please try again later.');
        } else {
          // Other error
          setError(`Error: ${err.response.data.message || 'Authentication failed'}`);
        }
      } else if (err.request) {
        // No response received
        console.error('No response received:', err.request);
        setError('No response from server. Please check your internet connection.');
      } else {
        // Error setting up request
        console.error('Error message:', err.message);
        setError('Failed to send request.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Update switch button handler to change URL
  const handleSwitchMode = () => {
    if (isLogin) {
      navigate(`/register${redirect !== '/' ? `?redirect=${redirect}` : ''}`);
    } else {
      navigate(`/login${redirect !== '/' ? `?redirect=${redirect}` : ''}`);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-form-container">
          <h1>{isLogin ? 'Login' : 'Create an Account'}</h1>
          
          {/* Show success message if redirected from registration */}
          {searchParams.get('registered') === 'true' && (
            <div className="success-message">
              Registration successful! Please log in with your credentials.
            </div>
          )}
          
          {error && <div className="error-message">{error}</div>}
          
          <form onSubmit={handleSubmit}>
            {!isLogin && (
              <>
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
              </>
            )}
            
            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
              />
            </div>
            
            {!isLogin && (
              <div className="form-group">
                <label htmlFor="confirmPassword">Confirm Password</label>
                <input
                  type="password"
                  id="confirmPassword"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                />
              </div>
            )}
            
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Please wait...' : isLogin ? 'Login' : 'Register'}
            </button>
          </form>
          
          <div className="auth-switch">
            {isLogin ? "Don't have an account?" : "Already have an account?"}
            <button 
              className="switch-btn" 
              onClick={handleSwitchMode}
            >
              {isLogin ? 'Register' : 'Login'}
            </button>
          </div>
          
          {isLogin && (
            <div className="forgot-password">
              <a href="/forgot-password">Forgot your password?</a>
            </div>
          )}
        </div>
        
        <div className="auth-info">
          <div className="auth-info-content">
            <h2>Welcome to Online Auction System</h2>
            <p>Join our community of buyers and sellers to discover unique items or sell your valuables to interested bidders.</p>
            
            <div className="features">
              <div className="feature">
                <div className="feature-icon">🔒</div>
                <div className="feature-text">
                  <h3>Secure Transactions</h3>
                  <p>Our platform ensures your payments and personal information are always protected.</p>
                </div>
              </div>
              
              <div className="feature">
                <div className="feature-icon">🏆</div>
                <div className="feature-text">
                  <h3>Trusted Community</h3>
                  <p>Join thousands of verified users with review systems to ensure trust.</p>
                </div>
              </div>
              
              <div className="feature">
                <div className="feature-icon">💰</div>
                <div className="feature-text">
                  <h3>Competitive Bidding</h3>
                  <p>Find the best deals or get the best price for your items through our auction system.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;