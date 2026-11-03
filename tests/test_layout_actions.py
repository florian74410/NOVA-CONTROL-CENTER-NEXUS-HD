import pytest
from nova_control_center.layout_storage import save_layout,load_layout,validate_layout
from nova_control_center.action_registry import ActionRegistry

def test_layout_roundtrip(tmp_path):
    path=tmp_path/"layout.json"
    frames=[{"title":"Vitalité","app_id":"iatb-cli","category":"Vitalité","x":0,"y":0,"w":3,"h":3}]
    save_layout(frames,path)
    assert load_layout(path)==frames

def test_reject_overlap_and_unsupported_size():
    frame={"title":"A","x":0,"y":0,"w":3,"h":3}
    with pytest.raises(ValueError):validate_layout([frame,frame])
    with pytest.raises(ValueError):validate_layout([dict(frame,w=2,h=3)])

def test_action_catalog_registration(qtbot):
    registry=ActionRegistry()
    registry.register("cli-a",{"categories":[{"actions":[{"name":"restart","label":"Redémarrer","description":"Redémarre le service","confirm":True}]}]})
    assert registry.catalog["cli-a"]["restart"]["description"]=="Redémarre le service"
    assert "restart" not in registry.catalog.get("cli-b",{})
