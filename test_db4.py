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
        sql = "SELECT id, title FROM it_tickets"
        result = await conn.execute(text(sql))
        rows = result.fetchall()
        print("TICKETS:", rows)
        
        sql = "SELECT id, full_name FROM users"
        result = await conn.execute(text(sql))
        rows = result.fetchall()
        print("USERS:", rows)

asyncio.run(main())
