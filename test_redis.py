import asyncio
from redis.asyncio import Redis as AsyncRedis

async def main():
    r = AsyncRedis.from_url("redis://localhost:6379/0")
    keys = await r.keys("sql_cache*")
    for k in keys:
        val = await r.get(k)
        print(f"Key: {k.decode('utf-8')}")
        print(f"Val: {val.decode('utf-8')}\n")

asyncio.run(main())
