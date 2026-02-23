from contextlib import contextmanager
from datetime import datetime, UTC
from typing import Generator

from sqlalchemy import create_engine, func, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from wakatime_tracker.config import load_config
from wakatime_tracker.database.models import ProjectSummary
import logging
import time

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.config = load_config()
        self.engine: Engine | None = None
        self.session_pool: sessionmaker[Session] | None = None
        self._init_engine()

    def _init_engine(self):
        max_retries = 5
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                self.engine = create_engine(self.config.database.url, pool_pre_ping=True, echo=False)
                self.session_pool = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

                logger.info("Database connection established")
                break

            except SQLAlchemyError as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to establish database connection after all retries")
                    raise

    @contextmanager
    def get_session(self) -> Generator[Session, Session, None]:
        with self.session_pool() as session:
            yield session

    def has_data(self) -> bool:
        """Проверка на наличие данных в базе"""

        with self.get_session() as session:
            count = session.query(ProjectSummary).count()
            return count > 0

    def save_project_data(self, date: str, project_data: dict):
        """Сохранение данных проекта с обновлением при существовании"""

        with self.get_session() as session:
            try:
                # Проверяем, существует ли уже запись
                existing = (
                    session.query(ProjectSummary)
                    .filter(ProjectSummary.date == date, ProjectSummary.project_name == project_data["name"])
                    .first()
                )

                if existing:
                    # Обновляем существующую запись
                    existing.total_seconds = project_data["total_seconds"]
                    existing.digital_time = project_data.get("digital", "")
                    existing.text_time = project_data.get("text", "")
                    existing.percent = project_data.get("percent", 0)
                    existing.updated_at = datetime.now(UTC)

                    logger.debug(f"Updated data for project {project_data['name']} on {date}")
                else:
                    # Создаем новую запись
                    project = ProjectSummary(
                        date=date,
                        project_name=project_data["name"],
                        total_seconds=project_data["total_seconds"],
                        digital_time=project_data.get("digital", ""),
                        text_time=project_data.get("text", ""),
                        percent=project_data.get("percent", 0),
                    )
                    session.add(project)
                    logger.debug(f"Saved new data for project {project_data['name']} on {date}")

                session.commit()

            except IntegrityError:
                self._update_existing(session, date, project_data)
            except Exception as e:
                logger.error(f"Error saving project data: {e}")
                raise

    @staticmethod
    def _update_existing(session: Session, date: str, project_data: dict):
        """Обновление существующей записи при IntegrityError"""

        try:
            existing = (
                session.query(ProjectSummary)
                .filter(ProjectSummary.date == date, ProjectSummary.project_name == project_data["name"])
                .with_for_update()
                .first()
            )

            if existing:
                existing.total_seconds = project_data["total_seconds"]
                existing.digital_time = project_data.get("digital", "")
                existing.text_time = project_data.get("text", "")
                existing.percent = project_data.get("percent", 0)
                existing.updated_at = datetime.now(UTC)

            session.commit()
        except Exception as e:
            logger.error(f"Error in update retry: {e}")
            raise

    def get_project_stats(self, start_date: str, end_date: str, project_name: str = None):
        """Получение статистики по проектам за период"""

        with self.get_session() as session:
            query = session.query(ProjectSummary).filter(
                ProjectSummary.date >= start_date, ProjectSummary.date <= end_date
            )

            if project_name:
                query = query.filter(ProjectSummary.project_name == project_name)

            return [item.to_dict() for item in query.order_by(ProjectSummary.date.desc()).all()]

    def get_unique_projects(self):
        """Получение списка уникальных проектов"""

        with self.get_session() as session:
            projects = session.query(ProjectSummary.project_name).distinct().all()
            return [p[0] for p in projects]

    def get_daily_totals(self, start_date: str, end_date: str):
        """Получение ежедневных итогов"""

        with self.get_session() as session:
            result = (
                session.query(ProjectSummary.date, func.sum(ProjectSummary.total_seconds).label("total_seconds"))
                .filter(ProjectSummary.date >= start_date, ProjectSummary.date <= end_date)
                .group_by(ProjectSummary.date)
                .order_by(ProjectSummary.date)
                .all()
            )

            return [{"date": r[0], "total_seconds": r[1]} for r in result]
