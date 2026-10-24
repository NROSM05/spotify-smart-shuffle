import asyncio

from backend.database import SessionLocal
from backend.models import User
from backend.playback_service import get_current_track, process_current_track

from sqlalchemy import select


last_processed_tracks = {}


async def monitor_user_playback(user_id: int):
    while True:
        try:
            await asyncio.to_thread(process_user_playback, user_id)
        except Exception as exc:
            print(f"Playback monitor error for user {user_id}: {exc}")

        await asyncio.sleep(5)


def process_user_playback(user_id: int):
    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None:
            return

        track = get_current_track(user, db)

        if not track or not track["is_playing"]:
            last_processed_tracks.pop(user_id, None)
            return

        playback_key = (
            track["id"],
            track.get("timestamp"),
        )

        if last_processed_tracks.get(user_id) == playback_key:
            return

        result = process_current_track(user, db)

        if result["status"] in ("queued", "already_queued"):
            last_processed_tracks[user_id] = playback_key
            print(f"User {user_id}: {result}")

def get_monitorable_user_ids():
    with SessionLocal() as db:
        statement = select(User.id).where(
            User.access_token_encrypted.is_not(None),
            User.refresh_token_encrypted.is_not(None),
        )
        return list(db.scalars(statement).all())

async def manage_playback_monitors():
    monitor_tasks = {}

    try:
        while True:
            user_ids = await asyncio.to_thread(get_monitorable_user_ids)
            active_user_ids = set(user_ids)

            for user_id in list(monitor_tasks):
                if user_id not in active_user_ids:
                    task = monitor_tasks.pop(user_id)
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    last_processed_tracks.pop(user_id, None)
                    print(f"Stopped playback monitor for user {user_id}")

            for user_id in user_ids:
                if user_id not in monitor_tasks:
                    monitor_tasks[user_id] = asyncio.create_task(
                        monitor_user_playback(user_id)
                    )
                    print(f"Started playback monitor for user {user_id}")

            await asyncio.sleep(10)

    finally:
        for task in monitor_tasks.values():
            task.cancel()

        await asyncio.gather(
            *monitor_tasks.values(),
            return_exceptions=True,
        )