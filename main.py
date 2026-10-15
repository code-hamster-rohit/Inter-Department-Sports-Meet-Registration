import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from routes.auth import router as auth_router
from routes.teams import router as teams_router

load_dotenv()

app = FastAPI(
    title="Inter-Dept Sports Meet API",
    description="API for Inter-Dept Sports Meet",
    version="1.0.0",
    contact={
        "name": "Parth",
        "email": "[EMAIL_ADDRESS]",
    },
)

# Session middleware for cookie-based authentication
SECRET_KEY = os.getenv("SECRET_KEY", "sports-meet-iitr-secure-session-key-2026")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=86400 * 7)

# Mount static assets using absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(teams_router)


@app.get("/")
async def root(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/register", status_code=303)
    return RedirectResponse(url="/login", status_code=303)