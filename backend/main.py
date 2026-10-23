import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.spotify_service import create_spotify_auth

app = FastAPI(
    title="Smart Shuffle API",
    description="Backend API for Smart Shuffle 2.0",
    version="2.0.0",
)

load_dotenv()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SESSION_SECRET_KEY"],
    same_site="lax",
    https_only=False,  # Local development only
)

REDIRECT_URI = "http://127.0.0.1:8001/auth/callback"


@app.get("/")
def home():
    return {
        "message": "Smart Shuffle API is running!",
        "version": "2.0.0",
    }


@app.get("/auth/login")
def spotify_login(request: Request):
    auth = create_spotify_auth(REDIRECT_URI)

    state = secrets.token_urlsafe(32)

    authorization_url = auth.get_authorize_url(state=state)

    # Save the verifier AFTER generating the authorization URL.
    request.session["spotify_oauth_state"] = state
    request.session["spotify_code_verifier"] = auth.code_verifier
    request.session["spotify_code_challenge"] = auth.code_challenge

    return RedirectResponse(url=authorization_url)

@app.get("/auth/callback")
def spotify_callback(request: Request, code: str = None, state: str = None):
    expected_state = request.session.pop("spotify_oauth_state", None)

    if not expected_state or not state or not secrets.compare_digest(
        expected_state, state
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state",
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Missing Spotify authorization code",
        )

    code_verifier = request.session.pop("spotify_code_verifier", None)
    code_challenge = request.session.pop("spotify_code_challenge", None)

    if not code_verifier or not code_challenge:
        raise HTTPException(
            status_code=400,
            detail="Missing PKCE handshake parameters",
        )

    auth = create_spotify_auth(REDIRECT_URI)

    auth.code_verifier = code_verifier
    auth.code_challenge = code_challenge

    token_info = auth.get_access_token(code, check_cache=False)

    # Temporary local test only.
    # Never return access tokens to the browser.
    request.session["spotify_connected"] = True

    return {
        "message": "Spotify connected successfully!",
        "connected": True,
    }