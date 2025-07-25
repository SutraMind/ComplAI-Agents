"""
Progress tracking and status reporting for multi-agent compliance analysis.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum


class AnalysisStage(Enum):
    """Enumeration for analysis stages."""
    INITIALIZATION = "initialization"
    DOCUMENT_PROCESSING = "document_processing"
    CC_AGENT_1_ANALYSIS = "cc_agent_1_analysis"
    CC_AGENT_2_ANALYSIS = "cc_agent_2_analysis"
    RA_AGENT_ASSESSMENT = "ra_agent_assessment"
    FEEDBACK_GENERATION = "feedback_generation"
    FEEDBACK_PROCESSING = "feedback_processing"
    CONSOLIDATION = "consolidation"
    COMPLETION = "completion"


@dataclass
class StageProgress:
    """Represents progress information for a single stage."""
    stage: AnalysisStage
    status: str  # "pending", "running", "completed", "failed"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress_percentage: float = 0.0
    details: str = ""
    error: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of this stage in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None
    
    def start(self, details: str = "") -> None:
        """Start this stage."""
        self.status = "running"
        self.start_time = datetime.now()
        self.details = details
        self.progress_percentage = 0.0
    
    def update_progress(self, percentage: float, details: str = "") -> None:
        """Update progress for this stage."""
        self.progress_percentage = min(100.0, max(0.0, percentage))
        if details:
            self.details = details
    
    def complete(self, details: str = "") -> None:
        """Mark this stage as completed."""
        self.status = "completed"
        self.end_time = datetime.now()
        self.progress_percentage = 100.0
        if details:
            self.details = details
    
    def fail(self, error: str, details: str = "") -> None:
        """Mark this stage as failed."""
        self.status = "failed"
        self.end_time = datetime.now()
        self.error = error
        if details:
            self.details = details


@dataclass
class ProgressTracker:
    """
    Tracks progress and provides status reporting for multi-agent compliance analysis.
    
    This class provides real-time progress updates, stage tracking, and performance
    monitoring for the entire analysis workflow.
    """
    
    # Progress tracking
    stages: Dict[AnalysisStage, StageProgress] = field(default_factory=dict)
    current_stage: Optional[AnalysisStage] = None
    overall_progress: float = 0.0
    
    # Timing
    start_time: Optional[datetime] = None
    estimated_completion_time: Optional[datetime] = None
    
    # Callbacks for progress updates
    progress_callbacks: List[Callable[[Dict[str, Any]], None]] = field(default_factory=list)
    
    # Stage weights for overall progress calculation
    stage_weights: Dict[AnalysisStage, float] = field(default_factory=lambda: {
        AnalysisStage.INITIALIZATION: 5.0,
        AnalysisStage.DOCUMENT_PROCESSING: 10.0,
        AnalysisStage.CC_AGENT_1_ANALYSIS: 25.0,
        AnalysisStage.CC_AGENT_2_ANALYSIS: 25.0,
        AnalysisStage.RA_AGENT_ASSESSMENT: 20.0,
        AnalysisStage.FEEDBACK_GENERATION: 5.0,
        AnalysisStage.FEEDBACK_PROCESSING: 5.0,
        AnalysisStage.CONSOLIDATION: 3.0,
        AnalysisStage.COMPLETION: 2.0
    })
    
    def __post_init__(self):
        """Initialize all stages."""
        for stage in AnalysisStage:
            self.stages[stage] = StageProgress(stage=stage, status="pending")
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a callback function to be called on progress updates."""
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a progress callback."""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def start_analysis(self) -> None:
        """Start the overall analysis tracking."""
        self.start_time = datetime.now()
        self.overall_progress = 0.0
        self._notify_progress_update()
    
    def start_stage(self, stage: AnalysisStage, details: str = "") -> None:
        """Start a specific analysis stage."""
        self.current_stage = stage
        self.stages[stage].start(details)
        self._update_overall_progress()
        self._notify_progress_update()
    
    def update_stage_progress(self, stage: AnalysisStage, percentage: float, details: str = "") -> None:
        """Update progress for a specific stage."""
        if stage in self.stages:
            self.stages[stage].update_progress(percentage, details)
            self._update_overall_progress()
            self._notify_progress_update()
    
    def complete_stage(self, stage: AnalysisStage, details: str = "") -> None:
        """Mark a stage as completed."""
        if stage in self.stages:
            self.stages[stage].complete(details)
            self._update_overall_progress()
            self._notify_progress_update()
    
    def fail_stage(self, stage: AnalysisStage, error: str, details: str = "") -> None:
        """Mark a stage as failed."""
        if stage in self.stages:
            self.stages[stage].fail(error, details)
            self._notify_progress_update()
    
    def complete_analysis(self) -> None:
        """Mark the overall analysis as completed."""
        if self.current_stage != AnalysisStage.COMPLETION:
            self.start_stage(AnalysisStage.COMPLETION, "Analysis completed successfully")
            self.complete_stage(AnalysisStage.COMPLETION)
        self.overall_progress = 100.0
        self._notify_progress_update()
    
    def _update_overall_progress(self) -> None:
        """Update the overall progress based on stage progress."""
        total_progress = 0.0
        total_weight = sum(self.stage_weights.values())
        
        for stage, stage_progress in self.stages.items():
            weight = self.stage_weights.get(stage, 0.0)
            stage_percentage = stage_progress.progress_percentage
            
            # Completed stages contribute full weight
            if stage_progress.status == "completed":
                stage_percentage = 100.0
            # Running stages contribute their current progress
            elif stage_progress.status == "running":
                stage_percentage = max(stage_percentage, 1.0)  # Minimum 1% for running stages
            
            total_progress += (stage_percentage / 100.0) * weight
        
        self.overall_progress = (total_progress / total_weight) * 100.0
        
        # Update estimated completion time
        self._update_estimated_completion()
    
    def _update_estimated_completion(self) -> None:
        """Update estimated completion time based on current progress."""
        if not self.start_time or self.overall_progress <= 0:
            return
        
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        if self.overall_progress > 0:
            estimated_total_time = elapsed_time * (100.0 / self.overall_progress)
            remaining_time = estimated_total_time - elapsed_time
            
            if remaining_time > 0:
                self.estimated_completion_time = datetime.now() + \
                    timedelta(seconds=remaining_time)
    
    def _notify_progress_update(self) -> None:
        """Notify all registered callbacks of progress update."""
        progress_data = self.get_progress_summary()
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                # Log error but don't fail the analysis
                print(f"Progress callback error: {e}")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of current progress."""
        return {
            "overall_progress": round(self.overall_progress, 1),
            "current_stage": self.current_stage.value if self.current_stage else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "estimated_completion": self.estimated_completion_time.isoformat() 
                if self.estimated_completion_time else None,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds() 
                if self.start_time else 0,
            "stages": {
                stage.value: {
                    "status": progress.status,
                    "progress": round(progress.progress_percentage, 1),
                    "details": progress.details,
                    "duration": progress.duration,
                    "error": progress.error
                }
                for stage, progress in self.stages.items()
            }
        }
    
    def get_detailed_progress(self) -> Dict[str, Any]:
        """Get detailed progress information."""
        summary = self.get_progress_summary()
        
        # Add performance metrics
        completed_stages = [s for s in self.stages.values() if s.status == "completed"]
        failed_stages = [s for s in self.stages.values() if s.status == "failed"]
        
        summary.update({
            "performance_metrics": {
                "completed_stages": len(completed_stages),
                "failed_stages": len(failed_stages),
                "average_stage_duration": sum(s.duration for s in completed_stages if s.duration) / 
                    len(completed_stages) if completed_stages else 0,
                "total_elapsed_time": (datetime.now() - self.start_time).total_seconds() 
                    if self.start_time else 0
            },
            "stage_details": {
                stage.value: {
                    "status": progress.status,
                    "progress": progress.progress_percentage,
                    "details": progress.details,
                    "start_time": progress.start_time.isoformat() if progress.start_time else None,
                    "end_time": progress.end_time.isoformat() if progress.end_time else None,
                    "duration": progress.duration,
                    "error": progress.error,
                    "weight": self.stage_weights.get(stage, 0.0)
                }
                for stage, progress in self.stages.items()
            }
        })
        
        return summary
    
    def is_completed(self) -> bool:
        """Check if the analysis is completed."""
        return self.overall_progress >= 100.0
    
    def has_failed_stages(self) -> bool:
        """Check if any stages have failed."""
        return any(stage.status == "failed" for stage in self.stages.values())
    
    def get_failed_stages(self) -> List[StageProgress]:
        """Get all failed stages."""
        return [stage for stage in self.stages.values() if stage.status == "failed"]
    
    def get_active_stage(self) -> Optional[StageProgress]:
        """Get the currently active stage."""
        if self.current_stage:
            return self.stages.get(self.current_stage)
        return None
    
    def reset(self) -> None:
        """Reset the progress tracker."""
        self.__post_init__()
        self.current_stage = None
        self.overall_progress = 0.0
        self.start_time = None
        self.estimated_completion_time = None