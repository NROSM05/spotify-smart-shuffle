import asyncio

from backend.database import SessionLocal
from backend.models import User
from backend.playback_service import get_current_track, process_current_track

from sqlalchemy import select


last_seen_progress = {}
last_seen_track_ids = {}


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

        if track and track["is_playing"]:
            previous_progress = last_seen_progress.get(user_id)
            current_progress = track["progress_ms"]

            previous_track_id = last_seen_track_ids.get(user_id)
            current_track_id = track["id"]

            track_changed = previous_track_id != current_track_id

            last_seen_track_ids[user_id] = current_track_id

            playback_restarted = (
                not track_changed
                and previous_progress is not None
                and current_progress < previous_progress - 3000
            )

            if playback_restarted:
                print(f"User {user_id}: playback restarted")
            last_seen_progress[user_id] = current_progress

        if not track or not track["is_playing"]:
            last_seen_progress.pop(user_id, None)
            last_seen_track_ids.pop(user_id, None)
            return

        if not track_changed and not playback_restarted:
            return
        result = process_current_track(user, db, track=track)

        if result["status"] in ("queued", "already_queued"):
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
                    last_seen_progress.pop(user_id, None)
                    last_seen_track_ids.pop(user_id, None)
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