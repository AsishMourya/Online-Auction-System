import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import '../styles/NotificationCenter.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const NotificationCenter = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [allNotificationsOpen, setAllNotificationsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      setError('');
      
      const token = localStorage.getItem('token');
      if (!token) {
        console.log('No token found, skipping notification fetch');
        setLoading(false);
        return;
      }

      console.log('Fetching notifications...');
      
      const response = await axios.get(`${API_URL}/api/v1/notifications/notifications/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      console.log('Notifications response:', response.data);
      
      // Handle different response formats
      let notificationsData;
      if (Array.isArray(response.data)) {
        notificationsData = response.data;
      } else if (response.data?.data && Array.isArray(response.data.data)) {
        notificationsData = response.data.data;
      } else if (response.data?.notifications && Array.isArray(response.data.notifications)) {
        notificationsData = response.data.notifications;
      } else {
        console.warn('Unexpected notifications data format:', response.data);
        notificationsData = [];
      }
      
      // Get locally marked read notifications from localStorage
      const locallyReadIds = [];
      try {
        const readFromStorage = JSON.parse(localStorage.getItem('readNotifications') || '[]');
        if (Array.isArray(readFromStorage)) {
          readFromStorage.forEach(id => locallyReadIds.push(id));
          console.log('Found locally marked read notifications:', locallyReadIds);
        }
      } catch (e) {
        console.error('Error parsing localStorage readNotifications:', e);
      }
      
      // Format notifications and apply read status from both API and localStorage
      const formattedNotifications = notificationsData.map(notification => {
        const isLocallyRead = locallyReadIds.includes(notification.id);
        
        return {
          id: notification.id,
          message: notification.message || notification.content || 'New notification',
          createdAt: notification.created_at || notification.timestamp || new Date().toISOString(),
          // Mark as read if either the server says it's read OR it's in our localStorage
          read: Boolean(notification.read) || isLocallyRead,
          type: notification.type || 'general',
          link: notification.link || null,
          actionId: notification.action_id || notification.auction_id || null
        };
      });
      
      // Sort by date (newest first)
      formattedNotifications.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      
      // Count unread notifications
      const unreadCount = formattedNotifications.filter(n => !n.read).length;
      console.log('Setting unread count to:', unreadCount);
      
      setNotifications(formattedNotifications);
      setUnreadCount(unreadCount);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching notifications:', error);
      
      if (error.response?.status === 401) {
        setError('Please login to view notifications');
      } else {
        setError('Failed to load notifications');
      }
      
      setLoading(false);
      setNotifications([]);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      const token = localStorage.getItem('token');
      
      console.log(`Marking notification ${notificationId} as read...`);
      
      // Try the most common API patterns for marking notifications as read
      const endpoints = [
        // PATCH endpoint
        { 
          method: 'patch',
          url: `${API_URL}/api/v1/notifications/notifications/${notificationId}/`,
          data: { read: true }
        },
        // PUT endpoint
        { 
          method: 'put',
          url: `${API_URL}/api/v1/notifications/notifications/${notificationId}/`,
          data: { read: true }
        },
        // POST to dedicated endpoint
        { 
          method: 'post',
          url: `${API_URL}/api/v1/notifications/read/${notificationId}/`,
          data: {}
        },
        // POST with action parameter
        { 
          method: 'post',
          url: `${API_URL}/api/v1/notifications/notifications/${notificationId}/read/`,
          data: {}
        },
        // GET endpoint (some APIs use GET for this)
        { 
          method: 'get',
          url: `${API_URL}/api/v1/notifications/read/${notificationId}/`,
          data: null
        }
      ];
      
      let success = false;
      let lastError = null;
      
      // Try each endpoint until one works
      for (const endpoint of endpoints) {
        try {
          console.log(`Trying to mark as read with ${endpoint.method.toUpperCase()} to ${endpoint.url}`);
          
          if (endpoint.method === 'get') {
            await axios.get(endpoint.url, {
              headers: { 'Authorization': `Bearer ${token}` }
            });
          } else {
            await axios[endpoint.method](endpoint.url, endpoint.data, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            });
          }
          
          console.log(`Successfully marked notification as read with ${endpoint.method.toUpperCase()}`);
          success = true;
          break;
        } catch (err) {
          console.warn(`Failed with ${endpoint.method.toUpperCase()}: ${err.message}`);
          lastError = err;
        }
      }
      
      if (!success) {
        console.error('All marking approaches failed. Last error:', lastError);
        throw new Error('Failed to mark notification as read');
      }
      
      // Update local state regardless of API result
      setNotifications(prevNotifications => 
        prevNotifications.map(notification => 
          notification.id === notificationId 
            ? { ...notification, read: true } 
            : notification
        )
      );
      
      // Update unread count
      setUnreadCount(prev => Math.max(0, prev - 1));
      
      // Force a complete refresh after a short delay
      setTimeout(() => {
        console.log('Performing full refresh of notifications');
        fetchNotifications();
      }, 500);
      
    } catch (error) {
      console.error('Error marking notification as read:', error);
      
      // Create a local storage entry to track this notification as read
      // This is a fallback when the API fails
      try {
        const readNotifications = JSON.parse(localStorage.getItem('readNotifications') || '[]');
        if (!readNotifications.includes(notificationId)) {
          readNotifications.push(notificationId);
          localStorage.setItem('readNotifications', JSON.stringify(readNotifications));
          console.log('Saved read status to localStorage as fallback');
        }
      } catch (storageError) {
        console.error('Error saving to localStorage:', storageError);
      }
      
      // Update UI optimistically anyway
      setNotifications(prevNotifications => 
        prevNotifications.map(notification => 
          notification.id === notificationId 
            ? { ...notification, read: true } 
            : notification
        )
      );
      
      setUnreadCount(prev => Math.max(0, prev - 1));
    }
  };

  const markAllAsRead = async () => {
    try {
      const token = localStorage.getItem('token');
      const unreadNotifications = notifications.filter(n => !n.read);
      
      if (unreadNotifications.length === 0) {
        console.log('No unread notifications to mark');
        return;
      }
      
      console.log(`Marking ${unreadNotifications.length} notifications as read...`);
      
      // Try bulk endpoint first
      let bulkSuccess = false;
      
      // Common bulk endpoints to try
      const bulkEndpoints = [
        `${API_URL}/api/v1/notifications/mark-all-read/`,
        `${API_URL}/api/v1/notifications/read-all/`,
        `${API_URL}/api/v1/notifications/notifications/read-all/`
      ];
      
      for (const endpoint of bulkEndpoints) {
        try {
          console.log(`Trying bulk mark all read: ${endpoint}`);
          await axios.post(endpoint, {}, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
          console.log('Successfully marked all as read with bulk endpoint');
          bulkSuccess = true;
          break;
        } catch (err) {
          console.warn(`Bulk endpoint ${endpoint} failed:`, err.message);
        }
      }
      
      // If bulk endpoints fail, mark each notification individually
      if (!bulkSuccess) {
        console.log('Bulk endpoints failed, trying individual updates...');
        
        // Process notifications in batches to avoid too many parallel requests
        const batchSize = 3;
        const notificationIds = unreadNotifications.map(n => n.id);
        
        for (let i = 0; i < notificationIds.length; i += batchSize) {
          const batch = notificationIds.slice(i, i + batchSize);
          await Promise.all(batch.map(id => markAsRead(id)));
          console.log(`Processed batch ${i/batchSize + 1}`);
        }
      }
      
      // Store all notification IDs in localStorage as a fallback
      try {
        const allIds = notifications.map(n => n.id);
        localStorage.setItem('readNotifications', JSON.stringify(allIds));
        console.log('Saved all notifications as read to localStorage');
      } catch (e) {
        console.error('Error saving to localStorage:', e);
      }
      
      // Update state
      setNotifications(prevNotifications => 
        prevNotifications.map(notification => ({ ...notification, read: true }))
      );
      
      setUnreadCount(0);
      
      // Full refresh to sync with server
      setTimeout(fetchNotifications, 500);
      
    } catch (error) {
      console.error('Error in markAllAsRead:', error);
      
      // Optimistic UI update
      setNotifications(prevNotifications => 
        prevNotifications.map(notification => ({ ...notification, read: true }))
      );
      setUnreadCount(0);
      
      // Store in localStorage as fallback
      try {
        const allIds = notifications.map(n => n.id);
        localStorage.setItem('readNotifications', JSON.stringify(allIds));
      } catch (e) {
        console.error('Error saving to localStorage:', e);
      }
    }
  };

  const formatTimeAgo = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    
    if (diffSec < 60) return `${diffSec} seconds ago`;
    
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} minutes ago`;
    
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours} hours ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 30) return `${diffDays} days ago`;
    
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[date.getMonth()]} ${date.getDate()}`;
  };

  useEffect(() => {
    fetchNotifications();
    
    // Set up polling for new notifications
    const interval = setInterval(fetchNotifications, 60000); // Check every minute
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Handle clicks outside the dropdown to close it
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'bid': return '🔨';
      case 'auction_end': return '🏁';
      case 'win': return '🏆';
      case 'outbid': return '💰';
      case 'message': return '✉️';
      case 'system': return '⚙️';
      default: return '🔔';
    }
  };

  const toggleNotifications = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      // Fetch fresh notifications when opening
      fetchNotifications();
    }
  };

  const handleNotificationClick = (notification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
    
    // Close the dropdown after clicking a notification
    if (!allNotificationsOpen) {
      setIsOpen(false);
    }
  };

  const toggleAllNotifications = () => {
    const newValue = !allNotificationsOpen;
    setAllNotificationsOpen(newValue);
    
    // If opening all notifications, close the dropdown and fetch fresh data
    if (newValue) {
      setIsOpen(false);
      fetchNotifications();
    }
  };

  // Render All Notifications View
  if (allNotificationsOpen) {
    return (
      <div className="all-notifications-page">
        <div className="all-notifications-header">
          <h2>All Notifications</h2>
          <button onClick={toggleAllNotifications} className="close-btn">
            &times;
          </button>
        </div>
        
        <div className="notification-actions">
          <button onClick={markAllAsRead} className="mark-read-btn">
            Mark All as Read
          </button>
          <button onClick={fetchNotifications} className="refresh-btn">
            Refresh
          </button>
        </div>
        
        {loading && <div className="loading-notifications">Loading notifications...</div>}
        
        {error && <div className="notification-error">{error}</div>}
        
        {!loading && notifications.length === 0 && !error && (
          <div className="empty-notifications">
            <p>You don't have any notifications yet.</p>
            <p>Notifications will appear here when you receive bids, messages, or other updates.</p>
          </div>
        )}
        
        <div className="all-notifications-list">
          {notifications.map(notification => (
            <div 
              key={notification.id} 
              className={`notification-item ${notification.read ? '' : 'unread'}`}
              onClick={() => handleNotificationClick(notification)}
            >
              <div className="notification-icon">
                {getNotificationIcon(notification.type)}
              </div>
              <div className="notification-content">
                <p className="notification-message">
                  {notification.link ? (
                    <Link to={notification.link}>
                      {notification.message}
                    </Link>
                  ) : notification.actionId ? (
                    <Link to={`/auction/${notification.actionId}`}>
                      {notification.message}
                    </Link>
                  ) : (
                    notification.message
                  )}
                </p>
                <p className="notification-time">{formatTimeAgo(notification.createdAt)}</p>
              </div>
              <div className="notification-status">
                {!notification.read && <span className="unread-dot"></span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Render Notification Dropdown
  return (
    <div className="notification-center" ref={dropdownRef}>
      <button 
        className={`notification-button ${unreadCount > 0 ? 'has-notifications' : ''}`}
        onClick={toggleNotifications}
      >
        <span className="notification-icon">🔔</span>
        {unreadCount > 0 && (
          <span className="notification-count">{unreadCount}</span>
        )}
      </button>
      
      {isOpen && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <h3>Notifications</h3>
            {notifications.length > 0 && (
              <button onClick={markAllAsRead} className="mark-read-btn">
                Mark All as Read
              </button>
            )}
          </div>
          
          {loading && <div className="loading-notifications">Loading...</div>}
          
          {error && <div className="notification-error">{error}</div>}
          
          {!loading && notifications.length === 0 && !error && (
            <div className="empty-notifications">
              <p>No notifications yet</p>
            </div>
          )}
          
          <div className="notification-list">
            {notifications.slice(0, 5).map(notification => (
              <div 
                key={notification.id} 
                className={`notification-item ${notification.read ? '' : 'unread'}`}
                onClick={() => handleNotificationClick(notification)}
              >
                <div className="notification-icon">
                  {getNotificationIcon(notification.type)}
                </div>
                <div className="notification-content">
                  <p className="notification-message">
                    {notification.link ? (
                      <Link to={notification.link}>
                        {notification.message}
                      </Link>
                    ) : notification.actionId ? (
                      <Link to={`/auction/${notification.actionId}`}>
                        {notification.message}
                      </Link>
                    ) : (
                      notification.message
                    )}
                  </p>
                  <p className="notification-time">{formatTimeAgo(notification.createdAt)}</p>
                </div>
              </div>
            ))}
          </div>
          
          <div className="notification-footer">
            <button onClick={toggleAllNotifications} className="view-all-btn">
              View All Notifications
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationCenter;