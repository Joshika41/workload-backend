from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import uuid
import os

import io
import models
from database import SessionLocal
from routers.auth import get_current_user, verify_admin_role

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/upload/syllabus")
async def upload_syllabus(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(verify_admin_role)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name='CD FORMAT ', skiprows=3)
        
        dept = db.query(models.Department).first()
        if not dept:
            dept = models.Department(name="General", programme_scope="Both")
            db.add(dept)
            db.commit()
            db.refresh(dept)
            
        department_id = dept.id
        subjects_to_insert = []
        
        for _, row in df.iterrows():
            course_code = row.get('Course Code')
            course_name = row.get('Course Name')
            programme = row.get('Programme')
            regulations = row.get('Regulations')
            semester = row.get('Semester')
            category_raw = row.get('Course Category')
            
            if pd.isna(course_code):
                continue
                
            subject = models.Subject(
                department_id=department_id,
                course_code=str(course_code),
                course_name=str(course_name) if pd.notna(course_name) else "",
                programme=str(programme) if pd.notna(programme) else "",
                regulations=int(regulations) if pd.notna(regulations) else 2025,
                semester=str(semester) if pd.notna(semester) else "I",
                category=str(category_raw) if pd.notna(category_raw) else "Theory"
            )
            subjects_to_insert.append(subject)

        db.add_all(subjects_to_insert)
        db.commit()
        
        return {"message": f"Successfully ingested {len(subjects_to_insert)} subjects"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/upload/faculty_list")
async def upload_faculty_list(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(verify_admin_role)):
    try:
        contents = await file.read()
        # Assumes the first sheet is the faculty list if sheet_name not specified, or just reads it
        df = pd.read_excel(io.BytesIO(contents))
        
        default_user = db.query(models.User).filter_by(email="default_faculty@example.com").first()
        if not default_user:
            default_user = models.User(
                email="default_faculty@example.com",
                hashed_password="hashed_password",
                role=models.RoleEnum.FACULTY
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            
        faculty_to_insert = []
        
        for _, row in df.iterrows():
            staff_name = row.get('Staff Name')
            designation = row.get('Designation')
            
            if pd.isna(staff_name):
                continue
                
            staff_name = str(staff_name).strip()
            designation = str(designation).strip() if pd.notna(designation) else "Faculty"
            
            # Avoid duplicates
            existing = db.query(models.Faculty).filter(models.Faculty.name == staff_name).first()
            if not existing:
                faculty = models.Faculty(
                    user_id=default_user.id,
                    name=staff_name,
                    designation=designation
                )
                faculty_to_insert.append(faculty)
                
        db.add_all(faculty_to_insert)
        db.commit()
        
        return {"message": f"Successfully ingested {len(faculty_to_insert)} faculty members"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/upload/rooms")
async def upload_rooms(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(verify_admin_role)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        rooms_to_insert = []
        for _, row in df.iterrows():
            room_number = row.get('Room Number')
            is_lab = row.get('Is Lab')
            capacity = row.get('Capacity')
            
            if pd.isna(room_number):
                continue
                
            room = models.Room(
                number=str(room_number).strip(),
                is_lab=bool(is_lab) if pd.notna(is_lab) else False,
                capacity=int(capacity) if pd.notna(capacity) else 60
            )
            rooms_to_insert.append(room)
            
        db.add_all(rooms_to_insert)
        db.commit()
        return {"message": f"Successfully ingested {len(rooms_to_insert)} rooms"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/admin/upload-faculty")
async def upload_faculty_onboarding(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(verify_admin_role)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Determine mapping for ERP ID
        # Assumes column name is "ERP ID" or something similar. Let's look for "ERP ID" explicitly.
        # But maybe we should flexibly accept "Faculty ID" or "ERP ID".
        erp_col = next((col for col in df.columns if 'erp' in col.lower() or 'id' in col.lower()), None)
        name_col = next((col for col in df.columns if 'name' in col.lower()), None)
        dept_col = next((col for col in df.columns if 'department' in col.lower()), None)
        desig_col = next((col for col in df.columns if 'designation' in col.lower()), None)
        email_col = next((col for col in df.columns if 'email' in col.lower()), None)

        if not erp_col or not name_col:
            raise HTTPException(status_code=400, detail="Excel must contain an ERP ID and Name column.")

        faculty_to_insert = []
        users_to_insert = []
        emails_to_dispatch = []

        smtp_host = os.environ.get('SMTP_HOST')
        smtp_user = os.environ.get('SMTP_USER')
        smtp_pass = os.environ.get('SMTP_PASS')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        
        from routers.auth import get_password_hash

        with db.begin_nested():
            for _, row in df.iterrows():
                erp_id = str(row.get(erp_col)).strip()
                name = str(row.get(name_col)).strip()
                dept = str(row.get(dept_col)).strip() if dept_col and pd.notna(row.get(dept_col)) else "Unknown"
                desig = str(row.get(desig_col)).strip() if desig_col and pd.notna(row.get(desig_col)) else "Faculty"
                off_email = str(row.get(email_col)).strip() if email_col and pd.notna(row.get(email_col)) else ""

                if pd.isna(row.get(name_col)):
                    continue

                is_quarantined = False
                skip_email = False
                
                # Quarantine Check
                if "new faculty" in erp_id.lower():
                    erp_id = f"TEMP-{uuid.uuid4().hex[:8].upper()}"
                    is_quarantined = True
                    skip_email = True
                
                temp_password = secrets.token_urlsafe(8)
                
                # Check for existing user
                existing_user = db.query(models.User).filter_by(username=erp_id).with_for_update().first()
                if not existing_user:
                    user_record = models.User(
                        email=off_email if off_email else f"{erp_id}@example.com",
                        username=erp_id,
                        hashed_password=get_password_hash(temp_password),
                        role=models.RoleEnum.FACULTY
                    )
                    db.add(user_record)
                    db.flush()
                    user_id = user_record.id
                else:
                    user_id = existing_user.id
                    
                existing_faculty = db.query(models.Faculty).filter_by(faculty_id=erp_id).with_for_update().first()
                if not existing_faculty:
                    faculty = models.Faculty(
                        faculty_id=erp_id,
                        user_id=user_id,
                        name=name,
                        department=dept,
                        designation=desig,
                        official_email=off_email,
                        is_quarantined=is_quarantined
                    )
                    db.add(faculty)
                    
                    if not skip_email and off_email:
                        emails_to_dispatch.append({
                            "email": off_email,
                            "erp_id": erp_id,
                            "password": temp_password,
                            "name": name
                        })

        db.commit()

        # SMTP Dispatch Phase
        for email_data in emails_to_dispatch:
            msg_body = f"Hello {email_data['name']},\n\nWelcome to the University Workload ERP.\nYour ERP ID (Username) is: {email_data['erp_id']}\nYour Temporary Password is: {email_data['password']}\n\nPlease log in and update your preferences."
            
            if smtp_host and smtp_user and smtp_pass:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = smtp_user
                    msg['To'] = email_data['email']
                    msg['Subject'] = "Welcome to the University Workload ERP"
                    msg.attach(MIMEText(msg_body, 'plain'))
                    
                    server = smtplib.SMTP(smtp_host, smtp_port)
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                    server.quit()
                except Exception as e:
                    print(f"[SMTP FAIL] Could not send to {email_data['email']}: {e}")
                    print(f"--- EMAIL PAYLOAD (Fallback) ---\n{msg_body}\n--------------------------")
            else:
                # Zero-Trust Fallback
                print(f"[SMTP ZERO-TRUST MOCK] Email to {email_data['email']}")
                print(f"--- EMAIL PAYLOAD ---\n{msg_body}\n--------------------")

        return {"message": f"Successfully onboarded new faculty entries.", "emails_dispatched": len(emails_to_dispatch)}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
