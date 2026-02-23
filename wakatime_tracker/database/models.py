from sqlalchemy import Column, String, DateTime, Float, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ProjectSummary(Base):
    __tablename__ = "project_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    project_name = Column(String(255), nullable=False)
    total_seconds = Column(Float, nullable=False)
    digital_time = Column(String(20))
    text_time = Column(String(50))
    percent = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_date_project", "date", "project_name", unique=True),
        Index("idx_date", "date"),
        Index("idx_project", "project_name"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "project_name": self.project_name,
            "total_seconds": self.total_seconds,
            "digital_time": self.digital_time,
            "text_time": self.text_time,
            "percent": self.percent,
            "created_at": self.created_at.isoformat(),
        }
