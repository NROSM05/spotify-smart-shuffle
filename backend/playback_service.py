import spotipy

from backend.spotify_service import get_valid_spotify_token
import json
from sqlalchemy import select
from backend.models import Chain


def get_spotify_client(user, db):
    access_token = get_valid_spotify_token(user, db)
    return spotipy.Spotify(auth=access_token)

def get_current_track(user, db):
    spotify = get_spotify_client(user, db)
    playback = spotify.current_playback()

    if not playback or not playback.get("item"):
        return None

    track = playback["item"]

    return {
        "id": track["id"],
        "name": track["name"],
        "artist": ", ".join(
            artist["name"] for artist in track["artists"]
        ),
        "is_playing": playback["is_playing"],
        "progress_ms": playback["progress_ms"],
        "duration_ms": track["duration_ms"],
    }

def queue_track(user, db, track_id: str):
    spotify = get_spotify_client(user, db)

    spotify.add_to_queue(
        f"spotify:track:{track_id}"
    )

    return {"queued": True, "track_id": track_id}

def find_matching_chain(user_id: int, track_id: str, db):
    chains = db.scalars(
        select(Chain).where(Chain.user_id == user_id)
    ).all()

    for chain in chains:
        tracks = json.loads(chain.tracks_json)

        for index, song_id in enumerate(tracks[:-1]):
            if song_id == track_id:
                return {
                    "chain_id": chain.id,
                    "chain_name": chain.name,
                    "next_track_id": tracks[index + 1],
                }

    return None

def process_current_track(user, db):
    track = get_current_track(user, db)

    if not track or not track["is_playing"]:
        return {"status": "not_playing"}

    match = find_matching_chain(user.id, track["id"], db)

    if not match:
        return {"status": "no_match"}

    spotify = get_spotify_client(user, db)
    queue = spotify.queue()

    queued_track_ids = {
        item["id"]
        for item in queue.get("queue", [])
        if item and item.get("id")
    }

    if match["next_track_id"] in queued_track_ids:
        return {
            "status": "already_queued",
            "next_track_id": match["next_track_id"],
        }

    result = queue_track(user, db, match["next_track_id"])

    return {
        "status": "queued",
        "current_track": track["name"],
        "chain_name": match["chain_name"],
        "next_track_id": result["track_id"],
    }