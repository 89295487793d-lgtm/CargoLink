import asyncio
from sqlalchemy import select, text
from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401 - registers models on Base.metadata
from app.models import CargoChat, CargoRequest, CarrierOffer


async def main() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        # Additive migration for attachments; safe to run on every startup.
        await connection.execute(text(
            "ALTER TABLE cargo_chat_messages ADD COLUMN IF NOT EXISTS content_type VARCHAR(32)"
        ))
        await connection.execute(text(
            "ALTER TABLE cargo_chat_messages ADD COLUMN IF NOT EXISTS file_id VARCHAR(500)"
        ))
        await connection.execute(text("ALTER TABLE cargo_requests ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(30) NOT NULL DEFAULT 'accepted'"))
        await connection.execute(text("ALTER TABLE cargo_requests ADD COLUMN IF NOT EXISTS delivery_updated_at TIMESTAMPTZ"))
        await connection.execute(text("ALTER TABLE cargo_requests ADD COLUMN IF NOT EXISTS delivery_updated_by INTEGER REFERENCES users(id)"))
    # Backfill private chats for accepted offers created before the chat feature.
    async with SessionLocal() as session:
        result = await session.execute(
            select(CarrierOffer, CargoRequest)
            .join(CargoRequest, CargoRequest.id == CarrierOffer.request_id)
            .where(CarrierOffer.status == "accepted")
        )
        for offer, cargo in result.all():
            chat_result = await session.execute(select(CargoChat).where(CargoChat.offer_id == offer.id))
            if chat_result.scalar_one_or_none() is None:
                session.add(CargoChat(
                    request_id=cargo.id,
                    offer_id=offer.id,
                    customer_id=cargo.customer_id,
                    carrier_id=offer.carrier_id,
                    status="active",
                ))
        await session.commit()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
