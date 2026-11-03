from PySide6.QtCore import QObject, Signal
from nova_control_center.cli_cache import CliCacheManager

class FakeConnector(QObject):
    result=Signal(str,object)
    failed=Signal(str,str)
    def __init__(self):
        super().__init__()
        self.calls=[]
    def request(self,method,params=None,timeout_ms=0):
        self.calls.append((method,params))

def test_shared_cache_and_force_refresh(qtbot):
    now=[100.0]
    manager=CliCacheManager(clock=lambda:now[0])
    cli=FakeConnector()
    manager.register("example-cli",cli)
    assert manager.get("example-cli",["cpu"])["cpu"]["status"]=="pending"
    assert len(cli.calls)==1
    manager.get("example-cli",["cpu"])
    assert len(cli.calls)==1
    cli.result.emit("data.get",{"values":{"cpu":{"value":42,"priority":1,"status":"ok"}}})
    assert manager.get("example-cli",["cpu"])["cpu"]["value"]==42
    assert len(cli.calls)==1
    now[0]+=61
    assert manager.get("example-cli",["cpu"])["cpu"]["stale"]
    assert len(cli.calls)==2
    cli.failed.emit("data.get","offline")
    assert manager.get("example-cli",["cpu"])["cpu"]["value"]==42
    manager.refresh("example-cli",["cpu"])
    assert len(cli.calls)==3

def test_independent_cli_caches(qtbot):
    manager=CliCacheManager()
    a,b=FakeConnector(),FakeConnector()
    manager.register("a-cli",a)
    manager.register("b-cli",b)
    manager.get("a-cli",["status"])
    assert len(a.calls)==1 and not b.calls
    manager.get("b-cli",["status"])
    assert len(b.calls)==1
