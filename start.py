"""Start the AI Company Factory web server.

Usage:
    python start.py
"""
import uvicorn

if __name__ == "__main__":
    print("AI Company Factory")
    print("Pixel Dashboard -> http://localhost:8000")
    print("API docs        -> http://localhost:8000/docs")
    print("Press Ctrl+C to stop")
    print()
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
