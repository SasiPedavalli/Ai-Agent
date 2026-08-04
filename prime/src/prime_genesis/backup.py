from __future__ import annotations
import hashlib,shutil
from dataclasses import dataclass
from pathlib import Path
from prime_genesis.models import utc_now
@dataclass(frozen=True)
class BackupResult:source:str;destination:str;sha256:str;size_bytes:int;created_at:str
def backup_sqlite(source:str|Path,destination:str|Path)->BackupResult:
 src=Path(source)
 if not src.exists():raise FileNotFoundError(src)
 dst=Path(destination);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);digest=hashlib.sha256(dst.read_bytes()).hexdigest();return BackupResult(str(src),str(dst),digest,dst.stat().st_size,utc_now())
