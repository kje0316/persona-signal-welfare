"""
데이터베이스 연결 및 관리
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """데이터베이스 설정"""

    def __init__(self):
        # 환경변수에서 DB URL 가져오기
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/persona_welfare"
        )
        self.debug = os.getenv("DEBUG", "False").lower() == "true"

    @property
    def async_database_url(self) -> str:
        """비동기 URL 반환"""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")


class DatabaseManager:
    """데이터베이스 매니저"""

    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()

        # 동기 엔진 (pandas 작업용)
        self.sync_engine = create_engine(
            self.config.database_url,
            pool_pre_ping=True,
            echo=self.config.debug
        )

        # 비동기 엔진 (FastAPI용)
        self.async_engine = create_async_engine(
            self.config.async_database_url,
            pool_pre_ping=True,
            echo=self.config.debug
        )

        # 세션 팩토리
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.sync_engine
        )

        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_tables(self):
        """테이블 생성"""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("데이터베이스 테이블 생성 완료")
        except Exception as e:
            logger.error(f"테이블 생성 실패: {e}")
            raise

    def get_sync_session(self) -> Session:
        """동기 세션 가져오기"""
        return self.SessionLocal()

    async def get_async_session(self) -> AsyncSession:
        """비동기 세션 가져오기"""
        return self.AsyncSessionLocal()

    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """비동기 세션 컨텍스트 매니저"""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def save_dataframe_to_table(self, df: pd.DataFrame, table_name: str) -> bool:
        """데이터프레임을 테이블로 저장"""
        try:
            df.to_sql(
                table_name,
                con=self.sync_engine,
                if_exists='replace',
                index=False,
                method='multi',
                chunksize=1000
            )
            logger.info(f"데이터프레임 저장 완료: {table_name} ({len(df)} rows)")
            return True
        except Exception as e:
            logger.error(f"데이터프레임 저장 실패: {e}")
            return False

    def load_dataframe_from_table(self, table_name: str) -> pd.DataFrame:
        """테이블에서 데이터프레임 로드"""
        try:
            df = pd.read_sql_table(table_name, con=self.sync_engine)
            logger.info(f"데이터프레임 로드 완료: {table_name} ({len(df)} rows)")
            return df
        except Exception as e:
            logger.error(f"데이터프레임 로드 실패: {e}")
            return pd.DataFrame()

    def execute_sql(self, query: str, params: dict = None) -> pd.DataFrame:
        """SQL 쿼리 실행 후 DataFrame 반환"""
        try:
            with self.sync_engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                return pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            logger.error(f"SQL 실행 실패: {e}")
            return pd.DataFrame()

    def table_exists(self, table_name: str) -> bool:
        """테이블 존재 여부 확인"""
        try:
            with self.sync_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"),
                    {"table_name": table_name}
                )
                return result.scalar()
        except Exception as e:
            logger.error(f"테이블 존재 확인 실패: {e}")
            return False

    def get_table_info(self, table_name: str) -> dict:
        """테이블 정보 가져오기"""
        try:
            with self.sync_engine.connect() as conn:
                # 컬럼 정보
                columns_query = text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    ORDER BY ordinal_position
                """)
                columns_result = conn.execute(columns_query, {"table_name": table_name})
                columns = [dict(row._mapping) for row in columns_result]

                # 행 수
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                row_count = conn.execute(count_query).scalar()

                return {
                    "table_name": table_name,
                    "columns": columns,
                    "row_count": row_count
                }
        except Exception as e:
            logger.error(f"테이블 정보 조회 실패: {e}")
            return {}

    async def close(self):
        """연결 종료"""
        await self.async_engine.dispose()
        self.sync_engine.dispose()


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()