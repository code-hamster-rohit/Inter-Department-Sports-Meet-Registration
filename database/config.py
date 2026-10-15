import asyncio
import os
import certifi
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

load_dotenv()

MONGODB_URI: str = os.getenv("MONGODB_URI", "")
DATABASE_NAME: str = os.getenv("DATABASE_NAME", "departments")

# Loop-aware client store prevents PyMongo cross-event-loop RuntimeErrors
_clients: dict[int, AsyncMongoClient] = {}


def get_client() -> AsyncMongoClient:
    try:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
    except RuntimeError:
        loop_id = 0

    if loop_id not in _clients:
        _clients[loop_id] = AsyncMongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(),
        )
    return _clients[loop_id]


def get_database(name: str | None = None):
    return get_client()[name or DATABASE_NAME]


# Dynamic proxies for direct db/client access matching current event loop
class _DBProxy:
    def __getitem__(self, item):
        return get_database()[item]

    def __getattr__(self, name):
        return getattr(get_database(), name)


class _ClientProxy:
    def __getitem__(self, item):
        return get_client()[item]

    def __getattr__(self, name):
        return getattr(get_client(), name)


client = _ClientProxy()
db = _DBProxy()


async def ping_db() -> bool:
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


async def close_connection():
    for c in list(_clients.values()):
        await c.close()
    _clients.clear()