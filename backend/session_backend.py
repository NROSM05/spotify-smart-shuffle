
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from backend.database import SessionLocal
from backend.models import ServerSession
from starlette_session.interfaces import ISessionBackend


class PostgresSessionBackend(ISessionBackend):
    async def get(self, key: str) -> dict | None:
        def _get():
            with SessionLocal() as db:
                session = db.scalar(
                    select(ServerSession).where(
                        ServerSession.id == key
                    )
                )

                if session is None:
                    return None

                expires_at = session.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)

                if expires_at <= datetime.now(timezone.utc):
                    db.delete(session)
                    db.commit()
                    return None

                return session.data

        return await asyncio.to_thread(_get)

    async def set(
        self,
        key: str,
        value: dict,
        exp: int | None,
    ) -> str:
        def _set():
            expiry = datetime.now(timezone.utc) + timedelta(
                seconds=exp if exp is not None else 1209600
            )

            with SessionLocal() as db:
                session = db.get(ServerSession, key)

                if session is None:
                    session = ServerSession(
                        id=key,
                        data=value,
                        expires_at=expiry,
                    )
                    db.add(session)
                else:
                    session.data = value
                    session.expires_at = expiry

                db.commit()

            return key

        return await asyncio.to_thread(_set)

    async def delete(self, key: str) -> None:
        def _delete():
            with SessionLocal() as db:
                db.execute(
                    delete(ServerSession).where(
                        ServerSession.id == key
                    )
                )
                db.commit()

        await asyncio.to_thread(_delete)
