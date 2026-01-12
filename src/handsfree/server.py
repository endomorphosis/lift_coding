"""Server entry point for HandsFree Dev Companion API."""

import uvicorn


def main():
    """Run the FastAPI server."""
    uvicorn.run(
        "handsfree.api:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
