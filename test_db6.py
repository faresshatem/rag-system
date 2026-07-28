import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

async def main():
    LLM_DATABASE_URL = os.getenv("LLM_DATABASE_URL")
    engine = create_async_engine(LLM_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        sql = "SELECT id, title FROM it_tickets"
        try:
            result = await conn.execute(text(sql))
            rows = result.fetchall()
            print("TICKETS:", rows)
        except Exception as e:
            print("ERROR:", e)

asyncio.run(main())
