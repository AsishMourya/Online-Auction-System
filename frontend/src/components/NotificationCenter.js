import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FaBell, FaCheckCircle, FaTimes } from 'react-icons/fa';
import '../styles/NotificationCenter.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const NotificationCenter = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    fetchNotifications();
    
    // Poll for new notifications every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchNotifications = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const response = await axios.get(`${API_URL}/api/v1/notifications/notifications/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const notificationsData = response.data?.data || response.data || [];
      setNotifications(notificationsData);
      
      // Count unread notifications
      const unread = notificationsData.filter(n => !n.read_at).length;
      setUnreadCount(unread);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const markAsRead = async (id) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      await axios.post(`${API_URL}/api/v1/notifications/notifications/${id}/mark_read/`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Update local state
      setNotifications(notifications.map(n => 
        n.id === id ? { ...n, read_at: new Date().toISOString() } : n
      ));
      
      // Update unread count
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      await axios.post(`${API_URL}/api/v1/notifications/notifications/mark_all_read/`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Update local state
      setNotifications(notifications.map(n => ({
        ...n, 
        read_at: n.read_at || new Date().toISOString()
      })));
      
      // Reset unread count
      setUnreadCount(0);
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) {
      return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
    }
  };

  const toggleNotifications = () => {
    setShowNotifications(!showNotifications);
    
    // If opening notifications and there are unread ones, mark them as read after a delay
    if (!showNotifications && unreadCount > 0) {
      setTimeout(() => {
        markAllAsRead();
      }, 3000); // Mark all as read after 3 seconds of viewing
    }
  };

  const getNotificationIcon = (type) => {
    // You can customize this based on notification types
    switch (type) {
      case 'bid':
        return <span className="notification-type-icon bid">💰</span>;
      case 'outbid':
        return <span className="notification-type-icon outbid">📊</span>;
      case 'auction_end':
        return <span className="notification-type-icon end">🏁</span>;
      case 'auction_won':
        return <span className="notification-type-icon won">🏆</span>;
      case 'payment':
        return <span className="notification-type-icon payment">💳</span>;
      default:
        return <span className="notification-type-icon">📣</span>;
    }
  };

  return (
    <div className="notification-center">
      <button className="notification-icon" onClick={toggleNotifications}>
        <FaBell />
        {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
      </button>
      
      {showNotifications && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <h3>Notifications</h3>
            <div className="notification-actions">
              {notifications.length > 0 && (
                <button className="mark-all-read" onClick={markAllAsRead}>
                  Mark all as read
                </button>
              )}
              <button className="close-btn" onClick={() => setShowNotifications(false)}>
                <FaTimes />
              </button>
            </div>
          </div>
          
          {notifications.length === 0 ? (
            <div className="no-notifications">
              <p>No notifications yet</p>
            </div>
          ) : (
            <div className="notification-list">
              {notifications.map(notification => (
                <div 
                  key={notification.id} 
                  className={`notification-item ${!notification.read_at ? 'unread' : ''}`}
                  onClick={() => markAsRead(notification.id)}
                >
                  <div className="notification-icon-wrapper">
                    {getNotificationIcon(notification.type)}
                  </div>
                  <div className="notification-content">
                    <h4>{notification.title}</h4>
                    <p>{notification.message}</p>
                    <span className="notification-time">{formatDate(notification.created_at)}</span>
                  </div>
                  {notification.read_at && (
                    <div className="read-status">
                      <FaCheckCircle />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          
          <div className="notification-footer">
            <a href="/notifications" className="view-all">View all notifications</a>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationCenter;