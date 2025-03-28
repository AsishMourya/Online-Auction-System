import axios from 'axios';

// API base URL from environment variable
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for CORS with credentials
});

// Add a request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    // Add authorization header with JWT token if available
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // If the error is 401 and hasn't already been retried
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Attempt to refresh the token
        const refreshToken = localStorage.getItem('refreshToken');
        if (!refreshToken) {
          // No refresh token, redirect to login
          window.location.href = '/login';
          return Promise.reject(error);
        }

        const response = await axios.post(`${API_URL}/api/v1/accounts/token/refresh/`, {
          refresh: refreshToken
        });

        // Store the new token
        const { access } = response.data.data;
        localStorage.setItem('token', access);

        // Update the authorization header
        originalRequest.headers['Authorization'] = `Bearer ${access}`;

        // Retry the original request
        return axios(originalRequest);
      } catch (refreshError) {
        // If refreshing fails, redirect to login
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// API service methods
const apiService = {
  login: (credentials) => api.post('/api/v1/accounts/login/', credentials),
  register: (userData) => api.post('/api/v1/accounts/register/', userData),
  logout: (refreshToken) => api.post('/api/v1/accounts/logout/', { refresh: refreshToken }),
  getUserProfile: () => api.get('/api/v1/accounts/profile/'),
  updateUserProfile: (profileData) => api.put('/api/v1/accounts/profile/', profileData),
  getAddresses: () => api.get('/api/v1/accounts/addresses/'),
  createAddress: (addressData) => api.post('/api/v1/accounts/addresses/', addressData),
  updateAddress: (id, addressData) => api.put(`/api/v1/accounts/addresses/${id}/`, addressData),
  deleteAddress: (id) => api.delete(`/api/v1/accounts/addresses/${id}/`),
  setDefaultAddress: (id) => api.post(`/api/v1/accounts/addresses/${id}/set_default/`),
  getPaymentMethods: () => api.get('/api/v1/accounts/payment-methods/'),
  createPaymentMethod: (methodData) => api.post('/api/v1/accounts/payment-methods/', methodData),
  updatePaymentMethod: (id, methodData) => api.put(`/api/v1/accounts/payment-methods/${id}/`, methodData),
  deletePaymentMethod: (id) => api.delete(`/api/v1/accounts/payment-methods/${id}/`),
  getWallet: () => api.get('/api/v1/accounts/wallet/'),
  getBalance: () => api.get('/api/v1/transactions/account/balance/'),
  getCategories: () => api.get('/api/v1/auctions/categories/all/'),
  getAuctions: (params) => api.get('/api/v1/auctions/auctions/', { params }),
  searchAuctions: (params) => api.get('/api/v1/auctions/search/', { params }),
  getAuctionById: (id) => api.get(`/api/v1/auctions/auctions/${id}/`),
  createAuction: (auctionData) => {
    const formData = new FormData();

    if (auctionData.item_data) {
      Object.keys(auctionData.item_data).forEach(key => {
        if (key !== 'image_urls') {
          formData.append(`item_data[${key}]`, auctionData.item_data[key]);
        }
      });

      if (auctionData.item_data.image_urls) {
        auctionData.item_data.image_urls.forEach((url, index) => {
          formData.append(`item_data[image_urls][${index}]`, url);
        });
      }

      delete auctionData.item_data;
    }

    Object.keys(auctionData).forEach(key => {
      formData.append(key, auctionData[key]);
    });

    return api.post('/api/v1/auctions/auctions/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  updateAuction: (id, auctionData) => api.put(`/api/v1/auctions/auctions/${id}/`, auctionData),
  deleteAuction: (id) => api.delete(`/api/v1/auctions/auctions/${id}/`),
  cancelAuction: (id) => api.post(`/api/v1/auctions/auctions/${id}/cancel/`),
  watchAuction: (id) => api.post(`/api/v1/auctions/auctions/${id}/watch/`),
  unwatchAuction: (id) => api.post(`/api/v1/auctions/auctions/${id}/unwatch/`),
  getWatchedAuctions: () => api.get('/api/v1/auctions/auctions/watched/'),
  getMyAuctions: () => api.get('/api/v1/auctions/auctions/my_auctions/'),
  getAuctionStats: (id) => api.get(`/api/v1/auctions/auctions/${id}/stats/`),
  placeBid: (bidData) => api.post('/api/v1/auctions/bids/', bidData),
  getMyBids: () => api.get('/api/v1/auctions/bids/my_bids/'),
  getAutoBids: () => api.get('/api/v1/auctions/autobids/'),
  createAutoBid: (autoBidData) => api.post('/api/v1/auctions/autobids/', autoBidData),
  activateAutoBid: (id) => api.post(`/api/v1/auctions/autobids/${id}/activate/`),
  deactivateAutoBid: (id) => api.post(`/api/v1/auctions/autobids/${id}/deactivate/`),
  getNotifications: () => api.get('/api/v1/notifications/notifications/'),
  markNotificationAsRead: (id) => api.post(`/api/v1/notifications/notifications/${id}/mark_read/`),
  getNotificationPreferences: () => api.get('/api/v1/notifications/preferences/'),
  updateNotificationPreferences: (preferencesData) => api.put('/api/v1/notifications/preferences/', preferencesData),
  getTransactions: () => api.get('/api/v1/transactions/transactions/'),
  getTransactionById: (id) => api.get(`/api/v1/transactions/transactions/${id}/`),
  deleteAccount: () => api.delete('/api/v1/accounts/delete-account/')
};

export default apiService;