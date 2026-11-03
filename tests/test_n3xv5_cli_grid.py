from n3xv5_core.cli_protocol import request,encode,decode,response,validate_catalog,ProtocolError
import pytest

def test_roundtrip():
    req=request("iatb-cli","catalog.describe",request_id="9")
    assert decode(encode(req))==req
    assert decode(encode(response(req,result={"ok":True})))["result"]["ok"]

def test_invalid_envelopes():
    with pytest.raises(ProtocolError):request("BAD","a")
    with pytest.raises(ProtocolError):decode(b'{"n3xv5":2,"id":"1"}\n')
    with pytest.raises(ProtocolError):decode(b"invalid\n")
    with pytest.raises(ProtocolError):encode({"huge":"x"*(1024*1024)})

def test_catalog():
    assert validate_catalog({"categories":[{"id":"vitality","label":"Vitalité","commands":[{"method":"vps.health"}]}]})
    with pytest.raises(ProtocolError):validate_catalog({"categories":[{"id":"x","label":"x","commands":[{}]}]})

def test_grid_geometry(qtbot):
    from nova_control_center.grid_engine import GridView
    view=GridView();qtbot.addWidget(view)
    scene=view.grid
    a=scene.add_tile("Vitalité",2,3)
    assert a and (a.xcell,a.ycell)==(0,0)
    assert len(scene.positions(2,3))<8*7
    assert not scene.can_place(1,1,2,3)
    assert scene.add_tile("Actions",2,3)
    assert not a.resize_cells(9,9)
    assert scene.layout()[0]["w"]==2
