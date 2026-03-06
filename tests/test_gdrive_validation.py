"""
Regression tests for Google Drive input validation security fixes.
Tests the P1 FQL injection prevention measures.
"""

import pytest

from app.gdrive import _validate_drive_name, _validate_drive_parent_id


class TestDriveNameValidation:
    """Test folder name validation for FQL injection prevention."""

    def test_valid_names(self):
        """Valid folder names should pass validation."""
        valid_names = [
            "backups",
            "db_backups",
            "uploads",
            "folder-name",
            "folder_name",
            "folder.name",
            "Folder Name With Spaces",
            "123",
            "a-b_c.d",
        ]
        for name in valid_names:
            assert _validate_drive_name(name) == name

    def test_invalid_names(self):
        """Invalid folder names should raise ValueError."""
        invalid_names = [
            "",  # empty
            "'",  # single quote
            "name' OR '1'='1",  # SQL injection attempt
            "name' AND trashed=false",  # FQL injection attempt
            "name;",  # semicolon
            "name\\",  # backslash
            "name\"",  # double quote
            "name<>",  # angle brackets
            "name|",  # pipe
            "name&",  # ampersand
            "name\n",  # newline
            "a" * 101,  # too long
        ]
        for name in invalid_names:
            with pytest.raises(ValueError, match="Drive folder name"):
                _validate_drive_name(name)

    def test_non_string_names(self):
        """Non-string inputs should raise ValueError."""
        with pytest.raises(ValueError, match="Drive folder name must be a non-empty string"):
            _validate_drive_name(None)
        with pytest.raises(ValueError, match="Drive folder name must be a non-empty string"):
            _validate_drive_name(123)


class TestDriveParentIdValidation:
    """Test parent folder ID validation for FQL injection prevention."""

    def test_valid_parent_ids(self):
        """Valid Google Drive file IDs should pass validation."""
        valid_ids = [
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",  # typical format
            "1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U",  # alphanumeric
            "abc123def456ghi789jkl012mno345pqr678stu901vwx",  # mixed case
            "1" * 28,  # minimum length
            "1" * 50,  # maximum length
        ]
        for parent_id in valid_ids:
            assert _validate_drive_parent_id(parent_id) == parent_id

    def test_invalid_parent_ids(self):
        """Invalid parent IDs should raise ValueError."""
        invalid_ids = [
            "",  # empty
            "short",  # too short
            "1" * 19,  # below minimum
            "1" * 51,  # above maximum
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'",  # quote injection
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms; DROP TABLE",  # SQL injection
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms AND trashed=false",  # FQL injection
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms<script>",  # XSS attempt
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms\n",  # newline
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms\\",  # backslash
        ]
        for parent_id in invalid_ids:
            with pytest.raises(ValueError, match="Drive parent ID"):
                _validate_drive_parent_id(parent_id)

    def test_non_string_parent_ids(self):
        """Non-string inputs should raise ValueError."""
        with pytest.raises(ValueError, match="Drive parent ID must be a non-empty string"):
            _validate_drive_parent_id(None)
        with pytest.raises(ValueError, match="Drive parent ID must be a non-empty string"):
            _validate_drive_parent_id(123)