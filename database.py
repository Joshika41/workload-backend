import enum
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

import os

# SMART MOVE: Switch this line to your postgres:// URL during deployment!
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./university_timetable.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    FACULTY = "FACULTY"
    DEAN = "DEAN"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.FACULTY, nullable=False)
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=True)

    faculty_rel = relationship("Faculty")

class Faculty(Base):
    __tablename__ = "faculty"
    id = Column(String, primary_key=True, index=True) # Faculty ID
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)

class Room(Base):
    __tablename__ = "rooms"
    room_number = Column(String, primary_key=True, index=True)
    room_type = Column(String, nullable=False) # 'Classroom' or 'Lab'
    capacity = Column(Integer, nullable=False)

class Syllabus(Base):
    __tablename__ = "syllabus"
    course_code = Column(String, primary_key=True, index=True)
    course_title = Column(String, nullable=False)
    course_type = Column(String, nullable=False) # 'Theory' or 'Practical'
    category = Column(String, nullable=False) # 'UG' or 'PG'

class WorkloadConfiguration(Base):
    __tablename__ = "workload_configurations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    faculty_id = Column(String, ForeignKey("faculty.id"), unique=True)
    theory_hours = Column(Integer, default=0) # Dropdown: 1, 2, 4
    lab_hours = Column(Integer, default=0)
    incharge_hours = Column(Integer, default=0) # 2 hours if assistant/incharge
    max_hours_limit = Column(Integer, default=16) # From total hours file
    total_calculated_hours = Column(Integer, default=0)
    is_overloaded = Column(Boolean, default=False)

    faculty_rel = relationship("Faculty")

class FacultyPreference(Base):
    __tablename__ = "faculty_preferences"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False)
    subject_name = Column(String, nullable=False)
    status = Column(String, default="PENDING")

    faculty_rel = relationship("Faculty")

class TimetableBlock(Base):
    __tablename__ = "timetable_blocks"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False)
    section = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    day = Column(Integer, nullable=False)
    period = Column(Integer, nullable=False)

# Create the tables automatically in SQLite
Base.metadata.create_all(bind=engine)
