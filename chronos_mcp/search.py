"""Event search functionality for Chronos MCP."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import re
import time


@dataclass
class SearchOptions:
    """Options for event search functionality."""
    query: str
    fields: List[str]
    case_sensitive: bool = False
    match_type: str = 'contains'
    use_regex: bool = False
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    max_results: Optional[int] = None
    
    def __post_init__(self):
        valid_types = ['contains', 'starts_with', 'ends_with', 'exact', 'regex']
        if self.match_type not in valid_types:
            raise ValueError(f"match_type must be one of {valid_types}")
        
        if not self.fields:
            self.fields = ['summary', 'description', 'location']
        
        if self.use_regex or self.match_type == 'regex':
            flags = 0 if self.case_sensitive else re.IGNORECASE
            self.pattern = re.compile(self.query, flags)


def search_events(events: List[Dict[str, Any]], options: SearchOptions) -> List[Dict[str, Any]]:
    """Search events based on provided options."""
    if not options.query and not (options.date_start or options.date_end):
        return events
    
    def matches_text(event: Dict[str, Any]) -> bool:
        if not options.query:
            return True
            
        for field in options.fields:
            value = event.get(field, '')
            if value is None:
                continue
                
            value_str = str(value)
            
            if not options.case_sensitive:
                value_str = value_str.lower()
                query = options.query.lower()
            else:
                query = options.query
            
            if options.use_regex or options.match_type == 'regex':
                if options.pattern.search(value_str):
                    return True
            elif options.match_type == 'contains':
                if query in value_str:
                    return True
            elif options.match_type == 'starts_with':
                if value_str.startswith(query):
                    return True
            elif options.match_type == 'ends_with':
                if value_str.endswith(query):
                    return True
            elif options.match_type == 'exact':
                if value_str == query:
                    return True
        
        return False
    
    def matches_date(event: Dict[str, Any]) -> bool:
        if not (options.date_start or options.date_end):
            return True
            
        event_start = event.get('dtstart')
        if not event_start:
            return False
            
        if isinstance(event_start, str):
            event_start = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
        
        if options.date_start and event_start < options.date_start:
            return False
        if options.date_end and event_start > options.date_end:
            return False
            
        return True
    
    results = [
        event for event in events
        if matches_text(event) and matches_date(event)
    ]
    
    if options.max_results:
        results = results[:options.max_results]
    
    return results


def calculate_relevance_score(event: Dict[str, Any], 
                            options: SearchOptions,
                            current_time: datetime = None) -> float:
    """Calculate relevance score for search ranking."""
    if current_time is None:
        current_time = datetime.now()
    
    score = 0.0
    query = options.query.lower() if not options.case_sensitive else options.query
    
    field_weights = {
        'summary': 3.0,
        'description': 2.0,
        'location': 1.0
    }
    
    for field in options.fields:
        if field not in field_weights:
            continue
            
        value = event.get(field, '')
        if not value:
            continue
            
        value_str = str(value)
        if not options.case_sensitive:
            value_str = value_str.lower()
        
        field_score = 0.0
        
        if options.use_regex or options.match_type == 'regex':
            matches = list(options.pattern.finditer(value_str))
            if matches:
                field_score = 2.0 * len(matches)
                first_match_pos = matches[0].start()
                position_factor = 1.0 - (first_match_pos / max(len(value_str), 1))
                field_score *= (1.0 + position_factor * 0.5)
        else:
            if options.match_type == 'exact' and value_str == query:
                field_score = 5.0
            elif options.match_type == 'starts_with' and value_str.startswith(query):
                field_score = 3.0
            elif options.match_type == 'contains' or query in value_str:
                occurrences = value_str.count(query)
                if occurrences > 0:
                    field_score = 1.0 * occurrences
                    first_pos = value_str.find(query)
                    position_factor = 1.0 - (first_pos / max(len(value_str), 1))
                    field_score *= (1.0 + position_factor * 0.5)
        
        score += field_score * field_weights.get(field, 1.0)
    
    # Recency boost
    event_start = event.get('dtstart')
    if event_start:
        if isinstance(event_start, str):
            event_start = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
        
        days_diff = abs((current_time - event_start).days)
        if days_diff <= 30:
            recency_boost = 0.1 * (1.0 - days_diff / 30.0)
            score *= (1.0 + recency_boost)
    
    return score


def search_events_ranked(events: List[Dict[str, Any]], 
                        options: SearchOptions) -> List[Tuple[Dict[str, Any], float]]:
    """Search events and return them with relevance scores."""
    matching_events = search_events(events, options)
    
    scored_events = []
    for event in matching_events:
        score = calculate_relevance_score(event, options)
        scored_events.append((event, score))
    
    scored_events.sort(key=lambda x: x[1], reverse=True)
    
    if options.max_results:
        scored_events = scored_events[:options.max_results]
    
    return scored_events
