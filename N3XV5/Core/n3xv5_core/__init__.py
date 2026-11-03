"""Shared N3XV5 N0v4 HUD Core contracts, no platform GUI dependencies."""
from .contracts import AppManifest, Platform, normalize_platform, validate_manifest
from .suite import SuiteRegistry
from .profile import SuiteProfile, ProfileGrants
__all__=["AppManifest","Platform","normalize_platform","validate_manifest","SuiteRegistry","SuiteProfile","ProfileGrants"]
