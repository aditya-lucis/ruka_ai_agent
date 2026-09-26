import pytest
import time
from ruka_persistence.ipc.server import IpcServer
from ruka_persistence.ipc.client import IpcClient

def test_ipc_server_client(tmp_path):
    endpoint_path = tmp_path / "endpoint.json"
    
    server = IpcServer(endpoint_path)
    server.start()
    
    # Wait for endpoint file
    time.sleep(0.1)
    assert endpoint_path.exists()
    
    client = IpcClient(endpoint_path)
    client.connect()
    
    # Call method
    res = client.call("ping", {"data": 123})
    assert res["result"] == "ok"
    
    client.close()
    server.stop()
