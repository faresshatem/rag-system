import asyncio
import os
import asyncpg
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

async def main():
    try:
        conn = await asyncpg.connect(user=os.getenv("LLM_POSTGRES_USER"), password=os.getenv("LLM_POSTGRES_PASSWORD"), host='localhost', port=5432, database='postgres')
        rows = await conn.fetch("SELECT id, title FROM it_tickets")
        print("nlq_readonly connected to postgres! TICKETS:", rows)
        await conn.close()
    except Exception as e:
        print("nlq_readonly error:", e)

asyncio.run(main())
