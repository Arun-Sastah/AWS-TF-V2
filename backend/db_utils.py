import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import (
    Table, Column, Integer, String, Text, Float, TIMESTAMP,
    MetaData, ForeignKey, func, select
)

# -------------------------
# PostgreSQL Async Engine
# -------------------------
DATABASE_URL = "postgresql+asyncpg://postgres:Blitz%26024@127.0.0.1:5432/infra_audit_db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
metadata = MetaData()

# -------------------------
# Table Definitions
# -------------------------
request_status_logs = Table(
    "request_status_logs",
    metadata,
    Column("log_id", Integer, primary_key=True, autoincrement=True),
    Column("request_id", Integer, nullable=False),
    Column("user_id", String(100), nullable=False),
    Column("status", String(50), nullable=False),  # started, success, failed
    Column("duration_seconds", Float, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
)

request_resources = Table(
    "request_resources",
    metadata,
    Column("resource_id", Integer, primary_key=True, autoincrement=True),
    Column("log_id", Integer, ForeignKey("request_status_logs.log_id", ondelete="CASCADE"), nullable=False),
    Column("resource_type", String(100), nullable=True),
    Column("resource_name", String(255), nullable=True),
    Column("resource_id_value", String(255), nullable=True),
    Column("created_at", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False)
)

# -------------------------
# Logging Functions
# -------------------------
async def log_request(
    request_id: int,
    user_id: str,
    status: str,
    duration_seconds: float = None,
    error_message: str = None,
    created_at: datetime = None
):
    """
    Create or update a request log entry.
    Returns: log_id
    """
    async with async_session() as session:
        async with session.begin():
            # Check if a log for this request_id already exists
            result = await session.execute(
                select(request_status_logs.c.log_id).where(request_status_logs.c.request_id == request_id)
            )
            existing_log_id = result.scalar()

            if existing_log_id:
                # Update the existing entry instead of inserting a new one
                await session.execute(
                    request_status_logs.update()
                    .where(request_status_logs.c.log_id == existing_log_id)
                    .values(
                        status=status,
                        duration_seconds=duration_seconds,
                        error_message=error_message,
                        updated_at=datetime.utcnow()
                    )
                )
                log_id = existing_log_id
            else:
                # Insert a new log entry
                insert_stmt = request_status_logs.insert().values(
                    request_id=request_id,
                    user_id=user_id,
                    status=status,
                    duration_seconds=duration_seconds,
                    error_message=error_message,
                    created_at=created_at or datetime.utcnow()
                ).returning(request_status_logs.c.log_id)
                result = await session.execute(insert_stmt)
                log_id = result.scalar()

    return log_id


async def log_resource(log_id: int, resource_type: str, resource_name: str, resource_id_value: str):
    """
    Insert a resource linked to an existing request log.
    Ensures the log_id exists before inserting to avoid FK errors.
    """
    async with async_session() as session:
        async with session.begin():
            # Verify log_id exists
            result = await session.execute(
                select(request_status_logs.c.log_id).where(request_status_logs.c.log_id == log_id)
            )
            if not result.scalar():
                raise ValueError(f"❌ log_id {log_id} does not exist in request_status_logs")

            insert_stmt = request_resources.insert().values(
                log_id=log_id,
                resource_type=resource_type,
                resource_name=resource_name,
                resource_id_value=resource_id_value
            )
            await session.execute(insert_stmt)


# -------------------------
# Initialize DB
# -------------------------
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    print("✅ Database connected and tables created (if not exist).")


# -------------------------
# Run test if executed directly
# -------------------------
if __name__ == "__main__":
    asyncio.run(init_db())
