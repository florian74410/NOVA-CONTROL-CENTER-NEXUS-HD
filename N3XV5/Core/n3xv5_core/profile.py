"""Portable *metadata* identity contract shared by all N3XV5 applications.

No OS-specific credentials or PIN hashes are exported. The HUB alone
authenticates; a profile id is not an authentication token.
"""
from __future__ import annotations
from dataclasses import dataclass,field
import re
import uuid

ID=re.compile(r"^[0-9a-f]{32}$")
APP=re.compile(r"^[a-z][a-z0-9-]{2,63}$")

@dataclass(frozen=True)
class ProfileGrants:
    app_id:str
    capabilities:tuple[str,...]
    def validated(self):
        if not APP.fullmatch(self.app_id) or len(self.capabilities)>64:
            raise ValueError("Invalid app grant")
        if any(not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,90}",x) for x in self.capabilities):
            raise ValueError("Invalid capability")
        return self

@dataclass(frozen=True)
class SuiteProfile:
    profile_id:str
    display_name:str
    grants:tuple[ProfileGrants,...]=field(default_factory=tuple)
    connection_ids:tuple[str,...]=field(default_factory=tuple)
    schema:int=1

    @classmethod
    def create(cls,name):
        return cls(profile_id=uuid.uuid4().hex,display_name=name).validated()

    def validated(self):
        if self.schema!=1 or not ID.fullmatch(self.profile_id):
            raise ValueError("Invalid profile")
        if not self.display_name or len(self.display_name)>100:
            raise ValueError("Invalid profile label")
        if len(self.grants)>64 or len(self.connection_ids)>500:
            raise ValueError("Exceeded suite profile limits")
        if len({x.app_id for x in self.grants})!=len(self.grants):
            raise ValueError("Duplicate application grants")
        for grant in self.grants:grant.validated()
        if any(not ID.fullmatch(x) for x in self.connection_ids):
            raise ValueError("Invalid connection handle")
        if len(set(self.connection_ids))!=len(self.connection_ids):
            raise ValueError("Duplicate connection handles")
        return self

    def permits(self,app_id,capability):
        return any(g.app_id==app_id and capability in g.capabilities for g in self.grants)

    def export_public(self):
        self.validated()
        return {"schema":self.schema,"suite":"n3xv5-n0v4-hud",
                "profile_id":self.profile_id,"display_name":self.display_name,
                "applications":[g.app_id for g in self.grants],
                "connection_ids":list(self.connection_ids)}
