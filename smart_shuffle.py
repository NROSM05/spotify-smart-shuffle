import os
import json
from pathlib import Path
import time
import spotipy
from spotipy.oauth2 import SpotifyPKCE
from spotipy.exceptions import SpotifyException
import requests

CLIENT_ID = "7400bdea10c4483f8dde1151413675af"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

config_path = Path(__file__).with_name("chains.json")

with open(config_path, "r", encoding="utf-8") as file:
    config = json.load(file)

SONG_CHAINS = [chain["tracks"] for chain in config["chains"]]

# Build song-to-next-song rules automatically.
SONG_PAIRS = {}
for chain in SONG_CHAINS:
    for current_song, next_song in zip(chain, chain[1:]):
        SONG_PAIRS[current_song] = next_song

from spotipy.cache_handler import CacheHandler

class CloudTokenCache(CacheHandler):
    def __init__(self):
        self.token_info = {
            "refresh_token": os.environ["SPOTIFY_REFRESH_TOKEN"],
            "access_token": "",
            "expires_at": 0,
            "token_type": "Bearer",
            "scope": (
                "user-read-currently-playing "
                "user-read-playback-state "
                "user-modify-playback-state"
            ),
        }

    def get_cached_token(self):
        return self.token_info

    def save_token_to_cache(self, token_info):
        self.token_info = token_info


scope = (
    "user-read-currently-playing "
    "user-read-playback-state "
    "user-modify-playback-state"
)

cloud_mode = bool(os.getenv("SPOTIFY_REFRESH_TOKEN"))

if cloud_mode:
    auth_manager = SpotifyPKCE(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        redirect_uri=REDIRECT_URI,
        scope=scope,
        cache_handler=CloudTokenCache(),
        open_browser=False,
    )
else:
    auth_manager = SpotifyPKCE(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=scope,
        open_browser=True,
    )

spotify = spotipy.Spotify(auth_manager=auth_manager)

last_seen_song = None
queued_for_current_song = False

print("Smart Shuffle is running!", flush=True)

try:
    while True:
        try:
            playback = spotify.current_playback()

            if playback and playback.get("is_playing"):
                song = playback.get("item")

                if song and song.get("type") == "track":
                    song_id = song["id"]
                    song_name = song["name"]

                    if song_id != last_seen_song:
                        print(f"Now playing: {song_name}", flush=True)
                        last_seen_song = song_id
                        queued_for_current_song = False

                    if (
                        song_id in SONG_PAIRS
                        and not queued_for_current_song
                    ):
                        next_song = SONG_PAIRS[song_id]

                        # Check Spotify's queue before adding the next track.
                        queue_data = spotify.queue()
                        upcoming = queue_data.get("queue", [])

                        already_queued = bool(
                            upcoming and upcoming[0].get("id") == next_song
                        )

                        if already_queued:
                            print(
                                f"{song_name}: Next song already queued. Skipping!",
                                flush=True
                            )           
                        else:
                            spotify.add_to_queue(
                                f"spotify:track:{next_song}"
                            )

                            print(
                                f"Queued next song after {song_name}!",
                                flush=True
                            )

                        queued_for_current_song = True

            else:
                last_seen_song = None
                queued_for_current_song = False

            time.sleep(10)

        except SpotifyException as error:
            if error.http_status == 429:
                retry_after = (
                    error.headers.get("Retry-After", 30)
                    if error.headers else 30
                )

                try:
                    wait_seconds = max(1, int(retry_after))
                except (ValueError, TypeError):
                    wait_seconds = 30

                print(
                    f"Spotify rate limit reached. Waiting {wait_seconds} seconds.",
                    flush=True
                )
                time.sleep(wait_seconds)
            else:
                print(f"Spotify API error: {error}", flush=True)
                time.sleep(30)

        except requests.exceptions.RequestException as error:
            print(f"Network error: {error}", flush=True)
            time.sleep(30)

except KeyboardInterrupt:
    print("\nSmart Shuffle stopped.")