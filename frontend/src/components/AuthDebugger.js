import React, { useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const AuthDebugger = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginResponse, setLoginResponse] = useState(null);
  const [authTestResponse, setAuthTestResponse] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleTestLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setLoginResponse(null);
    
    try {
      console.log('Attempting login with:', { email });
      
      const response = await axios.post(`${API_URL}/api/v1/accounts/login/`, {
        email,
        password
      });
      
      console.log('Login response:', response.data);
      setLoginResponse(response.data);
      
      // Try to extract token
      let token = null;
      if (response.data?.data?.access) {
        token = response.data.data.access;
      } else if (response.data?.access) {
        token = response.data.access;
      } else if (response.data?.token) {
        token = response.data.token;
      } else if (response.data?.data?.token) {
        token = response.data.data.token;
      }
      
      if (token) {
        console.log('Token found:', token.substring(0, 20) + '...');
        localStorage.setItem('token', token);
        
        // Test the token immediately
        await testAuthEndpoint(token);
      } else {
        setError('No token found in response');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message);
      if (err.response?.data) {
        setLoginResponse(err.response.data);
      }
    } finally {
      setLoading(false);
    }
  };
  
  const testAuthEndpoint = async (tokenToUse) => {
    try {
      const token = tokenToUse || localStorage.getItem('token');
      if (!token) {
        setError('No token available');
        return;
      }
      
      console.log('Testing auth with token:', token.substring(0, 20) + '...');
      console.log('Authorization header:', `Bearer ${token}`);
      
      const response = await axios.get(`${API_URL}/api/v1/auctions/test-auth/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Auth test response:', response.data);
      setAuthTestResponse(response.data);
    } catch (err) {
      console.error('Auth test error:', err);
      setError(err.message);
      if (err.response?.data) {
        setAuthTestResponse({
          error: true,
          status: err.response.status,
          data: err.response.data
        });
      }
    }
  };
  
  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', margin: '20px', maxWidth: '800px' }}>
      <h2>Authentication Debugger</h2>
      
      <form onSubmit={handleTestLogin} style={{ marginBottom: '20px' }}>
        <div style={{ marginBottom: '10px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>Email:</label>
          <input 
            type="email" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)}
            style={{ padding: '8px', width: '300px' }}
            required
          />
        </div>
        
        <div style={{ marginBottom: '10px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>Password:</label>
          <input 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)}
            style={{ padding: '8px', width: '300px' }}
            required
          />
        </div>
        
        <button 
          type="submit" 
          disabled={loading}
          style={{ padding: '8px 16px', background: '#4CAF50', color: 'white', border: 'none', borderRadius: '4px' }}
        >
          {loading ? 'Testing...' : 'Test Login & Auth'}
        </button>
        
        <button 
          type="button"
          onClick={() => testAuthEndpoint()}
          style={{ padding: '8px 16px', background: '#2196F3', color: 'white', border: 'none', borderRadius: '4px', marginLeft: '10px' }}
        >
          Test Existing Token
        </button>
      </form>
      
      {error && (
        <div style={{ padding: '10px', background: '#FFEBEE', border: '1px solid #FFCDD2', borderRadius: '4px', marginBottom: '15px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      
      <div style={{ display: 'flex', gap: '20px' }}>
        <div style={{ flex: 1 }}>
          <h3>Login Response</h3>
          {loginResponse && (
            <pre style={{ background: '#F5F5F5', padding: '10px', borderRadius: '4px', overflow: 'auto', maxHeight: '400px' }}>
              {JSON.stringify(loginResponse, null, 2)}
            </pre>
          )}
        </div>
        
        <div style={{ flex: 1 }}>
          <h3>Auth Test Response</h3>
          {authTestResponse && (
            <pre style={{ background: '#F5F5F5', padding: '10px', borderRadius: '4px', overflow: 'auto', maxHeight: '400px' }}>
              {JSON.stringify(authTestResponse, null, 2)}
            </pre>
          )}
        </div>
      </div>
      
      <div style={{ marginTop: '20px' }}>
        <h3>Current Token in Storage</h3>
        <pre style={{ background: '#F5F5F5', padding: '10px', borderRadius: '4px', overflow: 'auto', wordBreak: 'break-all' }}>
          {localStorage.getItem('token') || 'No token found'}
        </pre>
        
        <button 
          onClick={() => {
            const token = localStorage.getItem('token');
            if (!token) {
              alert('No token found');
              return;
            }
            
            try {
              // Split the token and decode the payload
              const parts = token.split('.');
              if (parts.length !== 3) {
                alert('Invalid token format');
                return;
              }
              
              const payload = JSON.parse(atob(parts[1]));
              alert('Token Payload:\n' + JSON.stringify(payload, null, 2));
            } catch (err) {
              alert('Error decoding token: ' + err.message);
            }
          }}
          style={{ padding: '8px 16px', background: '#FF9800', color: 'white', border: 'none', borderRadius: '4px', marginTop: '10px' }}
        >
          Decode Token
        </button>
      </div>
    </div>
  );
};

export default AuthDebugger;