from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.settings import ensure_directories, settings
from app.db.session import init_db

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    ensure_directories()
    init_db()


app.include_router(router)
app.mount("/outputs", StaticFiles(directory=settings.outputs_dir), name="outputs")
app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")


@app.get("/")
def health():
    return {"ok": True, "service": settings.app_name}
