"""Universal CLI action catalog and explanatory popup for HUB-owned GUI."""
from __future__ import annotations
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal

class ActionRegistry(QObject):
    requested=Signal(str,str,object)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.catalog={}
    def register(self,app_id,catalog):
        actions={}
        for category in catalog.get("categories",[]):
            for action in category.get("actions",[]):
                if not isinstance(action,dict):continue
                name=action.get("name")
                if not isinstance(name,str) or not name:continue
                actions[name]={"label":str(action.get("label",name)),
                               "description":str(action.get("description","")),
                               "params":action.get("params_schema",{}),
                               "confirm":bool(action.get("confirm",True))}
        self.catalog[app_id]=actions
    def explain_and_request(self,app_id,name,parent=None,params=None):
        action=self.catalog.get(app_id,{}).get(name)
        if action is None:raise KeyError("Unknown action")
        text=action["description"] or action["label"]
        if action["confirm"]:
            result=QMessageBox.question(parent,action["label"],text+"\n\nExécuter cette action ?",
                                        QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
            if result!=QMessageBox.StandardButton.Yes:return False
        else:
            QMessageBox.information(parent,action["label"],text)
        self.requested.emit(app_id,name,params or {})
        return True
