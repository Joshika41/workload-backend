import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class RoleEnum(str, enum.Enum):
    MASTER_ADMIN = "MASTER_ADMIN"
    DEAN = "DEAN"
    COORDINATOR = "COORDINATOR"
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"

class SubjectCategoryEnum(str, enum.Enum):
    THEORY = "Theory"
    LAB = "Lab"
    JOINT_COURSE = "Joint Course"
    ELECTIVE = "Elective"
    PROJECT = "Project"

class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    programme_scope = Column(String, nullable=False)

    users = relationship("User", back_populates="department")
    subjects = relationship("Subject", back_populates="department")

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)

    department = relationship("Department", back_populates="users")
    faculty_profile = relationship("Faculty", back_populates="user", uselist=False)

class Faculty(Base):
    __tablename__ = 'faculty'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    max_theory_hrs = Column(Float, default=0.0)
    max_lab_hrs = Column(Float, default=0.0)

    user = relationship("User", back_populates="faculty_profile")
    allocations = relationship("WorkloadAllocation", back_populates="faculty")

class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    course_code = Column(String, nullable=False)
    course_name = Column(String, nullable=False)
    programme = Column(String, nullable=False)
    regulations = Column(Integer, nullable=False)
    semester = Column(String, nullable=False)
    category = Column(Enum(SubjectCategoryEnum), nullable=False)

    department = relationship("Department", back_populates="subjects")
    allocations = relationship("WorkloadAllocation", back_populates="subject")

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(String, unique=True, nullable=False)
    is_lab = Column(Boolean, default=False)
    capacity = Column(Integer, nullable=False)

class WorkloadAllocation(Base):
    __tablename__ = 'workload_allocations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    faculty_id = Column(Integer, ForeignKey('faculty.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    class_section = Column(String, nullable=False)
    theory_hours = Column(Float, default=0.0)
    practical_hours = Column(Float, default=0.0)

    faculty = relationship("Faculty", back_populates="allocations")
    subject = relationship("Subject", back_populates="allocations")

class TimeSlot(Base):
    __tablename__ = 'time_slots'
    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    day_of_week = Column(String, nullable=False)
    period_number = Column(Integer, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    is_break = Column(Boolean, default=False)
    
    department = relationship("Department")

class PreferenceTypeEnum(str, enum.Enum):
    AVOID = "AVOID"
    PREFER = "PREFER"

class FacultyPreference(Base):
    __tablename__ = 'faculty_preferences'
    id = Column(Integer, primary_key=True, autoincrement=True)
    faculty_id = Column(Integer, ForeignKey('faculty.id'), nullable=False)
    preferred_day = Column(String, nullable=False)
    preferred_period = Column(Integer, nullable=False)
    preference_type = Column(Enum(PreferenceTypeEnum), nullable=False)
    
    faculty = relationship("Faculty")

class GeneratedTimetable(Base):
    __tablename__ = 'generated_timetables'
    id = Column(Integer, primary_key=True, autoincrement=True)
    allocation_id = Column(Integer, ForeignKey('workload_allocations.id'), nullable=False)
    day = Column(String, nullable=False)
    period = Column(Integer, nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    
    allocation = relationship("WorkloadAllocation")
    room = relationship("Room")
