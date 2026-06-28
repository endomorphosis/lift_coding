# IPFS Backend Integration - Hallucinate App & SwissKnife

## Overview

This document describes how `ipfs_accelerate_py`, `ipfs_kit_py`, and
`ipfs_datasets_py` integrate with the Hallucinate App (Electron) and
SwissKnife virtual desktop through the handsfree backend API.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Hallucinate App (Electron)                                          │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐   │
│  │  Renderer Process  │  │  Main Process (IPC Bridge)            │   │
│  │  (React/Vue UI)    │──│  ipfs-ipc-bridge.ts                   │   │
│  └────────────────────┘  └────────────────┬─────────────────────┘   │
└───────────────────────────────────────────┼──────────────────────────┘
                                            │ HTTP (localhost:8080)
┌───────────────────────────────────────────┼──────────────────────────┐
│  Python FastAPI Backend                   ▼                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  /v1/ipfs/* endpoints (handlers/ipfs_integration.py)          │   │
│  └──────────┬──────────────────┬──────────────────┬─────────────┘   │
│             │                  │                  │                   │
│  ┌──────────▼──────┐  ┌───────▼────────┐  ┌─────▼──────────────┐   │
│  │ ipfs_kit_       │  │ ipfs_datasets_ │  │ ipfs_accelerate_   │   │
│  │ adapters.py     │  │ routers.py     │  │ adapters.py        │   │
│  └──────────┬──────┘  └───────┬────────┘  └─────┬──────────────┘   │
└─────────────┼──────────────────┼─────────────────┼───────────────────┘
              │                  │                  │
   ┌──────────▼──────┐  ┌───────▼────────┐  ┌─────▼──────────────┐
   │  ipfs_kit_py    │  │ ipfs_datasets_ │  │ ipfs_accelerate_py │
   │  (v0.2.0)      │  │ py (v0.2.0)    │  │ (v0.4.0)           │
   │                 │  │                │  │                     │
   │ • ipfs_kit class│  │ • llm_router   │  │ • llm_router       │
   │ • P2P workflow  │  │ • embed_router │  │ • embed_router     │
   │ • JIT imports   │  │ • ipfs_backend │  │ • ipfs_accelerate  │
   │ • backend_config│  │   _router      │  │   class            │
   └─────────────────┘  └────────────────┘  └────────────────────┘
```

## API Endpoints

| Endpoint | Method | Description | Backend |
|----------|--------|-------------|---------|
| `/v1/ipfs/status` | GET | Health of all IPFS subsystems | All |
| `/v1/ipfs/add` | POST | Add content to IPFS | datasets → kit |
| `/v1/ipfs/cat` | POST | Retrieve content by CID | datasets → kit |
| `/v1/ipfs/pin` | POST | Pin content | kit |
| `/v1/ipfs/unpin` | POST | Unpin content | kit |
| `/v1/ipfs/resolve` | POST | Resolve CID metadata | kit |
| `/v1/ipfs/embed` | POST | Generate embeddings | datasets / accelerate |
| `/v1/ipfs/generate` | POST | Generate text (LLM) | datasets / accelerate |
| `/v1/ipfs/capabilities` | GET | Hardware capabilities | accelerate |

## Fallback Strategy

Each endpoint tries backends in priority order:
1. **ipfs_datasets_py routers** (lightweight, uses Kubo CLI or HTTP API)
2. **ipfs_kit_py** (full IPFS daemon management, cluster support)
3. Returns 503 if nothing is available

## Electron IPC Bridge

The TypeScript types in `docs/integration/ipfs-ipc-bridge.ts` define the
contract for Electron main-process IPC handlers:

```typescript
import { IPFS_IPC_CHANNELS } from './ipfs-ipc-bridge';

// In main process:
ipcMain.handle(IPFS_IPC_CHANNELS.STATUS, async () => {
  const resp = await fetch('http://localhost:8080/v1/ipfs/status');
  return resp.json();
});

// In renderer:
const status = await ipcRenderer.invoke('ipfs:status');
```

## SwissKnife ORB Integration

The `ipfs_descriptor_pack.py` module registers all IPFS capabilities as
ORB-routable descriptors. The SwissKnife virtual desktop can:

1. Query available IPFS tools via the descriptor pack
2. Route operations through MCP++ transport
3. Display status in the operator console

## Verified Upstream API Shapes

### ipfs_kit_py (endomorphosis/ipfs_kit_py @ main)
- Class: `ipfs_kit_py.ipfs_kit.ipfs_kit.create(role="leecher")`
- Methods: `.ipfs_add(path)`, `.ipfs_cat(cid)`, `.ipfs_pin_add(cid)`, `.ipfs_pin_rm(cid)`
- Config: `ipfs_kit_py.backend_config.get_backend_statuses()`

### ipfs_datasets_py (endomorphosis/ipfs_datasets_py @ main)
- `ipfs_datasets_py.llm_router.generate_text(prompt, *, model_name=None, provider=None)`
- `ipfs_datasets_py.embeddings_router.embed_texts(texts, *, model_name=None)`
- `ipfs_datasets_py.ipfs_backend_router.add_bytes(data, *, pin=True)` → CID str
- `ipfs_datasets_py.ipfs_backend_router.cat(cid)` → bytes

### ipfs_accelerate_py (endomorphosis/ipfs_accelerate_py @ main)
- Class: `ipfs_accelerate_py.ipfs_accelerate.ipfs_accelerate_py(**kwargs)`
- Methods: `.run_model()`, `.infer()`, `.get_capabilities()`, `.call_tool()`
- Router: `ipfs_accelerate_py.llm_router.generate_text(prompt, *)`
- Singleton: `ipfs_accelerate_py.get_instance()`
