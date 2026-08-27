# Phase 1 Completion Report: University Timetable & Workload Engine

> [!NOTE]
> This document serves as a comprehensive summary of all architectural foundations, API routes, database models, and frontend integration fixes achieved during Phase 1 of the project.

## 1. Backend Foundation & Architecture

We established a robust, highly-performant backend server using **Python FastAPI**. 
- **CORS Configuration**: Fully integrated `CORSMiddleware` to ensure seamless, blockage-free cross-origin communication with your local React frontend.
- **State Management**: Built robust error handling and transaction rollbacks to prevent API crashes during malformed requests.

## 2. Database Design & ORM (SQLAlchemy)

Designed and mapped a fully relational SQLite database (`university_timetable.db`) using SQLAlchemy within [`database.py`](file:///C:/Users/Dhana/.gemini/antigravity-ide/scratch/workload-backend/database.py). 

**Constructed Tables:**
- **`Faculty`**: Stores faculty details (`id`, `name`, `department`).
- **`Room`**: Manages physical spaces (`room_number`, `room_type`, `capacity`).
- **`Syllabus`**: Organizes courses (`course_code`, `course_title`, `course_type`, `category`).
- **`WorkloadConfiguration`**: The persistence layer for the core logic, storing `theory_hours`, `lab_hours`, `total_calculated_hours`, and dynamic `is_overloaded` flags linked to specific faculty members.

## 3. Advanced API Endpoints

We constructed three highly intelligent endpoints in [`main.py`](file:///C:/Users/Dhana/.gemini/antigravity-ide/scratch/workload-backend/main.py):

| Endpoint | Method | Core Functionality |
| :--- | :--- | :--- |
| `/api/admin/faculty-list` | `GET` | Uses a clean `sqlite3` context manager (preventing database locks) to fetch all faculty and attach default dropdown states for the UI. |
| `/api/admin/upload-metadata` | `POST` | An ultra-permissive handler utilizing `pandas` and `io.BytesIO`. It intercepts Excel files, dynamically auto-detects their target tables via column headers, and performs bulk SQLite insertions while gracefully handling single-file payloads without throwing 422 errors. |
| `/api/admin/generate-workload` | `POST` | The mathematical engine. Processes the frontend matrix array, calculates totals, generates limit warnings, and utilizes an Upsert strategy (Update/Insert) to permanently persist the computed configurations into the database. |

## 4. Scripting & Data Seeding

To accelerate testing and development, two utility scripts were created and executed:
- **`seed_faculty.py`**: Automated the injection of 20 fully structured dummy faculty records directly into the SQLite database. (Included a fix for Windows console Unicode encoding errors).
- **`create_test_excels.py`**: Leveraged `pandas` and `openpyxl` to auto-generate four clean, perfectly formatted sample Excel sheets (`syllabus.xlsx`, `faculty_list.xlsx`, `rooms_list.xlsx`, `hours_reference.xlsx`) for testing the upload endpoint.

## 5. Frontend Integration & Bug Squashing

We successfully intercepted and solved complex integration mismatches directly within the React frontend ([`index.tsx`](file:///C:/Users/Dhana/Downloads/workload-frontend/src/routes/index.tsx)):

> [!TIP]
> **The State Mutation Bug Fix**
> We diagnosed a classic React bug where modifying one dropdown overwrote the entire matrix. We implemented a precise `map()` update handler targeting exact row IDs, completely detaching the rows from one another.

> [!IMPORTANT]
> **Data Interface Normalization**
> The backend was emitting `faculty_id` and `department`, while the frontend expected `facultyId` and `dept`. This caused the UI matching logic to fail entirely. We implemented a `mapFaculty` normalizer function to perfectly bridge the schema gap, ensuring successful UI rendering and pristine payload generation.

---

**Phase 1 is officially complete, fully stabilized, and ready for Phase 2!**
