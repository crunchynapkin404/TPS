"""
Core data structures for TPS V1.4 planning services
Based on V1.3.1 planning/orchestrator.py analysis
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class PlanningAlgorithm(Enum):
    """Available planning algorithms"""
    BALANCED = "balanced"  # Equal distribution using fairness scores
    SEQUENTIAL = "sequential"  # Round-robin with constraints
    CUSTOM = "custom"  # Rule-based optimization


class PlanningStatus(Enum):
    """Planning operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ValidationResult:
    """Result of prerequisite validation"""
    success: bool
    message: str
    errors: List[str]
    warnings: List[str]
    checks: Dict[str, Any]


@dataclass
class PlanningResult:
    """Standardized result format for planning operations"""
    success: bool
    message: str
    data: Dict[str, Any]
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: PlanningStatus = PlanningStatus.COMPLETED


@dataclass
class PlanningRequest:
    """Standardized request format for planning operations"""
    team_id: int
    start_date: date
    weeks: int
    algorithm: PlanningAlgorithm = PlanningAlgorithm.BALANCED
    preview_only: bool = True
    force_regenerate: bool = False
    requested_by: Optional[int] = None  # User ID
    
    
@dataclass
class AssignmentCandidate:
    """Represents a potential assignment with scoring"""
    user_id: int
    user_name: str
    shift_id: int
    fairness_score: float
    skill_score: float
    availability_score: float
    total_score: float
    conflicts: List[str]
    

@dataclass
class BulkResult:
    """Result of bulk operations"""
    success: bool
    total_requested: int
    successful: int
    failed: int
    errors: List[str]
    warnings: List[str]
    details: List[Dict[str, Any]]


@dataclass 
class AssignmentResult:
    """Result of assignment operations"""
    success: bool
    message: str
    assignment_id: Optional[int] = None
    conflicts: Optional[List[str]] = None
    suggestions: Optional[List[AssignmentCandidate]] = None
