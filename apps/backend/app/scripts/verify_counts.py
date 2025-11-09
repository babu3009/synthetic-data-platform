"""
Quick verification script to print row counts from key tables.
"""
import asyncio
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal

TABLES: List[Tuple[str, str]] = [
    ("projects", "Projects"),
    ("sources", "Sources"),
    ("schemas", "Schemas"),
    ("requests", "Requests"),
    ("configs", "Configs"),
    ("artifacts", "Artifacts"),
    ("api_keys", "ApiKeys"),
    ("audit_events", "AuditEvents"),
    ("llm_providers", "LLM Providers"),
    ("llm_models", "LLM Models"),
    ("project_llm_settings", "Project LLM Settings"),
    ("project_members", "Project Members"),
]


async def main():
    print("🔎 Verifying table counts...\n")
    async with AsyncSessionLocal() as db:  # type: AsyncSession
        for tbl, label in TABLES:
            try:
                result = await db.execute(text(f"SELECT COUNT(*) FROM synthetic_data.{tbl}"))
                count = result.scalar_one()
                print(f"- {label:24s}: {count}")
            except Exception as e:
                print(f"- {label:24s}: error ({e})")


if __name__ == "__main__":
    asyncio.run(main())
