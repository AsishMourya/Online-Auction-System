import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create a reusable axios instance with authentication
const createAuthAxios = () => {
  const token = localStorage.getItem('token');
  
  return axios.create({
    baseURL: API_URL,
    headers: {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }
  });
};

// API endpoints
const api = {
  // Authentication
  login: (credentials) => {
    return axios.post(`${API_URL}/api/v1/accounts/login/`, credentials);
  },
  
  register: (userData) => {
    return axios.post(`${API_URL}/api/v1/accounts/register/`, userData);
  },
  
  refreshToken: (refreshToken) => {
    return axios.post(`${API_URL}/api/v1/accounts/token/refresh/`, { refresh: refreshToken });
  },
  
  // Auctions
  getAuctions: (params = {}) => {
    return createAuthAxios().get('/api/v1/auctions/auctions/', { params });
  },
  
  getAuction: (id) => {
    return createAuthAxios().get(`/api/v1/auctions/auctions/${id}/`);
  },
  
  createAuction: (auctionData) => {
    const authAxios = createAuthAxios();
    // Change content type for form data
    authAxios.defaults.headers['Content-Type'] = 'multipart/form-data';
    return authAxios.post('/api/v1/auctions/auctions/', auctionData);
  },
  
  placeBid: (auctionId, amount) => {
    return createAuthAxios().post(`/api/v1/auctions/auctions/${auctionId}/bid/`, { amount });
  },
  
  getAuctionBids: (auctionId) => {
    return createAuthAxios().get(`/api/v1/auctions/auctions/${auctionId}/bids/`);
  },
  
  // Categories
  getCategories: () => {
    return createAuthAxios().get('/api/v1/auctions/categories/');
  },
  
  // User profile
  getUserProfile: () => {
    return createAuthAxios().get('/api/v1/accounts/profile/');
  },
  
  updateUserProfile: (profileData) => {
    return createAuthAxios().put('/api/v1/accounts/profile/', profileData);
  }
};

export default api;