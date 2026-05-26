import os
import uvicorn
from backend.main import app

# Render sets the PORT environment variable dynamically
port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
