"""
Unit tests for input validation
"""
import pytest
from datetime import datetime
from chronos_mcp.validation import InputValidator
from chronos_mcp.exceptions import ValidationError


class TestTextFieldValidation:
    def test_validate_text_field_success(self):
        """Test successful text field validation"""
        result = InputValidator.validate_text_field("Test Event", "summary")
        assert result == "Test Event"
        
        # Test with HTML entities (should NOT be escaped at storage layer)
        result = InputValidator.validate_text_field(
            "Meeting & Discussion", 
            "summary"
        )
        assert result == "Meeting & Discussion"  # No escaping at storage
    
    def test_validate_text_field_required(self):
        """Test required field validation"""
        # Required field with empty value
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_text_field("", "summary", required=True)
        assert "summary is required" in str(exc_info.value)
        
        # Optional field with empty value
        result = InputValidator.validate_text_field("", "description", required=False)
        assert result == ""
    
    def test_validate_text_field_length(self):
        """Test field length validation"""
        # Exceed max length
        long_text = "A" * 300
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_text_field(long_text, "summary")
        assert "exceeds maximum length" in str(exc_info.value)
    
    def test_dangerous_patterns_detection(self):
        """Test detection of dangerous patterns"""
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "<a href='javascript:void(0)'>",
            "<div onclick='bad()'>",
            "<script src='bad.js'></script>",
            "<iframe src='evil.com'>",
            "<object data='bad'>",
            "<embed code='evil'>",
        ]
        
        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValidationError) as exc_info:
                InputValidator.validate_text_field(dangerous_input, "description")
            assert "potentially dangerous content" in str(exc_info.value)
    
    def test_unicode_normalization(self):
        """Test Unicode normalization"""
        # Unicode with different representations
        text_nfc = "café"  # NFC form
        text_nfd = "café"  # NFD form (e + combining acute)
        
        result1 = InputValidator.validate_text_field(text_nfc, "summary")
        result2 = InputValidator.validate_text_field(text_nfd, "summary")
        
        # Both should normalize to the same form
        assert result1 == result2


class TestDateTimeValidation:
    def test_validate_datetime_success(self):
        """Test successful datetime validation"""
        # Already a datetime object
        dt = datetime.now()
        result = InputValidator.validate_datetime(dt, "dtstart")
        assert result == dt
        
        # ISO format string
        iso_str = "2025-07-10T10:00:00"
        result = InputValidator.validate_datetime(iso_str, "dtstart")
        assert isinstance(result, datetime)
        
        # ISO format with Z suffix
        iso_z = "2025-07-10T10:00:00Z"
        result = InputValidator.validate_datetime(iso_z, "dtstart")
        assert isinstance(result, datetime)
    
    def test_validate_datetime_failure(self):
        """Test datetime validation failures"""
        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_datetime("not a date", "dtstart")
        assert "Invalid datetime format" in str(exc_info.value)
        
        # Wrong type
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_datetime(12345, "dtstart")
        assert "must be a datetime or ISO format string" in str(exc_info.value)


class TestUIDValidation:
    def test_validate_uid_success(self):
        """Test successful UID validation"""
        valid_uids = [
            "event-123",
            "abc_def",
            "test.uid",
            "user@example.com",
            "UID-2025-07-10"
        ]
        
        for uid in valid_uids:
            result = InputValidator.validate_uid(uid)
            assert result == uid
    
    def test_validate_uid_failure(self):
        """Test UID validation failures"""
        # Empty UID
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_uid("")
        assert "UID cannot be empty" in str(exc_info.value)
        
        # Invalid characters
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_uid("uid with spaces")
        assert "invalid characters" in str(exc_info.value)
        
        # Path traversal attempt
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_uid("../../../etc/passwd")
        # This will fail the regex check first, not the path check
        assert "invalid characters" in str(exc_info.value)
        
        # Too long
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_uid("a" * 300)
        assert "exceeds maximum length" in str(exc_info.value)


class TestEmailValidation:
    def test_validate_email_success(self):
        """Test successful email validation"""
        valid_emails = [
            "user@example.com",
            "test.user@domain.co.uk",
            "name+tag@example.org",
            "admin123@test-domain.com"
        ]
        
        for email in valid_emails:
            result = InputValidator.validate_email(email)
            assert result == email.lower()  # Should be lowercased
    
    def test_validate_email_failure(self):
        """Test email validation failures"""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user@@example.com",
            "user@.com",
            "a" * 250 + "@example.com"  # Too long
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                InputValidator.validate_email(email)


class TestEventValidation:
    def test_validate_event_success(self):
        """Test successful event validation"""
        event_data = {
            'summary': 'Team Meeting',
            'dtstart': '2025-07-10T10:00:00',
            'dtend': '2025-07-10T11:00:00',
            'description': 'Weekly sync',
            'location': 'Conference Room'
        }
        
        result = InputValidator.validate_event(event_data)
        
        assert result['summary'] == 'Team Meeting'
        assert isinstance(result['dtstart'], datetime)
        assert isinstance(result['dtend'], datetime)
        assert result['description'] == 'Weekly sync'
        assert result['location'] == 'Conference Room'
    
    def test_validate_event_missing_required(self):
        """Test event validation with missing required fields"""
        # Missing summary
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_event({
                'dtstart': '2025-07-10T10:00:00',
                'dtend': '2025-07-10T11:00:00'
            })
        assert "summary is required" in str(exc_info.value)
        
        # Missing dates
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_event({'summary': 'Test'})
        assert "start time is required" in str(exc_info.value)
    
    def test_validate_event_date_logic(self):
        """Test event date validation logic"""
        # End before start
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_event({
                'summary': 'Test',
                'dtstart': '2025-07-10T11:00:00',
                'dtend': '2025-07-10T10:00:00'
            })
        assert "end time must be after start time" in str(exc_info.value)


class TestAttendeeValidation:
    def test_validate_attendees_success(self):
        """Test successful attendee validation"""
        attendees = [
            {
                'email': 'user1@example.com',
                'name': 'User One',
                'role': 'REQ-PARTICIPANT',
                'status': 'ACCEPTED',
                'rsvp': True
            },
            {
                'email': 'user2@example.com'  # Minimal attendee
            }
        ]
        
        result = InputValidator.validate_attendees(attendees)
        
        assert len(result) == 2
        assert result[0]['email'] == 'user1@example.com'
        assert result[0]['role'] == 'REQ-PARTICIPANT'
        assert result[1]['email'] == 'user2@example.com'
    
    def test_validate_attendees_failure(self):
        """Test attendee validation failures"""
        # Not a list
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_attendees("not a list")
        assert "must be a list" in str(exc_info.value)
        
        # Missing email
        with pytest.raises(ValidationError):
            InputValidator.validate_attendees([{'name': 'No Email'}])
        
        # Invalid role
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_attendees([{
                'email': 'test@example.com',
                'role': 'INVALID-ROLE'
            }])
        assert "Invalid attendee role" in str(exc_info.value)


class TestRRULEValidation:
    def test_validate_rrule_success(self):
        """Test successful RRULE validation"""
        valid_rules = [
            "FREQ=DAILY",
            "FREQ=WEEKLY;BYDAY=MO,WE,FR",
            "FREQ=MONTHLY;BYMONTHDAY=15",
            "FREQ=YEARLY;BYMONTH=12;BYMONTHDAY=25"
        ]
        
        for rule in valid_rules:
            result = InputValidator.validate_rrule(rule)
            assert result == rule.upper()
    
    def test_validate_rrule_failure(self):
        """Test RRULE validation failures"""
        # Must start with FREQ
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_rrule("BYDAY=MO")
        assert "must start with FREQ=" in str(exc_info.value)
        
        # Invalid frequency
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_rrule("FREQ=HOURLY")
        assert "Invalid frequency" in str(exc_info.value)
        
        # Too long
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_rrule("FREQ=DAILY;" + "X=Y;" * 200)
        assert "too complex" in str(exc_info.value)
