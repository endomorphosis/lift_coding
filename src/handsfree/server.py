#!/usr/bin/env python3
"""Run the development server."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "handsfree.api:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )
