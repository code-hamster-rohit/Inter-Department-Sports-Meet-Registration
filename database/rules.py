from typing import Any
from bson import ObjectId
from database.config import db, client


def _get_collection(database: Any = None, collection: Any = None):
    if collection is None and isinstance(database, str):
        return db[database]

    target_db = client[database] if isinstance(database, str) else (database or db)
    if isinstance(collection, str):
        return target_db[collection]
    return collection


def _format_query(query: Any) -> dict:
    if not query:
        return {}
    if isinstance(query, (str, ObjectId)):
        return {"_id": ObjectId(query) if isinstance(query, str) and ObjectId.is_valid(query) else query}

    formatted = dict(query)
    if "_id" in formatted and isinstance(formatted["_id"], str) and ObjectId.is_valid(formatted["_id"]):
        formatted["_id"] = ObjectId(formatted["_id"])
    return formatted


def _serialize(doc: dict | None) -> dict | None:
    if not doc:
        return None
    res = dict(doc)
    if "_id" in res:
        res["_id"] = str(res["_id"])
    return res


async def add(data: dict | list[dict], database: Any = None, collection: Any = None):
    col = _get_collection(database, collection)
    if isinstance(data, list):
        res = await col.insert_many([dict(d) for d in data])
        return [str(item_id) for item_id in res.inserted_ids]

    res = await col.insert_one(dict(data))
    return str(res.inserted_id)


async def find(query: dict | None = None, database: Any = None, collection: Any = None, one: bool = False):
    col = _get_collection(database, collection)
    formatted_query = _format_query(query)

    if one:
        doc = await col.find_one(formatted_query)
        return _serialize(doc)

    docs = await col.find(formatted_query).to_list(length=None)
    return [_serialize(d) for d in docs]


async def update(query: dict, data: dict, database: Any = None, collection: Any = None, multiple: bool = False):
    col = _get_collection(database, collection)
    formatted_query = _format_query(query)
    update_data = data if any(k.startswith("$") for k in data) else {"$set": data}

    if multiple:
        res = await col.update_many(formatted_query, update_data)
    else:
        res = await col.update_one(formatted_query, update_data)

    return {"matched_count": res.matched_count, "modified_count": res.modified_count}


async def remove(query: dict, database: Any = None, collection: Any = None, multiple: bool = False):
    col = _get_collection(database, collection)
    formatted_query = _format_query(query)

    if multiple:
        res = await col.delete_many(formatted_query)
    else:
        res = await col.delete_one(formatted_query)

    return {"deleted_count": res.deleted_count}