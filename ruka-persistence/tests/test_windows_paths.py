import pytest
from ruka_persistence.windows.paths import WindowsPathLayout, PathLayoutError

def test_windows_path_layout(tmp_path):
    layout = WindowsPathLayout(tmp_path)
    
    # Check directory creation
    config_dir = layout.dir("config")
    assert config_dir.name == "config"
    assert config_dir.exists()
    
    # Check file
    db_file = layout.file("data", "ruka.db")
    assert db_file.parent.name == "data"
    assert db_file.name == "ruka.db"
    
    # Check jail confinement
    safe = layout.confine("data", "safe.txt")
    assert safe.name == "safe.txt"
    
    with pytest.raises(PathLayoutError):
        layout.confine("data", "../config/settings.json")
