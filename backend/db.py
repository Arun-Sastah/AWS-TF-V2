from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table, Column, Integer, String, Text, Float, TIMESTAMP, MetaData, func
import asyncio
from datetime import datetime

# -------------------------
# PostgreSQL Async Engine
# -------------------------
DATABASE_URL = "postgresql+asyncpg://postgres:Blitz%26024@db:5432/infra_audit_db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

metadata = MetaData()

# -------------------------
# Table Definition
# -------------------------
request_status_log = Table(
    "request_status_log",
    metadata,
    Column("log_id", Integer, primary_key=True, autoincrement=True),
    Column("request_id", Integer, nullable=True),
    Column("status", String, nullable=True),
    Column("terraform_plan", Text, nullable=True),
    Column("terraform_apply", Text, nullable=True),
    Column("duration_seconds", Float, nullable=True),
    Column("updated_at", TIMESTAMP(timezone=False), server_default=func.now()),
    Column("terraform_plan_log", Text, nullable=True),
    Column("terraform_apply_log", Text, nullable=True),
)

# -------------------------
# Logging Function
# -------------------------
async def log_request(
    request_id: int,
    status: str,
    terraform_plan: str = None,
    terraform_apply: str = None,
    duration_seconds: float = None,
    terraform_plan_log: str = None,
    terraform_apply_log: str = None,
):
    """
    Log Terraform request info to PostgreSQL
    """
    async with async_session() as session:
        async with session.begin():
            insert_stmt = request_status_log.insert().values(
                request_id=request_id,
                status=status,
                terraform_plan=terraform_plan,
                terraform_apply=terraform_apply,
                duration_seconds=duration_seconds,
                updated_at=datetime.utcnow(),
                terraform_plan_log=terraform_plan_log,
                terraform_apply_log=terraform_apply_log,
            )
            await session.execute(insert_stmt)
        await session.commit()
    return True

# -------------------------
# Test Connection
# -------------------------
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    print("✅ Database connected and table created (if not exists).")

# Run test
if __name__ == "__main__":
    asyncio.run(test_db())
