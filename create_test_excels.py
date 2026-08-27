import pandas as pd

def create_excels():
    print("Generating sample Excel files...")

    # 1. Syllabus
    syllabus_data = {
        "course_code": ["CS101", "CS102", "MA201", "IT301", "DS401"],
        "course_title": ["Introduction to Programming", "Data Structures Lab", "Engineering Mathematics", "Database Systems", "Machine Learning"],
        "course_type": ["Theory", "Practical", "Theory", "Theory", "Practical"],
        "category": ["UG", "UG", "UG", "UG", "PG"]
    }
    pd.DataFrame(syllabus_data).to_excel("syllabus.xlsx", index=False)
    print("- syllabus.xlsx created")

    # 2. Faculty List
    faculty_data = {
        "faculty_id": ["FAC001", "FAC002", "FAC003", "FAC004", "FAC005"],
        "name": ["Dr. R. Anandan", "Prof. K. Sunitha", "Dr. Amit Verma", "Prof. S. Rajesh", "Dr. Priya Sharma"],
        "department": ["Computer Applications (MCA)", "Computer Applications (MCA)", "Computer Applications (MCA)", "Information Technology", "Computer Applications (MCA)"]
    }
    pd.DataFrame(faculty_data).to_excel("faculty_list.xlsx", index=False)
    print("- faculty_list.xlsx created")

    # 3. Rooms List
    rooms_data = {
        "room_number": ["CR-101", "CR-102", "LAB-01", "CR-201", "LAB-02"],
        "room_type": ["Classroom", "Classroom", "Lab", "Classroom", "Lab"],
        "capacity": [60, 60, 30, 80, 40]
    }
    pd.DataFrame(rooms_data).to_excel("rooms_list.xlsx", index=False)
    print("- rooms_list.xlsx created")

    # 4. Hours Reference (Total Hours)
    hours_data = {
        "faculty_id": ["FAC001", "FAC002", "FAC003", "FAC004", "FAC005"],
        "max_hours_limit": [16, 14, 16, 18, 16]
    }
    pd.DataFrame(hours_data).to_excel("hours_reference.xlsx", index=False)
    print("- hours_reference.xlsx created")

    print("\nAll 4 Excel files have been generated successfully!")

if __name__ == "__main__":
    create_excels()
