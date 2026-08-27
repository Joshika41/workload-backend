import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal, TimetableBlock

def check_blocks():
    db = SessionLocal()
    try:
        blocks = db.query(TimetableBlock).all()
        
        print(f"Total blocks successfully saved: {len(blocks)}")
        print("-" * 60)
        for block in blocks:
            print(f"Faculty ID: {block.faculty_id} | Subject: {block.subject} | Day: {block.day} | Period: {block.period}")
        print("-" * 60)
    finally:
        db.close()

if __name__ == "__main__":
    check_blocks()
