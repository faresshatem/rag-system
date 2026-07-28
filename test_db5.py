import asyncio
import os
import asyncpg
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

async def main():
    conn = await asyncpg.connect(user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"), host='localhost', port=5432, database='postgres')
    dbs = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false;")
    print("Databases:", [db['datname'] for db in dbs])
    await conn.close()

asyncio.run(main())
