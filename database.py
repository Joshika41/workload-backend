
import uuid
from datetime import datetime
from sqlalchemy import JSON, DateTime

import enum
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

import os
from dotenv import load_dotenv
load_dotenv()

# SMART MOVE: Switch this line to your postgres:// URL during deployment!
DATABASE_URL = os.environ["DATABASE_URL"]

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Department(Base):
    __tablename__ = "departments"
    name = Column(String, primary_key=True, index=True)
    has_labs = Column(Boolean, default=True)


class ProgramTypeEnum(str, enum.Enum):
    UG = "UG"
    PG = "PG"

class SemesterTypeEnum(str, enum.Enum):
    ODD = "ODD"
    EVEN = "EVEN"

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
    faculty_id = Column(String, ForeignKey("faculty.faculty_id"), nullable=True)

    faculty_rel = relationship("Faculty")

class Faculty(Base):
    __tablename__ = "faculty"
    faculty_id = Column(String, primary_key=True, index=True) # Faculty ID
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    designation = Column(String, nullable=True)
    official_email = Column(String, nullable=True)
    is_quarantined = Column(Boolean, default=False)

class Room(Base):
    __tablename__ = "rooms"
    room_number = Column(String, primary_key=True, index=True)
    room_type = Column(String, nullable=False) # 'Classroom' or 'Lab'
    capacity = Column(Integer, nullable=False)

class Syllabus(Base):
    __tablename__ = "syllabus"
    subject_code = Column(String, primary_key=True, index=True)
    course_title = Column(String, nullable=False)
    course_type = Column(String, nullable=False) # 'Theory' or 'Practical'
    subject_category = Column(String, nullable=True) # C, D, E, M, S, A, V
    theory_hours_l = Column(Integer, default=0)
    practical_hours_p = Column(Integer, default=0)
    credits_c = Column(Integer, default=0)
    program_type = Column(Enum(ProgramTypeEnum), nullable=True)
    semester_type = Column(Enum(SemesterTypeEnum), nullable=True)
    category = Column(String, nullable=False) # 'UG' or 'PG'
    batch_sync_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class WorkloadConfiguration(Base):
    __tablename__ = "workload_configurations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    faculty_id = Column(String, ForeignKey("faculty.faculty_id"), unique=True)
    theory_hours = Column(Integer, default=0) # Dropdown: 1, 2, 4
    lab_hours = Column(Integer, default=0)
    incharge_hours = Column(Integer, default=0) # 2 hours if assistant/incharge
    max_hours_limit = Column(Integer, default=16) # From total hours file
    total_calculated_hours = Column(Integer, default=0)
    is_overloaded = Column(Boolean, default=False)
    program_type = Column(Enum(ProgramTypeEnum), nullable=True)
    semester_type = Column(Enum(SemesterTypeEnum), nullable=True)

    faculty_rel = relationship("Faculty")

class FacultyPreference(Base):
    __tablename__ = "faculty_preferences"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    faculty_id = Column(String, ForeignKey("faculty.faculty_id"), nullable=False)
    subject_name = Column(String, nullable=False)
    status = Column(String, default="PENDING")

    faculty_rel = relationship("Faculty")

class TimetableBlock(Base):
    __tablename__ = "timetable_blocks"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    faculty_id = Column(String, ForeignKey("faculty.faculty_id"), nullable=False)
    section = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    day = Column(Integer, nullable=False)
    period = Column(Integer, nullable=False)
    program_type = Column(Enum(ProgramTypeEnum), nullable=True)
    semester_type = Column(Enum(SemesterTypeEnum), nullable=True)

# Create the tables automatically in SQLite

class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, default="PENDING")
    result_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Cohort(Base):
    __tablename__ = "cohorts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    department = Column(String, nullable=False)
    academic_year = Column(Integer, nullable=False)
    class_name = Column(String, nullable=False)
    section = Column(String, nullable=False)
    program_type = Column(Enum(ProgramTypeEnum), nullable=True)
    semester_type = Column(Enum(SemesterTypeEnum), nullable=True)

class CohortSyllabusMapping(Base):
    __tablename__ = "cohort_syllabus_mapping"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cohort_id = Column(String, ForeignKey("cohorts.id"), nullable=False)
    subject_code = Column(String, ForeignKey("syllabus.subject_code"), nullable=False)


class PreferenceConstraint(Base):
    __tablename__ = "preference_constraints"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    program_type = Column(Enum(ProgramTypeEnum), nullable=False)
    semester_type = Column(Enum(SemesterTypeEnum), nullable=False)
    subject_category = Column(String, nullable=False)
    max_allowed = Column(Integer, nullable=False)

class SubjectPreference(Base):
    __tablename__ = "subject_preferences"
    preference_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    faculty_id = Column(String, ForeignKey("faculty.faculty_id"), nullable=False)
    subject_code = Column(String, ForeignKey("syllabus.subject_code"), nullable=False)
    status = Column(String, default="PENDING")

Base.metadata.create_all(bind=engine)
