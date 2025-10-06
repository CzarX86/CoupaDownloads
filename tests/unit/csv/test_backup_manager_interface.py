"""Contract tests for BackupManagerInterface."""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

# Add the specs directory to the path for importing contracts
specs_dir = Path(__file__).parent.parent.parent.parent / "specs" / "007-fix-csv-handler"
sys.path.insert(0, str(specs_dir))

from contracts.interfaces import (
    BackupManagerInterface,
    BackupMetadata,
    BackupError
)


class TestBackupManagerInterface:
    """Test contract compliance for BackupManagerInterface implementations."""
    
    def test_init_requires_backup_dir(self):
        """Test that BackupManagerInterface requires backup_dir parameter."""
        with pytest.raises(TypeError):
            # Should fail because BackupManagerInterface is abstract
            BackupManagerInterface()
    
    def test_create_backup_signature(self):
        """Test create_backup method signature."""
        manager = Mock(spec=BackupManagerInterface)
        
        # Mock return value
        mock_metadata = BackupMetadata(
            backup_path=Path("/backup/input_20251002_120000_session123.csv"),
            original_path=Path("/data/input.csv"),
            created_at=datetime.now(),
            session_id="session123",
            record_count=446,
            file_size_bytes=1024000
        )
        manager.create_backup.return_value = mock_metadata
        
        result = manager.create_backup(Path("/data/input.csv"), "session123")
        assert isinstance(result, BackupMetadata)
        assert result.session_id == "session123"
        manager.create_backup.assert_called_once_with(Path("/data/input.csv"), "session123")
    
    def test_cleanup_old_backups_signature(self):
        """Test cleanup_old_backups method signature."""
        manager = Mock(spec=BackupManagerInterface)
        manager.cleanup_old_backups.return_value = [
            Path("/backup/old1.csv"),
            Path("/backup/old2.csv")
        ]
        
        result = manager.cleanup_old_backups()
        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result)
    
    def test_restore_from_backup_signature(self):
        """Test restore_from_backup method signature."""
        manager = Mock(spec=BackupManagerInterface)
        manager.restore_from_backup.return_value = True
        
        mock_metadata = BackupMetadata(
            backup_path=Path("/backup/test.csv"),
            original_path=Path("/data/input.csv"),
            created_at=datetime.now(),
            session_id="session123",
            record_count=446,
            file_size_bytes=1024000
        )
        
        result = manager.restore_from_backup(mock_metadata, Path("/restore/target.csv"))
        assert isinstance(result, bool)
        manager.restore_from_backup.assert_called_once_with(mock_metadata, Path("/restore/target.csv"))
    
    def test_abstract_methods_prevent_instantiation(self):
        """Test that BackupManagerInterface cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BackupManagerInterface(Path("/backup"))
    
    def test_backup_error_exception(self):
        """Test that BackupError exception is properly defined."""
        with pytest.raises(BackupError):
            raise BackupError("Backup operation failed")


class TestBackupMetadataContract:
    """Test BackupMetadata dataclass contract."""
    
    def test_backup_metadata_creation(self):
        """Test BackupMetadata can be created with required fields."""
        metadata = BackupMetadata(
            backup_path=Path("/backup/input_20251002_120000_session123.csv"),
            original_path=Path("/data/input/input.csv"),
            created_at=datetime.now(),
            session_id="session123",
            record_count=446,
            file_size_bytes=1024000
        )
        
        assert isinstance(metadata.backup_path, Path)
        assert isinstance(metadata.original_path, Path)
        assert isinstance(metadata.created_at, datetime)
        assert metadata.session_id == "session123"
        assert metadata.record_count == 446
        assert metadata.file_size_bytes == 1024000
    
    def test_backup_metadata_path_validation(self):
        """Test that backup metadata properly handles Path objects."""
        # Test with string paths (should be converted to Path)
        metadata = BackupMetadata(
            backup_path=Path("/backup/test.csv"),
            original_path=Path("/data/input.csv"),
            created_at=datetime.now(),
            session_id="test_session",
            record_count=100,
            file_size_bytes=50000
        )
        
        assert metadata.backup_path.name == "test.csv"
        assert metadata.original_path.name == "input.csv"
        assert metadata.backup_path.is_absolute()
        assert metadata.original_path.is_absolute()
    
    def test_backup_metadata_session_tracking(self):
        """Test backup metadata tracks session information correctly."""
        now = datetime.now()
        metadata = BackupMetadata(
            backup_path=Path("/backup/session_backup.csv"),
            original_path=Path("/data/input.csv"),
            created_at=now,
            session_id="unique_session_12345",
            record_count=500,
            file_size_bytes=2048000
        )
        
        assert metadata.session_id.startswith("unique_session_")
        assert metadata.created_at == now
        assert metadata.record_count > 0
        assert metadata.file_size_bytes > 0