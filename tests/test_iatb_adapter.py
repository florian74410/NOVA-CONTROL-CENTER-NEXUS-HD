from nova_control_center.iatb_adapter import catalog,dispatch,COMMANDS
import pytest

def test_catalog_has_real_documented_categories():
    data=catalog()
    assert data["app"]=="iatb-cli"
    assert any(c["label"]=="Vitalité" for c in data["categories"])
    assert "vps.status" in COMMANDS
    assert "vps.reboot" not in COMMANDS

def test_unknown_commands_rejected():
    with pytest.raises(ValueError):dispatch("vps.shutdown",{})
    with pytest.raises(ValueError):dispatch("vps.status",{"shell":"rm -rf /"})
