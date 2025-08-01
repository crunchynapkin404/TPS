"""
TPS Monthly Timeline Shift Scheduler - FastAPI Backend
Production-ready API with SQLite database integration
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import sqlite3
import json
import os
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TPS Monthly Timeline Shift Scheduler",
    description="Production-ready shift scheduling system with perfect pixel alignment",
    version="1.0.0"
)

# Enable CORS for all origins (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DATABASE_URL = "scheduler.db"

# Initialize database
def init_database():
    """Initialize the database with schema if it doesn't exist"""
    if not os.path.exists(DATABASE_URL):
        with sqlite3.connect(DATABASE_URL) as conn:
            with open("database_schema.sql", "r") as f:
                conn.executescript(f.read())
        logger.info("Database initialized with schema")

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    try:
        yield conn
    finally:
        conn.close()

# Pydantic models for request/response
class UserResponse(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    avatar_url: Optional[str] = None
    department: str
    role: str
    is_active: bool

class ShiftTypeResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    color: str
    duration_hours: float
    requires_handover: bool
    max_per_day: int
    overtime_threshold: float
    is_active: bool

class ShiftRequest(BaseModel):
    user_id: int
    shift_type_id: int
    date: date
    start_time: time
    end_time: time
    notes: Optional[str] = None
    status: str = "scheduled"

class ShiftResponse(BaseModel):
    id: int
    user_id: int
    shift_type_id: int
    date: date
    start_time: time
    end_time: time
    duration_hours: float
    is_overtime: bool
    status: str
    notes: Optional[str] = None
    template_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    # Related objects
    user: Optional[UserResponse] = None
    shift_type: Optional[ShiftTypeResponse] = None

class ShiftUpdateRequest(BaseModel):
    user_id: Optional[int] = None
    shift_type_id: Optional[int] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class BulkShiftRequest(BaseModel):
    shifts: List[ShiftRequest]
    template_id: Optional[int] = None

class ShiftTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    shift_type_id: int
    start_time: time
    end_time: time
    days_of_week: List[int]  # 1=Monday, 7=Sunday
    recurrence_pattern: str = "weekly"

class ScheduleResponse(BaseModel):
    year: int
    month: int
    days_in_month: int
    shifts: List[ShiftResponse]
    users: List[UserResponse]
    shift_types: List[ShiftTypeResponse]
    conflicts: List[Dict[str, Any]] = []
    coverage_gaps: List[Dict[str, Any]] = []

# Utility functions
def calculate_duration(start_time: time, end_time: time) -> float:
    """Calculate duration in hours between start and end time"""
    start_dt = datetime.combine(date.today(), start_time)
    end_dt = datetime.combine(date.today(), end_time)
    
    # Handle overnight shifts
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    
    duration = (end_dt - start_dt).total_seconds() / 3600
    return round(duration, 2)

def row_to_dict(row) -> dict:
    """Convert sqlite3.Row to dictionary"""
    return dict(row) if row else None

def rows_to_dicts(rows) -> List[dict]:
    """Convert list of sqlite3.Row to list of dictionaries"""
    return [dict(row) for row in rows]

# API Endpoints

# Initialize database on module load
init_database()

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "TPS Monthly Timeline Shift Scheduler API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/users", response_model=List[UserResponse])
async def get_users():
    """Get all active users"""
    with get_db_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM users 
            WHERE is_active = 1 
            ORDER BY first_name, last_name
        """)
        users = rows_to_dicts(cursor.fetchall())
    return users

@app.get("/api/shift-types", response_model=List[ShiftTypeResponse])
async def get_shift_types():
    """Get all active shift types"""
    with get_db_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM shift_types 
            WHERE is_active = 1 
            ORDER BY name
        """)
        shift_types = rows_to_dicts(cursor.fetchall())
    return shift_types

@app.get("/api/schedule/{year}/{month}", response_model=ScheduleResponse)
async def get_schedule(
    year: int = Path(..., ge=2020, le=2030),
    month: int = Path(..., ge=1, le=12)
):
    """Get complete schedule for a specific month"""
    # Calculate date range for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    days_in_month = end_date.day
    
    with get_db_connection() as conn:
        # Get shifts for the month with related data
        cursor = conn.execute("""
            SELECT s.*, 
                   u.username, u.first_name, u.last_name, u.email, u.avatar_url, u.department, u.role,
                   st.name as shift_type_name, st.display_name as shift_display_name, 
                   st.color as shift_color, st.requires_handover
            FROM shifts s
            JOIN users u ON s.user_id = u.id
            JOIN shift_types st ON s.shift_type_id = st.id
            WHERE s.date BETWEEN ? AND ?
            ORDER BY s.date, s.start_time, u.first_name
        """, (start_date, end_date))
        
        raw_shifts = cursor.fetchall()
        
        # Transform shifts with related objects
        shifts = []
        for row in raw_shifts:
            shift_dict = dict(row)
            
            # Extract user data
            user_data = {
                'id': shift_dict['user_id'],
                'username': shift_dict['username'],
                'first_name': shift_dict['first_name'],
                'last_name': shift_dict['last_name'],
                'email': shift_dict['email'],
                'avatar_url': shift_dict['avatar_url'],
                'department': shift_dict['department'],
                'role': shift_dict['role'],
                'is_active': True
            }
            
            # Extract shift type data
            shift_type_data = {
                'id': shift_dict['shift_type_id'],
                'name': shift_dict['shift_type_name'],
                'display_name': shift_dict['shift_display_name'],
                'color': shift_dict['shift_color'],
                'requires_handover': shift_dict['requires_handover'],
                'duration_hours': shift_dict['duration_hours'],
                'max_per_day': 1,
                'overtime_threshold': 8.0,
                'is_active': True,
                'description': None
            }
            
            # Clean shift data
            shift_data = {
                'id': shift_dict['id'],
                'user_id': shift_dict['user_id'],
                'shift_type_id': shift_dict['shift_type_id'],
                'date': shift_dict['date'],
                'start_time': shift_dict['start_time'],
                'end_time': shift_dict['end_time'],
                'duration_hours': shift_dict['duration_hours'],
                'is_overtime': shift_dict['is_overtime'],
                'status': shift_dict['status'],
                'notes': shift_dict['notes'],
                'template_id': shift_dict['template_id'],
                'created_at': shift_dict['created_at'],
                'updated_at': shift_dict['updated_at'],
                'user': user_data,
                'shift_type': shift_type_data
            }
            
            shifts.append(shift_data)
        
        # Get all users
        cursor = conn.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY first_name, last_name")
        users = rows_to_dicts(cursor.fetchall())
        
        # Get all shift types
        cursor = conn.execute("SELECT * FROM shift_types WHERE is_active = 1 ORDER BY name")
        shift_types = rows_to_dicts(cursor.fetchall())
    
    return {
        'year': year,
        'month': month,
        'days_in_month': days_in_month,
        'shifts': shifts,
        'users': users,
        'shift_types': shift_types,
        'conflicts': [],  # TODO: Implement conflict detection
        'coverage_gaps': []  # TODO: Implement coverage gap detection
    }

@app.post("/api/shifts", response_model=ShiftResponse)
async def create_shift(shift: ShiftRequest):
    """Create a new shift"""
    # Calculate duration
    duration = calculate_duration(shift.start_time, shift.end_time)
    is_overtime = duration > 8.0
    
    with get_db_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO shifts (user_id, shift_type_id, date, start_time, end_time, 
                              duration_hours, is_overtime, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            shift.user_id, shift.shift_type_id, str(shift.date), 
            str(shift.start_time), str(shift.end_time), duration, is_overtime,
            shift.status, shift.notes
        ))
        
        shift_id = cursor.lastrowid
        conn.commit()
        
        # Get the created shift with related data
        cursor = conn.execute("""
            SELECT s.*, 
                   u.username, u.first_name, u.last_name, u.email, u.avatar_url, u.department, u.role,
                   st.name as shift_type_name, st.display_name as shift_display_name, 
                   st.color as shift_color, st.requires_handover
            FROM shifts s
            JOIN users u ON s.user_id = u.id
            JOIN shift_types st ON s.shift_type_id = st.id
            WHERE s.id = ?
        """, (shift_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Shift not found after creation")
        
        # Transform the data similar to get_schedule
        shift_dict = dict(row)
        result = {
            'id': shift_dict['id'],
            'user_id': shift_dict['user_id'],
            'shift_type_id': shift_dict['shift_type_id'],
            'date': shift_dict['date'],
            'start_time': shift_dict['start_time'],
            'end_time': shift_dict['end_time'],
            'duration_hours': shift_dict['duration_hours'],
            'is_overtime': shift_dict['is_overtime'],
            'status': shift_dict['status'],
            'notes': shift_dict['notes'],
            'template_id': shift_dict['template_id'],
            'created_at': shift_dict['created_at'],
            'updated_at': shift_dict['updated_at']
        }
    
    return result

@app.put("/api/shifts/{shift_id}", response_model=ShiftResponse)
async def update_shift(shift_id: int, shift_update: ShiftUpdateRequest):
    """Update an existing shift"""
    with get_db_connection() as conn:
        # Check if shift exists
        cursor = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,))
        existing_shift = cursor.fetchone()
        if not existing_shift:
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Build update query dynamically
        updates = []
        params = []
        
        if shift_update.user_id is not None:
            updates.append("user_id = ?")
            params.append(shift_update.user_id)
        
        if shift_update.shift_type_id is not None:
            updates.append("shift_type_id = ?")
            params.append(shift_update.shift_type_id)
        
        if shift_update.date is not None:
            updates.append("date = ?")
            params.append(str(shift_update.date))
        
        if shift_update.start_time is not None:
            updates.append("start_time = ?")
            params.append(str(shift_update.start_time))
        
        if shift_update.end_time is not None:
            updates.append("end_time = ?")
            params.append(str(shift_update.end_time))
        
        if shift_update.notes is not None:
            updates.append("notes = ?")
            params.append(shift_update.notes)
        
        if shift_update.status is not None:
            updates.append("status = ?")
            params.append(shift_update.status)
        
        # Recalculate duration if times changed
        if shift_update.start_time is not None or shift_update.end_time is not None:
            start_time = shift_update.start_time or existing_shift['start_time']
            end_time = shift_update.end_time or existing_shift['end_time']
            duration = calculate_duration(start_time, end_time)
            is_overtime = duration > 8.0
            
            updates.extend(["duration_hours = ?", "is_overtime = ?"])
            params.extend([duration, is_overtime])
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(shift_id)
            
            query = f"UPDATE shifts SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, params)
            conn.commit()
        
        # Return updated shift
        cursor = conn.execute("""
            SELECT s.*, 
                   u.username, u.first_name, u.last_name, u.email, u.avatar_url, u.department, u.role,
                   st.name as shift_type_name, st.display_name as shift_display_name, 
                   st.color as shift_color, st.requires_handover
            FROM shifts s
            JOIN users u ON s.user_id = u.id
            JOIN shift_types st ON s.shift_type_id = st.id
            WHERE s.id = ?
        """, (shift_id,))
        
        row = cursor.fetchone()
        shift_dict = dict(row)
        
        result = {
            'id': shift_dict['id'],
            'user_id': shift_dict['user_id'],
            'shift_type_id': shift_dict['shift_type_id'],
            'date': shift_dict['date'],
            'start_time': shift_dict['start_time'],
            'end_time': shift_dict['end_time'],
            'duration_hours': shift_dict['duration_hours'],
            'is_overtime': shift_dict['is_overtime'],
            'status': shift_dict['status'],
            'notes': shift_dict['notes'],
            'template_id': shift_dict['template_id'],
            'created_at': shift_dict['created_at'],
            'updated_at': shift_dict['updated_at']
        }
    
    return result

@app.delete("/api/shifts/{shift_id}")
async def delete_shift(shift_id: int):
    """Delete a shift"""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT id FROM shifts WHERE id = ?", (shift_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Shift not found")
        
        conn.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
        conn.commit()
    
    return {"message": "Shift deleted successfully"}

@app.post("/api/shifts/bulk", response_model=List[ShiftResponse])
async def create_bulk_shifts(bulk_request: BulkShiftRequest):
    """Create multiple shifts at once"""
    created_shifts = []
    
    with get_db_connection() as conn:
        for shift in bulk_request.shifts:
            duration = calculate_duration(shift.start_time, shift.end_time)
            is_overtime = duration > 8.0
            
            cursor = conn.execute("""
                INSERT INTO shifts (user_id, shift_type_id, date, start_time, end_time, 
                                  duration_hours, is_overtime, status, notes, template_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                shift.user_id, shift.shift_type_id, str(shift.date), 
                str(shift.start_time), str(shift.end_time), duration, is_overtime,
                shift.status, shift.notes, bulk_request.template_id
            ))
            
            shift_id = cursor.lastrowid
            created_shifts.append({
                'id': shift_id,
                'user_id': shift.user_id,
                'shift_type_id': shift.shift_type_id,
                'date': shift.date,
                'start_time': shift.start_time,
                'end_time': shift.end_time,
                'duration_hours': duration,
                'is_overtime': is_overtime,
                'status': shift.status,
                'notes': shift.notes,
                'template_id': bulk_request.template_id,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
        
        conn.commit()
    
    return created_shifts

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    # Initialize database when running directly
    init_database()
    uvicorn.run("scheduler_api:app", host="0.0.0.0", port=8000, reload=True)