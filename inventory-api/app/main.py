from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes import inventory, replenishment

app = FastAPI(title="Pharmacy Inventory Replenishment API")

# Serve frontend static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register route handlers
app.include_router(inventory.router)
app.include_router(replenishment.router)

@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "inventory-api"}
