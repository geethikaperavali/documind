import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.services.surveillance_scheduler import run_surveillance_worker
from backend.routers import (
    auth_router,
    documents_router,
    chat_router,
    dashboard_router,
    profile_router,
    research_router,
    compare_router,
    explorer_router,
    action_router,
    monitor_router,
    temporal_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(run_surveillance_worker())
    try:
        yield
    finally:
        worker_task.cancel()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="DocuMind - Secure AI-Powered Document Intelligence Platform Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router.router, prefix=settings.API_V1_STR)
app.include_router(documents_router.router, prefix=settings.API_V1_STR)
app.include_router(chat_router.router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router.router, prefix=settings.API_V1_STR)
app.include_router(profile_router.router, prefix=settings.API_V1_STR)
app.include_router(research_router.router, prefix=settings.API_V1_STR)
app.include_router(compare_router.router, prefix=settings.API_V1_STR)
app.include_router(explorer_router.router, prefix=settings.API_V1_STR)
app.include_router(action_router.router, prefix=settings.API_V1_STR)
app.include_router(monitor_router.router, prefix=settings.API_V1_STR)
app.include_router(temporal_router.router, prefix=settings.API_V1_STR)

@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    System health check returning status of environment configurations.
    """
    has_supabase = bool(settings.SUPABASE_URL and (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY))
    has_gemini = bool(settings.GEMINI_API_KEY)
    
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "supabase_configured": has_supabase,
        "gemini_configured": has_gemini,
        "embedding_model": settings.EMBEDDING_MODEL,
        "gemini_model": settings.GEMINI_MODEL
    }

# Mount Frontend static files for unified single-server deployment
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{page}.html")
    async def serve_page(page: str):
        page_file = FRONTEND_DIR / f"{page}.html"
        if page_file.exists():
            return FileResponse(page_file)
        return JSONResponse(status_code=404, content={"detail": "Page not found"})

# Global exception handler for uncaught exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[DocuMind Error] Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
