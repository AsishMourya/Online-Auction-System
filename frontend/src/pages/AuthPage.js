import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/AuthPage.css';

const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

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
      if (!isLogin && formData.password !== formData.confirmPassword) {
        setError('Passwords do not match');
        setLoading(false);
        return;
      }
      
      if (isLogin) {
        // Login request
        // const response = await axios.post('/api/users/login', {
        //   email: formData.email,
        //   password: formData.password
        // });
        
        // Mock successful login
        console.log('Login successful');
        localStorage.setItem('userToken', 'mock-token-12345');
        navigate('/');
      } else {
        // Register request
        // const response = await axios.post('/api/users/register', {
        //   name: formData.name,
        //   email: formData.email,
        //   password: formData.password
        // });
        
        // Mock successful registration
        console.log('Registration successful');
        localStorage.setItem('userToken', 'mock-token-12345');
        navigate('/');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-form-container">
          <h1>{isLogin ? 'Login' : 'Create an Account'}</h1>
          
          {error && <div className="error-message">{error}</div>}
          
          <form onSubmit={handleSubmit}>
            {!isLogin && (
              <div className="form-group">
                <label htmlFor="name">Full Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required={!isLogin}
                />
              </div>
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
                  required={!isLogin}
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
              onClick={() => setIsLogin(!isLogin)}
            >
              {isLogin ? 'Register' : 'Login'}
            </button>
          </div>
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