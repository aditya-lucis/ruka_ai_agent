import pytest
import json
from ruka_persistence.backup.manager import BackupManager

def test_backup_manager_creates_manifest(tmp_path):
    # Setup
    db_file = tmp_path / "ruka.db"
    db_file.write_text("fake db content")
    
    backup_dir = tmp_path / "backups"
    manager = BackupManager(backup_dir)
    
    # Execute
    backup_path = manager.create_backup(db_file)
    
    # Assert
    assert backup_dir.exists()
    assert len(list(backup_dir.glob("backup_*.db"))) == 1
    
    manifests = list(backup_dir.glob("manifest_*.json"))
    assert len(manifests) == 1
    
    manifest_data = json.loads(manifests[0].read_text())
    assert "hash" in manifest_data
    assert "file" in manifest_data
