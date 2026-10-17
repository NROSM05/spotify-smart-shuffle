import json
from pathlib import Path
import time
import spotipy
from spotipy.oauth2 import SpotifyPKCE
from spotipy.exceptions import SpotifyException

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

spotify = spotipy.Spotify(
    auth_manager=SpotifyPKCE(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=(
            "user-read-currently-playing "
            "user-read-playback-state "
            "user-modify-playback-state"
        ),
        open_browser=True
    )
)

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

                        spotify.add_to_queue(
                            f"spotify:track:{next_song}"
                        )

                        queued_for_current_song = True

                        print(
                            f"Queued next song after {song_name}!",
                            flush=True
                        )

            else:
                last_seen_song = None
                queued_for_current_song = False

            time.sleep(10)

        except SpotifyException as error:
            print(f"Spotify error: {error}", flush=True)
            time.sleep(30)

except KeyboardInterrupt:
    print("\nSmart Shuffle stopped.")
