import os

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyPKCE

load_dotenv()

SPOTIFY_SCOPES = (
    "user-read-currently-playing "
    "user-read-playback-state "
    "user-modify-playback-state"
)


def create_spotify_auth(redirect_uri: str):
    return SpotifyPKCE(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        redirect_uri=redirect_uri,
        scope=SPOTIFY_SCOPES,
        open_browser=False,
    )

def get_spotify_user(access_token: str):
    spotify = spotipy.Spotify(auth=access_token)
    return spotify.current_user()