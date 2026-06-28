"""IPFS integration API router.

Exposes ipfs_kit_py, ipfs_datasets_py, and ipfs_accelerate_py capabilities
as HTTP endpoints for the Electron frontend (Hallucinate App) and SwissKnife
virtual desktop.

Endpoints:
    GET  /v1/ipfs/status          - Health/availability of all IPFS adapters
    POST /v1/ipfs/add             - Add bytes/content to IPFS
    POST /v1/ipfs/cat             - Retrieve content by CID
    POST /v1/ipfs/pin             - Pin content by CID
    POST /v1/ipfs/unpin           - Unpin content by CID
    POST /v1/ipfs/resolve         - Resolve CID metadata
    POST /v1/ipfs/embed           - Generate embeddings via ipfs_datasets/accelerate
    POST /v1/ipfs/generate        - Generate text via LLM router
    GET  /v1/ipfs/capabilities    - List accelerate hardware capabilities
    GET  /v1/ipfs/hardware_profile - Detailed hardware profile
    GET  /v1/ipfs/list_models     - List available models
    POST /v1/ipfs/list_datasets   - List/search datasets
    POST /v1/ipfs/inference       - Direct model inference
    GET  /v1/ipfs/list_pins       - List pinned CIDs
    POST /v1/ipfs/stat            - Object statistics for CID
    POST /v1/ipfs/dag/get         - Get DAG node by CID
    POST /v1/ipfs/dag/put         - Store DAG node
    POST /v1/ipfs/name/publish    - Publish CID to IPNS
    POST /v1/ipfs/name/resolve    - Resolve IPNS name
    POST /v1/ipfs/search_models   - Search available AI models
    GET  /v1/ipfs/metrics         - Performance metrics
    GET  /v1/ipfs/endpoints       - List inference endpoints
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from handsfree.ipfs_accelerate_adapters import (
    IPFSAccelerateUnavailableError,
    get_ipfs_accelerate_adapter,
)
from handsfree.ipfs_datasets_routers import (
    IPFSDatasetsRouterUnavailableError,
    get_embeddings_router,
    get_ipfs_router,
    get_llm_router,
)
from handsfree.ipfs_kit_adapters import (
    IPFSKitUnavailableError,
    get_ipfs_kit_adapter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ipfs", tags=["ipfs"])


# --------------------------------------------------------------------------- #
# Request/Response models
# --------------------------------------------------------------------------- #


class IPFSStatusResponse(BaseModel):
    """Aggregated health status of all IPFS subsystems."""

    ipfs_kit: dict[str, Any] = Field(default_factory=dict)
    ipfs_datasets: dict[str, Any] = Field(default_factory=dict)
    ipfs_accelerate: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class IPFSAddRequest(BaseModel):
    """Request to add content to IPFS."""

    data_base64: str = Field(..., description="Base64-encoded content to store")
    pin: bool = Field(default=True, description="Whether to pin the content")


class IPFSAddResponse(BaseModel):
    """Response from IPFS add operation."""

    cid: str | None = Field(default=None, description="Content identifier")
    raw_result: Any = Field(default=None, description="Full result from backend")


class IPFSCatRequest(BaseModel):
    """Request to retrieve content by CID."""

    cid: str = Field(..., description="IPFS content identifier")


class IPFSCatResponse(BaseModel):
    """Response with retrieved content."""

    data_base64: str | None = Field(default=None, description="Base64-encoded content")
    size: int = Field(default=0)


class IPFSPinRequest(BaseModel):
    """Request to pin/unpin content."""

    cid: str = Field(..., description="IPFS content identifier")


class IPFSResolveRequest(BaseModel):
    """Request to resolve CID metadata."""

    cid: str = Field(..., description="IPFS content identifier")


class IPFSEmbedRequest(BaseModel):
    """Request to generate embeddings."""

    texts: list[str] = Field(..., description="Texts to embed")
    model_name: str | None = Field(default=None, description="Optional model name")
    provider: str | None = Field(
        default=None,
        description="Provider: 'datasets' (ipfs_datasets_py) or 'accelerate' (ipfs_accelerate_py)",
    )


class IPFSEmbedResponse(BaseModel):
    """Embedding vectors response."""

    embeddings: list[list[float]] = Field(default_factory=list)
    provider_used: str = Field(default="unknown")


class IPFSGenerateRequest(BaseModel):
    """Request to generate text via LLM router."""

    prompt: str = Field(..., description="Input prompt")
    model_name: str | None = Field(default=None)
    provider: str | None = Field(
        default=None,
        description="Provider: 'datasets' or 'accelerate'",
    )


class IPFSGenerateResponse(BaseModel):
    """Generated text response."""

    text: str = Field(default="")
    provider_used: str = Field(default="unknown")


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@router.get("/status", response_model=IPFSStatusResponse)
async def ipfs_status_endpoint() -> IPFSStatusResponse:
    """Return health/availability of all IPFS adapters."""
    kit_status: dict[str, Any] = {"available": False}
    datasets_status: dict[str, Any] = {"available": False}
    accelerate_status: dict[str, Any] = {"available": False}

    # ipfs_kit_py
    try:
        kit_adapter = get_ipfs_kit_adapter()
        kit_status["available"] = not isinstance(
            kit_adapter,
            type(None),  # never matches, but catches unavailable adapter below
        )
        # Check if it's the unavailable stub
        kit_status["available"] = hasattr(kit_adapter, "get_backend_statuses")
        backend_statuses = kit_adapter.get_backend_statuses()
        kit_status["backends"] = backend_statuses
        if not backend_statuses:
            # Still available via adapter, just no backends configured
            kit_status["available"] = True
            kit_status["note"] = "adapter loaded, backends may need configuration"
    except IPFSKitUnavailableError:
        kit_status["available"] = False
        kit_status["error"] = "ipfs_kit_py not installed"
    except Exception as exc:
        kit_status["available"] = False
        kit_status["error"] = str(exc)

    # ipfs_datasets_py routers
    try:
        embeddings = get_embeddings_router()
        ipfs_router = get_ipfs_router()
        llm = get_llm_router()
        datasets_status["available"] = True
        datasets_status["routers"] = {
            "embeddings": type(embeddings).__name__,
            "ipfs": type(ipfs_router).__name__,
            "llm": type(llm).__name__,
        }
    except Exception as exc:
        datasets_status["error"] = str(exc)

    # ipfs_accelerate_py
    try:
        accel = get_ipfs_accelerate_adapter()
        accelerate_status = accel.status()
    except Exception as exc:
        accelerate_status["error"] = str(exc)

    return IPFSStatusResponse(
        ipfs_kit=kit_status,
        ipfs_datasets=datasets_status,
        ipfs_accelerate=accelerate_status,
        timestamp=time.time(),
    )


@router.post("/add", response_model=IPFSAddResponse)
async def ipfs_add_endpoint(req: IPFSAddRequest) -> IPFSAddResponse:
    """Add content to IPFS via ipfs_kit or ipfs_datasets backend router."""
    data = base64.b64decode(req.data_base64)

    # Try ipfs_datasets_py.ipfs_backend_router first (lighter weight)
    try:
        ipfs_be = get_ipfs_router()
        cid = ipfs_be.add_bytes(data, pin=req.pin)
        return IPFSAddResponse(cid=str(cid) if cid else None, raw_result=cid)
    except IPFSDatasetsRouterUnavailableError:
        pass
    except Exception as exc:
        logger.debug("ipfs_datasets_py add_bytes failed, trying ipfs_kit: %s", exc)

    # Fallback to ipfs_kit_py
    try:
        kit = get_ipfs_kit_adapter()
        result = kit.add_bytes(data)
        # ipfs_kit returns dict with Hash/Name or just a CID string
        if isinstance(result, dict):
            cid = result.get("Hash") or result.get("cid") or result.get("Name")
        else:
            cid = str(result) if result else None
        return IPFSAddResponse(cid=cid, raw_result=result)
    except IPFSKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No IPFS backend available: {exc}",
        ) from exc


@router.post("/cat", response_model=IPFSCatResponse)
async def ipfs_cat_endpoint(req: IPFSCatRequest) -> IPFSCatResponse:
    """Retrieve content by CID."""
    # Try ipfs_datasets_py first
    try:
        ipfs_be = get_ipfs_router()
        content = ipfs_be.cat(req.cid)
        if isinstance(content, bytes):
            return IPFSCatResponse(
                data_base64=base64.b64encode(content).decode("ascii"),
                size=len(content),
            )
        elif isinstance(content, str):
            encoded = content.encode("utf-8")
            return IPFSCatResponse(
                data_base64=base64.b64encode(encoded).decode("ascii"),
                size=len(encoded),
            )
    except IPFSDatasetsRouterUnavailableError:
        pass
    except Exception as exc:
        logger.debug("ipfs_datasets_py cat failed, trying ipfs_kit: %s", exc)

    # Fallback to ipfs_kit_py
    try:
        kit = get_ipfs_kit_adapter()
        content = kit.cat(req.cid)
        if isinstance(content, bytes):
            return IPFSCatResponse(
                data_base64=base64.b64encode(content).decode("ascii"),
                size=len(content),
            )
        elif isinstance(content, str):
            encoded = content.encode("utf-8")
            return IPFSCatResponse(
                data_base64=base64.b64encode(encoded).decode("ascii"),
                size=len(encoded),
            )
        return IPFSCatResponse(data_base64=None, size=0)
    except IPFSKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No IPFS backend available: {exc}",
        ) from exc


@router.post("/pin")
async def ipfs_pin_endpoint(req: IPFSPinRequest) -> dict[str, Any]:
    """Pin content by CID."""
    try:
        ipfs_be = get_ipfs_router()
        ipfs_be.add_bytes(b"")  # test availability
    except Exception:
        pass

    try:
        kit = get_ipfs_kit_adapter()
        result = kit.pin(req.cid)
        return {"ok": True, "cid": req.cid, "result": result}
    except IPFSKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/unpin")
async def ipfs_unpin_endpoint(req: IPFSPinRequest) -> dict[str, Any]:
    """Unpin content by CID."""
    try:
        kit = get_ipfs_kit_adapter()
        result = kit.unpin(req.cid)
        return {"ok": True, "cid": req.cid, "result": result}
    except IPFSKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/resolve")
async def ipfs_resolve_endpoint(req: IPFSResolveRequest) -> dict[str, Any]:
    """Resolve CID metadata."""
    try:
        kit = get_ipfs_kit_adapter()
        result = kit.resolve(req.cid)
        return {"ok": True, "cid": req.cid, "result": result}
    except IPFSKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/embed", response_model=IPFSEmbedResponse)
async def ipfs_embed_endpoint(req: IPFSEmbedRequest) -> IPFSEmbedResponse:
    """Generate embeddings via ipfs_datasets or ipfs_accelerate routers."""
    provider_used = req.provider or "datasets"

    if provider_used == "accelerate":
        try:
            accel = get_ipfs_accelerate_adapter()
            vectors = accel.embed(req.texts, model_name=req.model_name)
            return IPFSEmbedResponse(embeddings=vectors, provider_used="accelerate")
        except IPFSAccelerateUnavailableError:
            # Fall through to datasets
            provider_used = "datasets"

    try:
        embeddings_router = get_embeddings_router()
        vectors = embeddings_router.embed_texts(req.texts, model_name=req.model_name)
        return IPFSEmbedResponse(embeddings=vectors, provider_used="datasets")
    except IPFSDatasetsRouterUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No embeddings provider available: {exc}",
        ) from exc


@router.post("/generate", response_model=IPFSGenerateResponse)
async def ipfs_generate_endpoint(req: IPFSGenerateRequest) -> IPFSGenerateResponse:
    """Generate text via LLM router (ipfs_datasets or ipfs_accelerate)."""
    provider_used = req.provider or "datasets"

    if provider_used == "accelerate":
        try:
            accel = get_ipfs_accelerate_adapter()
            text = accel.generate(req.prompt, model_name=req.model_name)
            return IPFSGenerateResponse(text=str(text), provider_used="accelerate")
        except IPFSAccelerateUnavailableError:
            provider_used = "datasets"

    try:
        llm = get_llm_router()
        text = llm.generate_text(req.prompt, model_name=req.model_name)
        return IPFSGenerateResponse(text=str(text), provider_used="datasets")
    except IPFSDatasetsRouterUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No LLM provider available: {exc}",
        ) from exc


@router.get("/capabilities")
async def ipfs_capabilities_endpoint() -> dict[str, Any]:
    """List accelerate hardware/model capabilities."""
    try:
        accel = get_ipfs_accelerate_adapter()
        caps = accel.get_capabilities(detail=True)
        return {"ok": True, "capabilities": caps}
    except IPFSAccelerateUnavailableError as exc:
        return {"ok": False, "capabilities": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "capabilities": None, "error": str(exc)}


# --------------------------------------------------------------------------- #
# Extended endpoints: hardware_profile, list_models, list_datasets, inference
# --------------------------------------------------------------------------- #


class IPFSInferenceRequest(BaseModel):
    """Request to run model inference via ipfs_accelerate."""

    model_name: str = Field(..., description="Model to run inference with")
    inputs: Any = Field(..., description="Model inputs (text, dict, or list)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Extra params")


class IPFSListDatasetsRequest(BaseModel):
    """Request to list/search available datasets."""

    query: str | None = Field(default=None, description="Search query")
    limit: int = Field(default=20, description="Max results")


@router.get("/hardware_profile")
async def ipfs_hardware_profile_endpoint() -> dict[str, Any]:
    """Return detailed hardware profile from ipfs_accelerate."""
    try:
        accel = get_ipfs_accelerate_adapter()
        caps = accel.get_capabilities(detail=True)
        # Extract hardware-specific info
        profile = {
            "ok": True,
            "gpu": caps.get("gpu") or caps.get("device"),
            "vram": caps.get("vram") or caps.get("memory"),
            "backends": caps.get("backends") or caps.get("supported_backends") or [],
            "quantization_formats": caps.get("quantization_formats") or [],
            "compute_capability": caps.get("compute_capability"),
            "cpu_count": caps.get("cpu_count"),
            "platform": caps.get("platform"),
            "raw": caps,
        }
        return profile
    except IPFSAccelerateUnavailableError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/list_models")
async def ipfs_list_models_endpoint() -> dict[str, Any]:
    """List available models from ipfs_accelerate backend."""
    try:
        accel = get_ipfs_accelerate_adapter()
        # Try various methods the adapter might expose
        if hasattr(accel, "list_models"):
            models = accel.list_models()
        elif hasattr(accel, "get_capabilities"):
            caps = accel.get_capabilities(detail=True)
            models = caps.get("models") or caps.get("loaded_models") or []
        else:
            models = []
        return {"ok": True, "models": models}
    except IPFSAccelerateUnavailableError as exc:
        return {"ok": False, "models": [], "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "models": [], "error": str(exc)}


@router.post("/list_datasets")
async def ipfs_list_datasets_endpoint(
    req: IPFSListDatasetsRequest,
) -> dict[str, Any]:
    """List/search available datasets from ipfs_datasets backend."""
    try:
        ipfs_be = get_ipfs_router()
        # Try to get dataset list from the backend
        if hasattr(ipfs_be, "list_datasets"):
            datasets = ipfs_be.list_datasets(query=req.query, limit=req.limit)
        elif hasattr(ipfs_be, "search"):
            datasets = ipfs_be.search(req.query or "", limit=req.limit)
        else:
            # Minimal fallback: report that backend is available but listing not supported
            datasets = []
        return {"ok": True, "datasets": datasets, "query": req.query}
    except IPFSDatasetsRouterUnavailableError as exc:
        return {"ok": False, "datasets": [], "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "datasets": [], "error": str(exc)}


@router.post("/inference")
async def ipfs_inference_endpoint(req: IPFSInferenceRequest) -> dict[str, Any]:
    """Run inference via ipfs_accelerate (direct model execution)."""
    try:
        accel = get_ipfs_accelerate_adapter()
        result = accel.run_model(req.model_name, req.inputs, **req.parameters)
        return {"ok": True, "model": req.model_name, "result": result}
    except IPFSAccelerateUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Accelerate backend unavailable: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failed: {exc}",
        ) from exc


# --------------------------------------------------------------------------- #
# Extended endpoints: DAG, name, pins, search_models, metrics
# --------------------------------------------------------------------------- #


class IPFSDAGRequest(BaseModel):
    """Request for DAG operations."""

    cid: str = Field(..., description="CID for DAG get")


class IPFSDAGPutRequest(BaseModel):
    """Request to put a DAG node."""

    data: Any = Field(..., description="DAG node data (dict/JSON)")


class IPFSNameRequest(BaseModel):
    """Request for IPNS name operations."""

    value: str = Field(..., description="CID to publish or name to resolve")


class IPFSSearchModelsRequest(BaseModel):
    """Request to search available models."""

    query: str = Field(default="", description="Search query")


@router.get("/list_pins")
async def ipfs_list_pins_endpoint() -> dict[str, Any]:
    """List all pinned CIDs."""
    try:
        kit = get_ipfs_kit_adapter()
        pins = kit.list_pins()
        return {"ok": True, "pins": pins}
    except IPFSKitUnavailableError as exc:
        return {"ok": False, "pins": [], "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "pins": [], "error": str(exc)}


@router.post("/stat")
async def ipfs_stat_endpoint(req: IPFSDAGRequest) -> dict[str, Any]:
    """Get object statistics for a CID."""
    try:
        kit = get_ipfs_kit_adapter()
        stat = kit.stat(req.cid)
        return {"ok": True, "cid": req.cid, "stat": stat}
    except IPFSKitUnavailableError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/dag/get")
async def ipfs_dag_get_endpoint(req: IPFSDAGRequest) -> dict[str, Any]:
    """Get a DAG node by CID."""
    try:
        kit = get_ipfs_kit_adapter()
        dag = kit.dag_get(req.cid)
        return {"ok": True, "cid": req.cid, "dag": dag}
    except IPFSKitUnavailableError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/dag/put")
async def ipfs_dag_put_endpoint(req: IPFSDAGPutRequest) -> dict[str, Any]:
    """Store a DAG node, return CID."""
    try:
        kit = get_ipfs_kit_adapter()
        result = kit.dag_put(req.data)
        return {"ok": True, "result": result}
    except IPFSKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/name/publish")
async def ipfs_name_publish_endpoint(req: IPFSNameRequest) -> dict[str, Any]:
    """Publish a CID to IPNS."""
    try:
        kit = get_ipfs_kit_adapter()
        result = kit.name_publish(req.value)
        return {"ok": True, "result": result}
    except IPFSKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/name/resolve")
async def ipfs_name_resolve_endpoint(req: IPFSNameRequest) -> dict[str, Any]:
    """Resolve an IPNS name to a CID."""
    try:
        kit = get_ipfs_kit_adapter()
        result = kit.name_resolve(req.value)
        return {"ok": True, "result": result}
    except IPFSKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/search_models")
async def ipfs_search_models_endpoint(req: IPFSSearchModelsRequest) -> dict[str, Any]:
    """Search available AI models via accelerate backend."""
    try:
        accel = get_ipfs_accelerate_adapter()
        results = accel.search_models(req.query)
        return {"ok": True, "results": results}
    except IPFSAccelerateUnavailableError as exc:
        return {"ok": False, "results": [], "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "results": [], "error": str(exc)}


@router.get("/metrics")
async def ipfs_metrics_endpoint() -> dict[str, Any]:
    """Get performance metrics from accelerate backend."""
    try:
        accel = get_ipfs_accelerate_adapter()
        metrics = accel.get_performance_metrics()
        return {"ok": True, "metrics": metrics}
    except IPFSAccelerateUnavailableError as exc:
        return {"ok": False, "metrics": {}, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "metrics": {}, "error": str(exc)}


@router.get("/endpoints")
async def ipfs_endpoints_endpoint() -> dict[str, Any]:
    """List configured inference endpoints."""
    try:
        accel = get_ipfs_accelerate_adapter()
        endpoints = accel.get_endpoints()
        return {"ok": True, "endpoints": endpoints}
    except IPFSAccelerateUnavailableError as exc:
        return {"ok": False, "endpoints": [], "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "endpoints": [], "error": str(exc)}
