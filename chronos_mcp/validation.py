"""Input validation for Chronos MCP."""

import re
import html
from typing import Dict, List, Any, Optional, Tuple
import unicodedata
from datetime import datetime

from .exceptions import ValidationError, AccountAlreadyExistsError
from .models import TaskStatus


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
        # Script tags (various forms)
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<script\s+[^>]*>', re.IGNORECASE),
        re.compile(r'<\s*script[^>]*>', re.IGNORECASE),
        
        # JavaScript protocols
        re.compile(r'(?:href|src|action|formaction|data)\s*=\s*["\']?\s*javascript:', re.IGNORECASE),
        re.compile(r'javascript\s*:', re.IGNORECASE),
        
        # Event handlers
        re.compile(r'\bon\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE),
        re.compile(r'\bon\w+\s*=\s*[^"\'\s>]+', re.IGNORECASE),
        
        # Data URIs with script content
        re.compile(r'data\s*:\s*[^;]*;\s*base64', re.IGNORECASE),
        re.compile(r'data\s*:\s*text/html', re.IGNORECASE),
        
        # Control characters
        re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]'),
        
        # Dangerous HTML elements
        re.compile(r'<(?:iframe|frame|object|embed|applet|form)[^>]*>', re.IGNORECASE),
        re.compile(r'<(?:meta|link)[^>]+(?:http-equiv|rel)[^>]*>', re.IGNORECASE),
        
        # Expression and eval patterns
        re.compile(r'expression\s*\(', re.IGNORECASE),
        re.compile(r'eval\s*\(', re.IGNORECASE),
        re.compile(r'setTimeout\s*\(', re.IGNORECASE),
        re.compile(r'setInterval\s*\(', re.IGNORECASE),
        
        # Encoded/obfuscated patterns
        re.compile(r'&#[xX]?[0-9a-fA-F]+;'),
        re.compile(r'%[0-9a-fA-F]{2}'),
        re.compile(r'\\u[0-9a-fA-F]{4}', re.IGNORECASE),
        
        # CSS injection patterns
        re.compile(r'@import', re.IGNORECASE),
        re.compile(r'url\s*\(\s*["\']?\s*javascript:', re.IGNORECASE),
        
        # SVG XSS patterns
        re.compile(r'<svg[^>]*>', re.IGNORECASE),
        re.compile(r'<foreignobject[^>]*>', re.IGNORECASE),
        
        # Special protocol handlers
        re.compile(r'(?:vbscript|mocha|livescript|data):', re.IGNORECASE),
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
    def _decode_and_normalize(cls, value: str) -> str:
        """Decode and normalize potentially obfuscated content for pattern matching"""
        import urllib.parse
        
        # Create a copy for testing (don't modify original)
        test_value = value
        
        # Decode common encodings
        try:
            # HTML entities
            import html
            test_value = html.unescape(test_value)
            
            # URL encoding  
            test_value = urllib.parse.unquote(test_value)
            
            # Unicode escapes
            test_value = test_value.encode().decode('unicode_escape', errors='ignore')
            
        except Exception:
            # If decoding fails, use original value
            test_value = value
        
        return test_value
    
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
        
        # Normalize Unicode
        value = unicodedata.normalize('NFKC', value)
        
        # Check for dangerous patterns on both original and decoded versions
        test_values = [value, cls._decode_and_normalize(value)]
        
        for test_val in test_values:
            for pattern in cls.DANGEROUS_PATTERNS:
                if pattern.search(test_val):
                    raise ValidationError(
                        f"{field_name} contains potentially dangerous content"
                    )
        
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
    
    @classmethod
    def validate_task(cls, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize task data."""
        sanitized = {}
        
        if not task_data.get('summary'):
            raise ValidationError("Task summary is required")
        
        sanitized['summary'] = cls.validate_text_field(
            task_data['summary'], 'summary', required=True
        )
        
        if 'description' in task_data:
            sanitized['description'] = cls.validate_text_field(
                task_data['description'], 'description'
            )
        
        if 'due' in task_data and task_data['due'] is not None:
            sanitized['due'] = cls.validate_datetime(task_data['due'], 'due')
        
        if 'priority' in task_data and task_data['priority'] is not None:
            sanitized['priority'] = cls.validate_priority(task_data['priority'])
        
        if 'status' in task_data and task_data['status'] is not None:
            sanitized['status'] = cls.validate_task_status(task_data['status'])
        
        if 'percent_complete' in task_data and task_data['percent_complete'] is not None:
            sanitized['percent_complete'] = cls.validate_percent_complete(task_data['percent_complete'])
        
        if 'uid' in task_data:
            sanitized['uid'] = cls.validate_uid(task_data['uid'])
            
        if 'related_to' in task_data:
            sanitized['related_to'] = cls.validate_related_to(task_data['related_to'])
        
        return sanitized
    
    @classmethod
    def validate_journal(cls, journal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize journal data."""
        sanitized = {}
        
        if not journal_data.get('summary'):
            raise ValidationError("Journal summary is required")
        
        sanitized['summary'] = cls.validate_text_field(
            journal_data['summary'], 'summary', required=True
        )
        
        if 'description' in journal_data:
            sanitized['description'] = cls.validate_text_field(
                journal_data['description'], 'description'
            )
        
        if 'dtstart' in journal_data and journal_data['dtstart'] is not None:
            sanitized['dtstart'] = cls.validate_datetime(journal_data['dtstart'], 'dtstart')
        
        if 'categories' in journal_data:
            sanitized['categories'] = cls.validate_categories(journal_data['categories'])
        
        if 'uid' in journal_data:
            sanitized['uid'] = cls.validate_uid(journal_data['uid'])
            
        if 'related_to' in journal_data:
            sanitized['related_to'] = cls.validate_related_to(journal_data['related_to'])
        
        return sanitized
    
    @classmethod
    def validate_priority(cls, priority: Any) -> int:
        """Validate task priority (1-9, RFC 5545 compliant)."""
        try:
            priority_val = int(priority)
        except (ValueError, TypeError):
            raise ValidationError("Priority must be an integer")
        
        if priority_val < 1 or priority_val > 9:
            raise ValidationError("Priority must be between 1-9 (1 is highest)")
        
        return priority_val
    
    @classmethod
    def validate_task_status(cls, status: Any) -> TaskStatus:
        """Validate task status."""
        if isinstance(status, TaskStatus):
            return status
        
        try:
            return TaskStatus(str(status))
        except ValueError:
            valid_statuses = [s.value for s in TaskStatus]
            raise ValidationError(f"Invalid task status. Must be one of: {valid_statuses}")
    
    @classmethod
    def validate_percent_complete(cls, percent: Any) -> int:
        """Validate percent complete (0-100)."""
        try:
            percent_val = int(percent)
        except (ValueError, TypeError):
            raise ValidationError("Percent complete must be an integer")
        
        if percent_val < 0 or percent_val > 100:
            raise ValidationError("Percent complete must be between 0-100")
        
        return percent_val
    
    @classmethod
    def validate_categories(cls, categories: Any) -> List[str]:
        """Validate categories list."""
        if not isinstance(categories, list):
            if isinstance(categories, str):
                # Single category as string
                categories = [categories]
            else:
                raise ValidationError("Categories must be a list or string")
        
        validated_categories = []
        for category in categories:
            if not isinstance(category, str):
                raise ValidationError("Each category must be a string")
            
            category_clean = cls.validate_text_field(str(category), 'category')
            if category_clean:  # Only add non-empty categories
                validated_categories.append(category_clean)
        
        return validated_categories
    
    @classmethod
    def validate_related_to(cls, related_to: Any) -> List[str]:
        """Validate RELATED-TO UIDs list."""
        if not isinstance(related_to, list):
            if isinstance(related_to, str):
                # Single UID as string
                related_to = [related_to]
            else:
                raise ValidationError("RELATED-TO must be a list or string")
        
        validated_uids = []
        for uid in related_to:
            if not isinstance(uid, str):
                raise ValidationError("Each RELATED-TO UID must be a string")
            
            validated_uid = cls.validate_uid(uid)
            validated_uids.append(validated_uid)
        
        return validated_uids
