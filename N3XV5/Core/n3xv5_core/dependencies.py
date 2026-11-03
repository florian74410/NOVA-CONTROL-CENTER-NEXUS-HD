"""Offline shared artifact cache with immutable content-addressed blobs."""
from __future__ import annotations
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from .contracts import SHA256

MAX_ASSET_BYTES=1024*1024*1024
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

class DependencyStore:
    def __init__(self,root,platform):
        self.root=Path(root)
        self.platform=platform.value

    def blob(self,digest):
        if not SHA256.fullmatch(digest):
            raise ValueError("SHA256 digest required")
        return self.root/"Common"/self.platform/"sha256"/digest

    def ingest(self,file_path,expected_digest):
        file_path=Path(file_path)
        if not file_path.is_file() or file_path.is_symlink():
            raise ValueError("Only regular local files are allowed")
        if file_path.stat().st_size>MAX_ASSET_BYTES:
            raise ValueError("Dependency too large")
        if sha256(file_path)!=expected_digest:
            raise ValueError("Dependency integrity mismatch")
        dst=self.blob(expected_digest)
        dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        if dst.exists():
            if sha256(dst)!=expected_digest:raise ValueError("Shared cache corruption")
            return dst
        fd,temp=tempfile.mkstemp(prefix=".incoming-",dir=dst.parent)
        try:
            with os.fdopen(fd,"wb") as out,file_path.open("rb") as source:
                shutil.copyfileobj(source,out,1024*1024)
                out.flush()
                os.fsync(out.fileno())
            if sha256(temp)!=expected_digest:raise ValueError("Checksum changed during import")
            os.chmod(temp,0o444)
            os.replace(temp,dst)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        return dst

    def available(self,digest):
        file=self.blob(digest)
        return file.is_file() and sha256(file)==digest
