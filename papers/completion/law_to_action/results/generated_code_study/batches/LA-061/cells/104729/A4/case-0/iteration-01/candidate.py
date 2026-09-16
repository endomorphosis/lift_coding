# Authenticate to Xbox Network (Xbox Network) in Node.js using @xboxreplay/xboxlive-auth

import { XboxLiveAuth } from '@xboxreplay/xboxlive-auth';

const auth = new XboxLiveAuth();

// Exchange authorization code for tokens
const tokens = await auth.exchangeCode(code);

// Get XSTS token and user hash
const xstsToken = tokens.xstsToken;
const userHash = tokens.userHash;

// Return the authentication result
return { kind: 'success', tokens: { xstsToken, userHash } } };