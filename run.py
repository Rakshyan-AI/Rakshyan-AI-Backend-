import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting Rakshan AI Core Backend Server on http://0.0.0.0:{port}")
    print(f"📖 Swagger Interactive API Docs available at http://localhost:{port}/docs")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
