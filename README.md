# 🎧 Spotify Smart Shuffle

A Python-based Spotify playback automation tool that preserves seamless transitions between songs, even when shuffle is enabled.

Built using the **Spotify Web API**, **Spotipy**, and **Docker**, and deployed to **Northflank** for continuous cloud-based operation.

## The Problem

Some songs are designed to flow directly into one another, creating seamless transitions across an album. However, enabling Spotify's shuffle feature can separate these tracks and disrupt the intended listening experience.

Spotify Smart Shuffle solves this by automatically detecting when a configured song is playing and adding its intended successor to the playback queue.

This allows listeners to enjoy shuffled music while preserving their favorite transitions.

## 🎬 Demo

Watch Smart Shuffle automatically detect a song, queue its
transition track, and play the songs seamlessly.

https://github.com/user-attachments/assets/3657e1bf-0436-426a-a498-5e293d1c3307

## Features

- **Automatic playback monitoring** — Checks Spotify playback to detect the currently playing track.
- **Custom song chains** — Configure two or more tracks in a specific order using Spotify track IDs.
- **Automatic queue management** — Adds the next track in a chain to the Spotify playback queue.
- **Duplicate prevention** — Checks the upcoming queue before adding a track.
- **Multi-track transitions** — Supports sequences spanning multiple songs.
- **API error handling** — Handles Spotify API errors, rate limits, and temporary network failures.
- **Playback diagnostics** — Logs detected tracks and periodic playback-status heartbeats.
- **Cloud deployment** — Runs continuously on Northflank without requiring a local computer.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Spotify Web API | Playback monitoring and queue management |
| Spotipy | Python integration with Spotify |
| OAuth 2.0 (PKCE) | Spotify user authorization |
| JSON | Song-chain configuration |
| Docker | Application containerization |
| Northflank | Cloud hosting and deployment |
| GitHub | Version control and source management |

## How It Works

1. The application authenticates with Spotify using OAuth 2.0 PKCE.
2. It loads the configured song chains from `chains.json`.
3. It polls Spotify's playback API approximately every 10 seconds.
4. When a configured track is detected, it identifies the next track in the chain.
5. It checks the playback queue to avoid adding a duplicate.
6. If necessary, it adds the successor track to the Spotify queue.
7. The process continues while the application is running.

### Example

A configured chain might look like:

**Metro Spider → I Can't Save You (Interlude)**

When *Metro Spider* begins playing, the application automatically queues *I Can't Save You (Interlude)*, preserving the intended transition during shuffle playback.

## Project Structure

```text
spotify-smart-shuffle/
├── smart_shuffle.py     # Playback monitoring and queue automation
├── chains.json          # Configurable song transitions
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
├── .gitignore           # Excluded local files
└── README.md            # Project documentation
```

## Configuration

Song transitions are defined in `chains.json`:

```json
{
  "chains": [
    {
      "name": "Metro Spider → I Can't Save You",
      "tracks": [
        "2VtgzixdB967bHDNu5A1nh",
        "2N9LEu6Pf8nDcp3GjWJT1Z"
      ]
    }
  ]
}
```

Each chain contains an ordered list of Spotify track IDs. The application automatically generates the corresponding track-to-track transition rules.

## Authentication and Deployment

The application uses Spotify OAuth 2.0 PKCE for authorization.

- **Local development:** Spotify authorization is handled through a browser-based login flow.
- **Cloud deployment:** The application uses environment variables for its Spotify client ID and refresh token.
- **Hosting:** The application is containerized with Docker and deployed to Northflank.

Authentication tokens and credentials must never be committed to the repository.

### Requirements

- Python 3.10+
- Spotify Premium account
- Spotify Developer application with an appropriate redirect URI
- Dependencies listed in `requirements.txt`

This repository currently represents a personal-use implementation, not a hosted multi-user service. Running a separate instance requires Spotify developer configuration and authorization.

## Current Limitations

- Playback detection relies on periodic API polling.
- Spotify API responses and queue behavior can occasionally affect transition reliability.
- The application currently supports one authorized Spotify account per running instance.
- Song chains are configured manually through JSON rather than a graphical interface.

## Future Improvements

- Web-based interface for creating and managing song chains.
- Multi-user support with individual Spotify authorization.
- Improved playback synchronization and queue verification.
- More detailed monitoring and diagnostics.

Any public or commercial deployment would require compliance with Spotify's developer policies and applicable access restrictions.

## Project Status

**Functional personal-use prototype — deployed and tested.**

The application is actively used with custom song chains, automatic cloud execution, and playback diagnostics.

---

*An independent personal project, not affiliated with or endorsed by Spotify.*
