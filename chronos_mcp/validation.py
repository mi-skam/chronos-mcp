"""Input validation for Chronos MCP."""

import re
import html
from typing import Dict, List, Any, Optional, Tuple
import unicodedata
from datetime import datetime

from .exceptions import ValidationError, AccountAlreadyExistsError


class InputValidator:
    """Comprehensive input validation for CalDAV operations."""
    
    MAX_LENGTHS = {
        'summary': 255,
        'description': 5000,
        'location': 255,
        'uid': 255,
        'attendee_email': 254,
        'url': 2048,
        'alias': 50,
        'calendar_name': 100
    }
    
    PATTERNS = {
        'uid': re.compile(r'^[a-zA-Z0-9\-_.@]+$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'url': re.compile(r'^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+(?:/.*)?$'),
        'color': re.compile(r'^#[0-9A-Fa-f]{6}$'),
    }
    
    DANGEROUS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<script\s+[^>]*>', re.IGNORECASE),
        re.compile(r'(?:href|src)\s*=\s*["\']?\s*javascript:', re.IGNORECASE),
        re.compile(r'\bon\w+\s*=\s*["\']', re.IGNORECASE),
        re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]'),
        re.compile(r'<iframe[^>]+src[^>]*>', re.IGNORECASE),
        re.compile(r'<(?:object|embed)[^>]+(?:code|classid|data)[^>]*>', re.IGNORECASE),
    ]
    
    @classmethod
    def validate_event(cls, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize event data."""
        sanitized = {}
        
        if not event_data.get('summary'):
            raise ValidationError("Event summary is required")
        if not event_data.get('dtstart'):
            raise ValidationError("Event start time is required")
        if not event_data.get('dtend'):
            raise ValidationError("Event end time is required")
        
        sanitized['summary'] = cls.validate_text_field(
            event_data['summary'], 'summary', required=True
        )
        
        if 'description' in event_data:
            sanitized['description'] = cls.validate_text_field(
                event_data['description'], 'description'
            )
        
        if 'location' in event_data:
            sanitized['location'] = cls.validate_text_field(
                event_data['location'], 'location'
            )
        
        sanitized['dtstart'] = cls.validate_datetime(event_data['dtstart'], 'dtstart')
        sanitized['dtend'] = cls.validate_datetime(event_data['dtend'], 'dtend')
        
        if sanitized['dtend'] <= sanitized['dtstart']:
            raise ValidationError("Event end time must be after start time")
        
        if 'uid' in event_data:
            sanitized['uid'] = cls.validate_uid(event_data['uid'])
        
        if 'attendees' in event_data:
            sanitized['attendees'] = cls.validate_attendees(event_data['attendees'])
        
        if 'recurrence_rule' in event_data:
            sanitized['recurrence_rule'] = cls.validate_rrule(event_data['recurrence_rule'])
        
        return sanitized
    
    @classmethod
    def validate_text_field(cls, value: str, field_name: str, 
                          required: bool = False) -> str:
        """Validate and sanitize text fields."""
        if not value and required:
            raise ValidationError(f"{field_name} is required")
        
        if not value:
            return ""
        
        value = str(value).strip()
        
        max_length = cls.MAX_LENGTHS.get(field_name, 1000)
        if len(value) > max_length:
            raise ValidationError(
                f"{field_name} exceeds maximum length of {max_length} characters"
            )
        
        # Check for dangerous patterns (XSS, injection)
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(value):
                raise ValidationError(
                    f"{field_name} contains potentially dangerous content"
                )
        
        # Normalize Unicode
        value = unicodedata.normalize('NFKC', value)
        
        # NOTE: HTML escaping removed - should happen at display layer, not storage
        # CalDAV expects unescaped data
        
        return value
    
    @classmethod
    def validate_datetime(cls, value: Any, field_name: str) -> datetime:
        """Validate datetime values."""
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                cleaned = value.replace('Z', '+00:00')
                return datetime.fromisoformat(cleaned)
            except ValueError:
                raise ValidationError(f"Invalid datetime format for {field_name}")
        
        raise ValidationError(f"{field_name} must be a datetime or ISO format string")
    
    @classmethod
    def validate_uid(cls, uid: str) -> str:
        """Validate UID format."""
        if not uid:
            raise ValidationError("UID cannot be empty")
        
        if len(uid) > cls.MAX_LENGTHS['uid']:
            raise ValidationError(f"UID exceeds maximum length of {cls.MAX_LENGTHS['uid']}")
        
        if not cls.PATTERNS['uid'].match(uid):
            raise ValidationError(
                "UID contains invalid characters. "
                "Only alphanumeric, dash, underscore, dot, and @ are allowed"
            )
        
        return uid
    
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email address."""
        email = email.strip().lower()
        
        if len(email) > cls.MAX_LENGTHS['attendee_email']:
            raise ValidationError("Email address too long")
        
        if not cls.PATTERNS['email'].match(email):
            raise ValidationError(f"Invalid email address format: {email}")
        
        return email
    
    @classmethod
    def validate_attendees(cls, attendees: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate attendee list."""
        if not isinstance(attendees, list):
            raise ValidationError("Attendees must be a list")
            
        validated = []
        
        for attendee in attendees:
            if not isinstance(attendee, dict):
                raise ValidationError("Each attendee must be a dictionary")
            
            if 'email' not in attendee:
                raise ValidationError("Attendee email is required")
            
            validated_attendee = {
                'email': cls.validate_email(attendee['email'])
            }
            
            if 'name' in attendee:
                validated_attendee['name'] = cls.validate_text_field(
                    attendee['name'], 'attendee_name'
                )
            
            # Preserve other attendee fields
            for field in ['role', 'status', 'rsvp']:
                if field in attendee:
                    if field == 'role':
                        # Validate role
                        valid_roles = ['CHAIR', 'REQ-PARTICIPANT', 'OPT-PARTICIPANT', 'NON-PARTICIPANT']
                        if attendee[field] not in valid_roles:
                            raise ValidationError(f"Invalid attendee role: {attendee[field]}")
                    validated_attendee[field] = attendee[field]
            
            validated.append(validated_attendee)
        
        return validated
    
    @classmethod
    def validate_rrule(cls, rrule: str) -> str:
        """Validate recurrence rule."""
        rrule = rrule.strip().upper()
        
        if not rrule.startswith('FREQ='):
            raise ValidationError("RRULE must start with FREQ=")
        
        valid_freqs = ['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY']
        freq_match = re.match(r'FREQ=(\w+)', rrule)
        if not freq_match or freq_match.group(1) not in valid_freqs:
            raise ValidationError(f"Invalid frequency. Must be one of: {valid_freqs}")
        
        if len(rrule) > 500:
            raise ValidationError("RRULE too complex (exceeds 500 characters)")
        
        return rrule
