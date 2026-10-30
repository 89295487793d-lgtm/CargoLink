import asyncio
from app.database import Base, engine
from app import models  # noqa: F401 - registers models on Base.metadata

async def main() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
