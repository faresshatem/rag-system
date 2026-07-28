import asyncio
import os
import asyncpg
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

async def main():
    conn = await asyncpg.connect(user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"), host='localhost', port=5432, database='postgres')
    try:
        rows = await conn.fetch("SELECT id, title FROM it_tickets")
        print("postgres DB TICKETS:", rows)
    except Exception as e:
        print("postgres DB error:", e)
    finally:
        await conn.close()

asyncio.run(main())
