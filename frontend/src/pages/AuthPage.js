import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import '../styles/AuthPage.css';
import auth from '../utils/auth';

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
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: ''
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
      
      if (isLogin) {
        // Login request using auth utility
        const success = await auth.login(formData.email, formData.password);
        
        if (success) {
          navigate(redirect);
        } else {
          setError('Login failed - could not authenticate with provided credentials');
        }
      } else {
        // Register request
        const registerData = {
          email: formData.email,
          password: formData.password,
          confirm_password: formData.confirmPassword,
          first_name: formData.first_name,
          last_name: formData.last_name
        };
        
        const response = await auth.register(registerData);
        
        // Rest of your registration handling code
        // ...
      }
    } catch (err) {
      // Your existing error handling code
      console.error('Auth error:', err);
      
      if (err.response) {
        console.error('Error response data:', err.response.data);
        console.error('Error response status:', err.response.status);
        console.error('Error response headers:', err.response.headers);
        
        if (err.response.status === 400) {
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
          setError('Invalid email or password');
        } else if (err.response.status === 403) {
          setError('Access denied. Please try again later.');
        } else if (err.response.status === 404) {
          setError('Service unavailable. Please try again later.');
        } else if (err.response.status === 405) {
          setError('Invalid request method. Please try again later.');
          console.error('You are likely using the wrong HTTP method (GET vs POST)');
        } else if (err.response.status === 500) {
          setError('Server error. Please try again later.');
        } else {
          setError(`Error: ${err.response.data.message || 'Authentication failed'}`);
        }
      } else if (err.request) {
        console.error('No response received:', err.request);
        setError('No response from server. Please check your internet connection.');
      } else {
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