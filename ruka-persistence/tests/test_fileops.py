import pytest
from pathlib import Path
from ruka_persistence.tools.path_jail import PathJail, detect_binary, ToolError
from ruka_persistence.tools.gateway import IOGateway

def test_path_jail_safe(tmp_path):
    jail = PathJail(tmp_path)
    
    # Safe paths
    p1 = jail.confine("data/test.txt")
    assert p1 == (tmp_path / "data" / "test.txt").resolve()
    
    p2 = jail.confine("data/../test2.txt")
    assert p2 == (tmp_path / "test2.txt").resolve()

def test_path_jail_escape(tmp_path):
    jail = PathJail(tmp_path)
    
    # Escape path
    with pytest.raises(ToolError, match="jalur keluar kurung kerja"):
        jail.confine("../outside.txt")
        
    with pytest.raises(ToolError, match="jalur keluar kurung kerja"):
        jail.confine("../../etc/passwd")
        
    # Test Windows absolute path style escape if it resolves outside
    if Path("C:/Windows/system32").resolve().exists():
         with pytest.raises(ToolError, match="jalur keluar kurung kerja"):
             jail.confine("C:/Windows/system32")

def test_gateway_write_and_read(tmp_path):
    jail = PathJail(tmp_path)
    gw = IOGateway(jail)
    
    gw.write_text("hello.txt", "world")
    
    text = gw.read_text("hello.txt")
    assert text == "world"
    
def test_gateway_binary_detect(tmp_path):
    jail = PathJail(tmp_path)
    gw = IOGateway(jail)
    
    bin_path = tmp_path / "img.png"
    bin_path.write_bytes(b'\x89PNG\r\n\x1a\n')
    
    with pytest.raises(ToolError, match="file biner ditolak"):
        gw.read_text("img.png")

def test_gateway_search(tmp_path):
    jail = PathJail(tmp_path)
    gw = IOGateway(jail)
    
    gw.write_text("doc1.txt", "has ruka word")
    gw.write_text("doc2.txt", "no word here")
    gw.write_text("doc3.txt", "ruka is here")
    
    res = gw.search_text("ruka")
    assert len(res) == 2
    assert "doc1.txt" in res or "doc1.txt" in [x.replace("\\", "/") for x in res]

def test_gateway_delete(tmp_path):
    jail = PathJail(tmp_path)
    gw = IOGateway(jail)
    
    gw.write_text("delme.txt", "bye")
    
    with pytest.raises(ToolError, match="token konfirmasi salah"):
        gw.delete_file("delme.txt", "WRONG")
        
    success = gw.delete_file("delme.txt", "YES_DELETE")
    assert success is True
    assert not (tmp_path / "delme.txt").exists()
