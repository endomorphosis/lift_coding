/**
 * API Configuration
 * Update BASE_URL to point to your backend server
 */

// Default to localhost for development
// Update this based on your environment
export const BASE_URL = 'http://localhost:8080';

// Session management
let sessionToken = null;
let userId = null;

export function setSession(token, user) {
  sessionToken = token;
  userId = user;
}

export function getSession() {
  return { token: sessionToken, userId };
}

export function clearSession() {
  sessionToken = null;
  userId = null;
}

/**
 * Get headers for API requests
 */
export function getHeaders(includeAuth = true) {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (includeAuth && sessionToken) {
    headers['Authorization'] = `Bearer ${sessionToken}`;
  }

  if (userId) {
    headers['X-User-ID'] = userId;
  }

  return headers;
}
