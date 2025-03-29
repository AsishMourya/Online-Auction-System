import axios from 'axios';

// Create an API base URL - in production, use environment variable
export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with defaults
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Add request interceptor to include auth token
apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// Add response interceptor for debugging
apiClient.interceptors.response.use(
  response => {
    console.log(`API Success: ${response.config.method.toUpperCase()} ${response.config.url}`);
    return response;
  },
  error => {
    console.error(`API Error: ${error.config?.method?.toUpperCase()} ${error.config?.url}`, 
                  error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// API methods
const api = {
  // Auctions - updated to match your backend URLs
  getAuctions: (params) => apiClient.get('/api/v1/auctions/auctions/', { params }),
  getAuctionById: (id) => apiClient.get(`/api/v1/auctions/auctions/${id}/`),
  createAuction: (data) => apiClient.post('/api/v1/auctions/auctions/', data),
  placeBid: (auctionId, amount) => apiClient.post(`/api/v1/auctions/auctions/${auctionId}/bid/`, { amount }),
  
  // Auto-bidding
  getAutoBidForAuction: (auctionId) => 
    apiClient.get(`/api/v1/auctions/autobids/?auction_id=${auctionId}`),
    
  setAutoBid: (auctionId, data) => 
    apiClient.post('/api/v1/auctions/autobids/', {
      auction_id: auctionId,
      ...data
    }),
    
  updateAutoBid: (autoBidId, data) => 
    apiClient.put(`/api/v1/auctions/autobids/${autoBidId}/`, data),
    
  disableAutoBid: (auctionId) => 
    apiClient.post(`/api/v1/auctions/autobids/disable/`, {
      auction_id: auctionId
    }),

  // Categories
  getCategories: () => apiClient.get('/api/v1/auctions/categories/'),
  getAllCategories: () => apiClient.get('/api/v1/auctions/categories/all/'),
  
  // User & Wallet
  login: (credentials) => apiClient.post('/api/v1/accounts/login/', credentials),
  register: (userData) => apiClient.post('/api/v1/accounts/register/', userData),
  getProfile: () => apiClient.get('/api/v1/accounts/profile/'),
  getWallet: () => apiClient.get('/api/v1/accounts/wallet/'),
  
  // Transactions
  getTransactions: () => apiClient.get('/api/v1/transactions/transactions/'),
  deposit: (amount) => apiClient.post('/api/v1/transactions/deposit/', { amount }),
  quickDeposit: (amount) => apiClient.post('/api/v1/transactions/quick-deposit/', { amount }),

  // Diagnostics
  testApi: () => apiClient.get('/api/v1/auctions/test/'),
  debugUrls: () => apiClient.get('/api/v1/auctions/debug-urls/'),
  runDiagnostics: async () => {
    const results = {};
    const endpoints = [
      { name: 'API Test', path: '/api/v1/auctions/test/' },
      { name: 'Debug URLs', path: '/api/v1/auctions/debug-urls/' },
      { name: 'Auctions', path: '/api/v1/auctions/auctions/' },
      { name: 'Categories', path: '/api/v1/auctions/categories/' },
      { name: 'Wallet', path: '/api/v1/accounts/wallet/' }
    ];
    
    for (const endpoint of endpoints) {
      try {
        const response = await apiClient.get(endpoint.path);
        results[endpoint.name] = { 
          status: 'Success', 
          statusCode: response.status,
          data: response.data
        };
      } catch (error) {
        results[endpoint.name] = { 
          status: 'Failed', 
          statusCode: error.response?.status || 'Network Error',
          error: error.response?.data || error.message
        };
      }
    }
    
    console.log('API Diagnostics Results:', results);
    return results;
  }
};

export default api;