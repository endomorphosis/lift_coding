# Authenticate to Xbox Network (Xbox Live) in Node.js using @xboxreplay/xboxlive-auth

import { XboxLiveAuth } from '@xboxreplay/xboxlive-auth';

const auth = new XboxLiveAuth();

// Authenticate using OAuth 2.0
async function authenticateToXboxNetwork(payload) {
  try {
    // Get the access token from the payload
    const accessToken = payload.access_token;

    // Authenticate to Xbox Network
    const result = await auth.authenticate(accessToken);

    // Return the XSTS token and user hash
    return {
      xsts_token: result.xsts_token,
      user_hash: result.user_hash
    };
  } catch (error) {
    console.error('Authentication failed:', error);
    throw error;
  }
}

// Emit the allowed JSON record
function emit_allowed(payload) {
  console.log(JSON.stringify(payload));
}

// Main function to run the authentication
async function run(payload) {
  try {
    const authResult = await authenticateToXboxNetwork(payload);
    emit_allowed(authResult);
  } catch (error) {
    console.error('Error:', error);
  }
}

// Start the authentication process
run({});