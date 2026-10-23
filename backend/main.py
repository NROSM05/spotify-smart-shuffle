
import json
import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from backend.database import get_db
from backend.models import Chain, User
from backend.spotify_service import create_spotify_auth, get_spotify_user


load_dotenv()

app = FastAPI(
    title="Smart Shuffle API",
    description="Backend API for Smart Shuffle 2.0",
    version="2.0.0",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SESSION_SECRET_KEY"],
    same_site="lax",
    https_only=False,  # Local development only
)

REDIRECT_URI = "http://127.0.0.1:8001/auth/callback"


def get_current_user_id(request: Request) -> int:
    user_id = request.session.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in with Spotify.",
        )

    return int(user_id)


class ChainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    tracks: list[str] = Field(min_length=2)


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

    request.session["spotify_oauth_state"] = state
    request.session["spotify_code_verifier"] = auth.code_verifier
    request.session["spotify_code_challenge"] = auth.code_challenge

    return RedirectResponse(url=authorization_url)


@app.get("/auth/callback")
def spotify_callback(
    request: Request,
    code: str = None,
    state: str = None,
    db: Session = Depends(get_db),
):
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

    access_token = auth.get_access_token(code, check_cache=False)
    spotify_user = get_spotify_user(access_token)

    user = db.scalar(
        select(User).where(User.spotify_id == spotify_user["id"])
    )

    if user is None:
        user = User(
            spotify_id=spotify_user["id"],
            display_name=spotify_user.get("display_name"),
        )
        db.add(user)
    else:
        user.display_name = spotify_user.get("display_name")

    db.commit()
    db.refresh(user)

    request.session.clear()
    request.session["user_id"] = user.id

    return {
        "message": "Spotify connected successfully!",
        "connected": True,
        "user": {
            "id": spotify_user["id"],
            "display_name": spotify_user.get("display_name"),
        },
    }


@app.get("/users/{user_id}/chains")
def get_user_chains(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another user's chains.",
        )

    chains = db.scalars(
        select(Chain).where(Chain.user_id == user_id)
    ).all()

    return [
        {
            "id": chain.id,
            "name": chain.name,
            "tracks": json.loads(chain.tracks_json),
        }
        for chain in chains
    ]


@app.post("/users/{user_id}/chains", status_code=201)
def create_chain(
    user_id: int,
    chain_data: ChainCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another user's chains.",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    chain = Chain(
        user_id=user_id,
        name=chain_data.name,
        tracks_json=json.dumps(chain_data.tracks),
    )

    db.add(chain)
    db.commit()
    db.refresh(chain)

    return {
        "id": chain.id,
        "name": chain.name,
        "tracks": chain_data.tracks,
    }


@app.delete("/users/{user_id}/chains/{chain_id}")
def delete_chain(
    user_id: int,
    chain_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another user's chains.",
        )

    chain = db.scalar(
        select(Chain).where(
            Chain.id == chain_id,
            Chain.user_id == user_id,
        )
    )

    if chain is None:
        raise HTTPException(
            status_code=404,
            detail="Chain not found",
        )

    db.delete(chain)
    db.commit()

    return {"message": "Chain deleted successfully!"}
