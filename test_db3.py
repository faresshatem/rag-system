import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

async def main():
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        sql = "SELECT it_tickets.title, it_tickets.status, it_tickets.priority, users.id, users.full_name FROM it_tickets JOIN users ON it_tickets.user_id = users.id WHERE users.full_name ILIKE '%Ahm%'"
        result = await conn.execute(text(sql))
        rows = result.fetchall()
        print("ROWS:", rows)

asyncio.run(main())
