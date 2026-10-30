"""OAuth credentials backed by Windows Credential Manager via keyring."""
from __future__ import annotations
import json, logging, time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from . import paths
log = logging.getLogger(__name__)
SERVICE, ACCOUNT = "ClaudeUsage", "oauth"

@dataclass(frozen=True)
class Credentials:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    scopes: list[str] | None = None
    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at - time.time() < 60
    def to_json(self) -> str:
        return json.dumps({"accessToken": self.access_token, "refreshToken": self.refresh_token, "expiresAt": self.expires_at, "scopes": self.scopes})
    @classmethod
    def from_json(cls, text: str) -> Credentials | None:
        try: data=json.loads(text); token=data["accessToken"]
        except (ValueError, KeyError, TypeError): return None
        if not isinstance(token,str) or not token: return None
        return cls(token,data.get("refreshToken"),data.get("expiresAt"),data.get("scopes"))

class Backend(Protocol):
    def read(self) -> str | None: ...
    def write(self, value: str) -> bool: ...
    def delete(self) -> None: ...

class WindowsKeyringBackend:
    def __init__(self):
        import keyring
        self.keyring=keyring
    def read(self) -> str | None:
        try: return self.keyring.get_password(SERVICE, ACCOUNT)
        except Exception as exc: log.warning("Credential Manager read failed: %s",exc); return None
    def write(self,value:str)->bool:
        try: self.keyring.set_password(SERVICE,ACCOUNT,value); return True
        except Exception as exc: log.warning("Credential Manager write failed: %s",exc); return False
    def delete(self)->None:
        try: self.keyring.delete_password(SERVICE,ACCOUNT)
        except Exception: pass

class FileBackend:
    """Fallback storage; Windows ACLs inherit from the user's profile directory."""
    def __init__(self,path:Path|None=None): self._path=path
    @property
    def path(self)->Path: return self._path or paths.config_dir()/"credentials.json"
    def read(self)->str|None:
        try: return self.path.read_text(encoding="utf-8")
        except OSError: return None
    def write(self,value:str)->bool:
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.path.with_suffix(".tmp"); temp.write_text(value,encoding="utf-8"); temp.replace(self.path); return True
        except OSError as exc: log.error("Credential fallback write failed: %s",exc); return False
    def delete(self)->None:
        try: self.path.unlink(missing_ok=True)
        except OSError: pass

def default_backends()->list[Backend]:
    result=[]
    try: result.append(WindowsKeyringBackend())
    except ImportError as exc: log.warning("keyring unavailable: %s",exc)
    result.append(FileBackend())
    return result

class CredentialStore:
    def __init__(self,backends:list[Backend]|None=None): self._backends=backends if backends is not None else default_backends()
    def load(self)->Credentials|None:
        for backend in self._backends:
            value=backend.read()
            if value and (item:=Credentials.from_json(value)): return item
        return None
    def save(self,credentials:Credentials)->None:
        value=credentials.to_json()
        for i,backend in enumerate(self._backends):
            if backend.write(value):
                for other in self._backends[i+1:]: other.delete()
                return
        log.error("Could not store credentials")
    def clear(self)->None:
        for backend in self._backends: backend.delete()

def claude_code_credentials_file()->Path: return paths.claude_code_dir()/".credentials.json"
def import_from_claude_code()->Credentials|None:
    try:
        data=json.loads(claude_code_credentials_file().read_text(encoding="utf-8")); oauth=data["claudeAiOauth"]; token=oauth["accessToken"]
    except (OSError,ValueError,KeyError,TypeError): return None
    if not isinstance(token,str) or not token: return None
    expires=oauth.get("expiresAt")
    return Credentials(token,oauth.get("refreshToken"),expires/1000 if isinstance(expires,(int,float)) else None,oauth.get("scopes"))
def claude_code_login_available()->bool: return claude_code_credentials_file().is_file()
