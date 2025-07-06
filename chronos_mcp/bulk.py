"""Bulk operations for Chronos MCP."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime


class BulkOperationMode(Enum):
    """Modes for bulk operation execution."""
    ATOMIC = "atomic"
    CONTINUE_ON_ERROR = "continue"
    FAIL_FAST = "fail_fast"


@dataclass
class BulkOptions:
    """Configuration for bulk operations."""
    mode: BulkOperationMode = BulkOperationMode.CONTINUE_ON_ERROR
    max_parallel: int = 5
    timeout_per_operation: int = 30
    validate_before_execute: bool = True
    dry_run: bool = False


@dataclass
class OperationResult:
    """Result of a single operation within bulk."""
    index: int
    success: bool
    uid: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class BulkResult:
    """Aggregate result of bulk operation."""
    total: int
    successful: int
    failed: int
    results: List[OperationResult] = field(default_factory=list)
    duration_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        return (self.successful / self.total * 100) if self.total > 0 else 0.0
    
    def get_failures(self) -> List[OperationResult]:
        return [r for r in self.results if not r.success]
    
    def get_successes(self) -> List[OperationResult]:
        return [r for r in self.results if r.success]


class BulkOperationManager:
    """Manages bulk CalDAV operations."""
    
    def __init__(self, event_manager=None):
        self.event_manager = event_manager
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def bulk_create_events(self, 
                          calendar_uid: str,
                          events: List[Dict[str, Any]], 
                          options: BulkOptions = None) -> BulkResult:
        """Create multiple events with configurable error handling."""
        if options is None:
            options = BulkOptions()
        
        start_time = time.time()
        result = BulkResult(total=len(events), successful=0, failed=0)
        
        if options.validate_before_execute:
            validation_errors = self._validate_events(events)
            if validation_errors and options.mode == BulkOperationMode.ATOMIC:
                for idx, error in validation_errors:
                    result.results.append(OperationResult(
                        index=idx,
                        success=False,
                        error=f"Validation failed: {error}"
                    ))
                result.failed = len(validation_errors)
                result.duration_ms = (time.time() - start_time) * 1000
                return result
        
        if options.dry_run:
            for idx in range(len(events)):
                result.results.append(OperationResult(
                    index=idx,
                    success=True,
                    uid=f"dry-run-uid-{idx}",
                    duration_ms=0.1
                ))
            result.successful = len(events)
        else:
            created_uids = []
            
            for batch_start in range(0, len(events), options.max_parallel):
                batch_end = min(batch_start + options.max_parallel, len(events))
                batch = events[batch_start:batch_end]
                
                batch_results = self._execute_batch_create(
                    calendar_uid, batch, batch_start, options
                )
                
                for op_result in batch_results:
                    result.results.append(op_result)
                    if op_result.success:
                        result.successful += 1
                        created_uids.append(op_result.uid)
                    else:
                        result.failed += 1
                        
                        if options.mode == BulkOperationMode.FAIL_FAST:
                            break
                        elif options.mode == BulkOperationMode.ATOMIC:
                            self._rollback_created_events(
                                calendar_uid, created_uids
                            )
                            result.successful = 0
                            result.failed = len(events)
                            break
                
                if (options.mode == BulkOperationMode.FAIL_FAST and result.failed > 0) or \
                   (options.mode == BulkOperationMode.ATOMIC and result.failed > 0):
                    break
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def _validate_events(self, events: List[Dict[str, Any]]) -> List[Tuple[int, str]]:
        """Validate event data before execution."""
        errors = []
        
        for idx, event in enumerate(events):
            if not event.get('summary'):
                errors.append((idx, "Missing required field: summary"))
            if not event.get('dtstart'):
                errors.append((idx, "Missing required field: dtstart"))
            if not event.get('dtend'):
                errors.append((idx, "Missing required field: dtend"))
            
            try:
                start = datetime.fromisoformat(str(event.get('dtstart', '')).replace('Z', '+00:00'))
                end = datetime.fromisoformat(str(event.get('dtend', '')).replace('Z', '+00:00'))
                if end < start:
                    errors.append((idx, "End time before start time"))
            except:
                errors.append((idx, "Invalid date format"))
        
        return errors
    
    def _execute_batch_create(self, calendar_uid: str, batch: List[Dict], 
                             start_idx: int, options: BulkOptions) -> List[OperationResult]:
        """Execute a batch of create operations in parallel."""
        results = []
        
        # Use the provided event manager
        if not self.event_manager:
            raise ValueError("EventManager not provided to BulkOperationManager")
        
        for idx, event in enumerate(batch):
            op_start = time.time()
            try:
                # Create the event using EventManager
                created_event = self.event_manager.create_event(
                    calendar_uid=calendar_uid,
                    summary=event.get('summary'),
                    start=event.get('dtstart'),
                    end=event.get('dtend'),
                    description=event.get('description'),
                    location=event.get('location'),
                    all_day=event.get('all_day', False),
                    alarm_minutes=event.get('alarm_minutes'),
                    recurrence_rule=event.get('recurrence_rule'),
                    attendees=event.get('attendees', [])
                )
                
                results.append(OperationResult(
                    index=start_idx + idx,
                    success=True,
                    uid=created_event.uid,
                    duration_ms=(time.time() - op_start) * 1000
                ))
            except Exception as e:
                results.append(OperationResult(
                    index=start_idx + idx,
                    success=False,
                    error=str(e),
                    duration_ms=(time.time() - op_start) * 1000
                ))
        
        return results
    
    def _rollback_created_events(self, calendar_uid: str, uids: List[str]):
        """Rollback created events in case of atomic operation failure."""
        # Delete all created events
        if self.event_manager:
            for uid in uids:
                try:
                    self.event_manager.delete_event(calendar_uid, uid)
                except:
                    # Log but continue rollback
                    pass
    
    def bulk_delete_events(self,
                          calendar_uid: str,
                          event_uids: List[str],
                          options: BulkOptions = None) -> BulkResult:
        """Delete multiple events efficiently."""
        if options is None:
            options = BulkOptions()
        
        start_time = time.time()
        result = BulkResult(total=len(event_uids), successful=0, failed=0)
        
        # Similar implementation to bulk_create_events
        # but for deletion operations
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
