
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class MonitoredProcess(Base):
    __tablename__ = 'monitored_processes'

    id = Column(Integer, primary_key=True)
    process_name = Column(String, nullable=False)
    pid = Column(Integer, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    last_uptime_seconds = Column(Float, nullable=True)
    
    # Relationship to activity logs
    activity_logs = relationship("ProcessActivityLog", back_populates="process", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MonitoredProcess(process_name='{self.process_name}', pid={self.pid})>"

class ProcessActivityLog(Base):
    __tablename__ = 'process_activity_logs'

    id = Column(Integer, primary_key=True)
    process_id = Column(Integer, ForeignKey('monitored_processes.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    last_activity_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    session_uptime_seconds = Column(Float, nullable=True)

    # Relationship to parent process
    process = relationship("MonitoredProcess", back_populates="activity_logs")

    def __repr__(self):
        return f"<ProcessActivityLog(process_id={self.process_id}, start_time='{self.start_time}')>"

# Create database engine and session
engine = create_engine('sqlite:///process_monitor.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
