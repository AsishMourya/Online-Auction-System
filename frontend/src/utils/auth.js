import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Extract token from various response formats
const extractToken = (response) => {
  if (!response || !response.data) return null;
  
  // Try all possible locations
  if (response.data?.data?.access) return response.data.data.access;
  if (response.data?.access) return response.data.access;
  if (response.data?.token) return response.data.token;
  if (response.data?.data?.token) return response.data.data.token;
  
  // If response data is directly a string token
  if (typeof response.data === 'string' && response.data.startsWith('ey')) {
    return response.data;
  }
  
  return null;
};

// Extract refresh token
const extractRefreshToken = (response) => {
  if (!response || !response.data) return null;
  
  if (response.data?.data?.refresh) return response.data.data.refresh;
  if (response.data?.refresh) return response.data.refresh;
  
  return null;
};

// Extract user data
const extractUserData = (response) => {
  if (!response || !response.data) return null;
  
  if (response.data?.data?.user) return response.data.data.user;
  if (response.data?.user) return response.data.user;
  
  return null;
};

const auth = {
  login: async (email, password) => {
    try {
      console.log('Logging in with email:', email);
      
      const response = await axios.post(`${API_URL}/api/v1/accounts/login/`, {
        email,
        password
      });
      
      console.log('Login response status:', response.status);
      console.log('Login response raw data:', response.data);
      
      // Extract tokens and user data
      const token = extractToken(response);
      const refreshToken = extractRefreshToken(response);
      const userData = extractUserData(response);
      
      if (token) {
        console.log('Token found, storing in localStorage');
        localStorage.setItem('token', token);
        
        if (refreshToken) {
          localStorage.setItem('refreshToken', refreshToken);
        }
        
        if (userData) {
          localStorage.setItem('user', JSON.stringify(userData));
        }
        
        // Notify app of authentication change
        window.dispatchEvent(new Event('authStateChanged'));
        return true;
      } else {
        console.error('No token found in response');
        return false;
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  },
  
  register: async (userData) => {
    try {
      const response = await axios.post(`${API_URL}/api/v1/accounts/register/`, userData);
      return response.data;
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  },
  
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    window.dispatchEvent(new Event('authStateChanged'));
  },
  
  isLoggedIn: () => {
    return !!localStorage.getItem('token');
  },
  
  getToken: () => {
    return localStorage.getItem('token');
  },
  
  // Function to test if token is working
  testToken: async () => {
    const token = localStorage.getItem('token');
    if (!token) return { success: false, message: 'No token found' };
    
    try {
      const response = await axios.get(`${API_URL}/api/v1/accounts/debug-auth/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        message: error.message,
        status: error.response?.status,
        data: error.response?.data
      };
    }
  }
};

export default auth;