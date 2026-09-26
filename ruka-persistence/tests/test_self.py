import pytest
import time
from ruka_persistence.selfmodel.self import PersistentSelf

def test_persistent_self_hash(tmp_path):
    p = PersistentSelf(
        identity_name="Ruka",
        birth_date=time.time(),
        core_directives=["Protect data", "Assist user"]
    )
    
    file_path = tmp_path / "self.json"
    generated_hash = p.save(file_path)
    
    assert file_path.exists()
    
    # Load and verify
    loaded_p, is_valid = PersistentSelf.load(file_path)
    assert is_valid is True
    assert loaded_p.identity_name == "Ruka"
    
    # Mutate data (tampering)
    data = file_path.read_text(encoding="utf-8")
    tampered_data = data.replace("Ruka", "EvilRuka")
    file_path.write_text(tampered_data, encoding="utf-8")
    
    loaded_evil, is_valid_evil = PersistentSelf.load(file_path)
    assert is_valid_evil is False
