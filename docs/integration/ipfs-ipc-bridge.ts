/**
 * IPFS Backend Integration - Electron IPC Bridge Contract
 *
 * These TypeScript types define the IPC message contract between the
 * Hallucinate App Electron frontend and the Python FastAPI backend for
 * IPFS operations (ipfs_kit_py, ipfs_datasets_py, ipfs_accelerate_py).
 *
 * The frontend calls these via HTTP to the backend at /v1/ipfs/*
 * or through the Electron main process IPC bridge.
 */

// --------------------------------------------------------------------------
// Status & Health
// --------------------------------------------------------------------------

export interface IPFSBackendStatus {
  ipfs_kit: {
    available: boolean;
    backends?: Record<string, {
      exists?: boolean;
      enabled?: boolean;
      simulation?: boolean;
      has_credentials?: boolean;
    }>;
    note?: string;
    error?: string;
  };
  ipfs_datasets: {
    available: boolean;
    routers?: {
      embeddings: string;
      ipfs: string;
      llm: string;
    };
    error?: string;
  };
  ipfs_accelerate: {
    available: boolean;
    webnn_webgpu_available?: boolean;
    llm_router_available?: boolean;
    embeddings_router_available?: boolean;
    model_manager_available?: boolean;
    instance_status?: unknown;
    error?: string;
  };
  timestamp: number;
}

// --------------------------------------------------------------------------
// IPFS Content Operations
// --------------------------------------------------------------------------

export interface IPFSAddRequest {
  /** Base64-encoded content to store */
  data_base64: string;
  /** Whether to pin the content (default: true) */
  pin?: boolean;
}

export interface IPFSAddResponse {
  cid: string | null;
  raw_result?: unknown;
}

export interface IPFSCatRequest {
  /** IPFS content identifier */
  cid: string;
}

export interface IPFSCatResponse {
  /** Base64-encoded content */
  data_base64: string | null;
  size: number;
}

export interface IPFSPinRequest {
  cid: string;
}

export interface IPFSPinResponse {
  ok: boolean;
  cid: string;
  result?: unknown;
}

export interface IPFSResolveRequest {
  cid: string;
}

export interface IPFSResolveResponse {
  ok: boolean;
  cid: string;
  result?: unknown;
}

// --------------------------------------------------------------------------
// AI/ML Operations (via IPFS Datasets & Accelerate routers)
// --------------------------------------------------------------------------

export interface IPFSEmbedRequest {
  texts: string[];
  model_name?: string | null;
  /** 'datasets' (default) or 'accelerate' */
  provider?: 'datasets' | 'accelerate' | null;
}

export interface IPFSEmbedResponse {
  embeddings: number[][];
  provider_used: string;
}

export interface IPFSGenerateRequest {
  prompt: string;
  model_name?: string | null;
  /** 'datasets' (default) or 'accelerate' */
  provider?: 'datasets' | 'accelerate' | null;
}

export interface IPFSGenerateResponse {
  text: string;
  provider_used: string;
}

// --------------------------------------------------------------------------
// Hardware Capabilities (ipfs_accelerate_py)
// --------------------------------------------------------------------------

export interface IPFSCapabilitiesResponse {
  ok: boolean;
  capabilities: {
    webnn_webgpu_available?: boolean;
    model_manager_available?: boolean;
    llm_router_available?: boolean;
    embeddings_router_available?: boolean;
    [key: string]: unknown;
  } | null;
  error?: string;
}

// --------------------------------------------------------------------------
// Electron IPC Channel Names
// --------------------------------------------------------------------------

/**
 * IPC channel names for the Electron main <-> renderer bridge.
 * The main process proxies these to the Python backend HTTP API.
 */
export const IPFS_IPC_CHANNELS = {
  STATUS: 'ipfs:status',
  ADD: 'ipfs:add',
  CAT: 'ipfs:cat',
  PIN: 'ipfs:pin',
  UNPIN: 'ipfs:unpin',
  RESOLVE: 'ipfs:resolve',
  EMBED: 'ipfs:embed',
  GENERATE: 'ipfs:generate',
  CAPABILITIES: 'ipfs:capabilities',
} as const;

export type IPFSIPCChannel = typeof IPFS_IPC_CHANNELS[keyof typeof IPFS_IPC_CHANNELS];

// --------------------------------------------------------------------------
// Electron IPC Handler Map (for main process registration)
// --------------------------------------------------------------------------

/**
 * Type-safe mapping from IPC channel to request/response types.
 * Use this in the Electron main process to register handlers:
 *
 * ```typescript
 * import { IPFSIPCHandlerMap, IPFS_IPC_CHANNELS } from './ipfs-ipc-bridge';
 *
 * ipcMain.handle(IPFS_IPC_CHANNELS.STATUS, async () => {
 *   const resp = await fetch(`${BACKEND_URL}/v1/ipfs/status`);
 *   return resp.json() as IPFSBackendStatus;
 * });
 * ```
 */
export interface IPFSIPCHandlerMap {
  [IPFS_IPC_CHANNELS.STATUS]: { request: void; response: IPFSBackendStatus };
  [IPFS_IPC_CHANNELS.ADD]: { request: IPFSAddRequest; response: IPFSAddResponse };
  [IPFS_IPC_CHANNELS.CAT]: { request: IPFSCatRequest; response: IPFSCatResponse };
  [IPFS_IPC_CHANNELS.PIN]: { request: IPFSPinRequest; response: IPFSPinResponse };
  [IPFS_IPC_CHANNELS.UNPIN]: { request: IPFSPinRequest; response: IPFSPinResponse };
  [IPFS_IPC_CHANNELS.RESOLVE]: { request: IPFSResolveRequest; response: IPFSResolveResponse };
  [IPFS_IPC_CHANNELS.EMBED]: { request: IPFSEmbedRequest; response: IPFSEmbedResponse };
  [IPFS_IPC_CHANNELS.GENERATE]: { request: IPFSGenerateRequest; response: IPFSGenerateResponse };
  [IPFS_IPC_CHANNELS.CAPABILITIES]: { request: void; response: IPFSCapabilitiesResponse };
}

// --------------------------------------------------------------------------
// Backend URL configuration
// --------------------------------------------------------------------------

/** Default backend URL for the Python FastAPI server */
export const DEFAULT_BACKEND_URL = 'http://localhost:8080';

/**
 * Build the full endpoint URL for an IPFS operation.
 */
export function getIPFSEndpointURL(
  operation: 'status' | 'add' | 'cat' | 'pin' | 'unpin' | 'resolve' | 'embed' | 'generate' | 'capabilities',
  backendUrl: string = DEFAULT_BACKEND_URL,
): string {
  return `${backendUrl}/v1/ipfs/${operation}`;
}
