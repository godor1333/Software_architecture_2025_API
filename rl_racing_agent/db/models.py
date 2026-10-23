from sqlalchemy import Column, Integer, Float, Boolean, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TelemetryORM(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode = Column(Integer, nullable=False)
    step = Column(Integer, nullable=False)
    reward = Column(Float, nullable=False)
    speed = Column(Float, nullable=False)
    progress = Column(Float, nullable=False)
    crashed = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)