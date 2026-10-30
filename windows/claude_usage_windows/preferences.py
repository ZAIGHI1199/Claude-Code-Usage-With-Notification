"""Windows preferences persisted in the user's roaming profile."""
from __future__ import annotations
import json, logging, os
from pathlib import Path
from collections.abc import Callable
from . import paths
log=logging.getLogger(__name__)
DISPLAY_OPTIONS={"percentAndTime":"Usage and reset","percent":"Usage only","time":"Reset only","iconOnly":"Icon only"}
REFRESH_OPTIONS=[30,60,120,300]
WARN_RANGE=(0.5,0.95)
class Preferences:
    def __init__(self,path:Path|None=None,autostart_file:Path|None=None):
        self._path=path; self._observers:list[Callable[[str],None]]=[]
        self._display="percentAndTime"; self._refresh_interval=60; self._warn_threshold=.8; self._show_context_in_tray=False
        self._load()
    @property
    def path(self)->Path: return self._path or paths.config_dir()/"settings.json"
    def _load(self):
        try: data=json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError,ValueError): return
        if not isinstance(data,dict): return
        if data.get("display") in DISPLAY_OPTIONS:self._display=data["display"]
        if data.get("refresh_interval") in REFRESH_OPTIONS:self._refresh_interval=data["refresh_interval"]
        value=data.get("warn_threshold")
        if isinstance(value,(int,float)) and not isinstance(value,bool):self._warn_threshold=min(max(value,.5),.95)
        if isinstance(data.get("show_context_in_tray"),bool):self._show_context_in_tray=data["show_context_in_tray"]
    def _save(self):
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"display":self._display,"refresh_interval":self._refresh_interval,"warn_threshold":self._warn_threshold,"show_context_in_tray":self._show_context_in_tray},indent=2),encoding="utf-8"); tmp.replace(self.path)
        except OSError as exc: log.warning("Could not save preferences: %s",exc)
    def subscribe(self,observer): self._observers.append(observer)
    def _set(self,name,value):
        attr="_"+name
        if getattr(self,attr)==value:return
        setattr(self,attr,value); self._save()
        for observer in list(self._observers):observer(name)
    @property
    def display(self):return self._display
    @display.setter
    def display(self,v):
        if v in DISPLAY_OPTIONS:self._set("display",v)
    @property
    def refresh_interval(self):return self._refresh_interval
    @refresh_interval.setter
    def refresh_interval(self,v):
        if v in REFRESH_OPTIONS:self._set("refresh_interval",v)
    @property
    def warn_threshold(self):return self._warn_threshold
    @warn_threshold.setter
    def warn_threshold(self,v):self._set("warn_threshold",round(min(max(v,.5),.95),2))
    @property
    def show_context_in_tray(self):return self._show_context_in_tray
    @show_context_in_tray.setter
    def show_context_in_tray(self,v):self._set("show_context_in_tray",bool(v))
    @property
    def shows_percent(self):return self._display in ("percentAndTime","percent")
    @property
    def shows_time(self):return self._display in ("percentAndTime","time")
    @property
    def launch_at_login(self):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                winreg.QueryValueEx(key,"ClaudeUsage"); return True
        except OSError:return False
    @launch_at_login.setter
    def launch_at_login(self,enabled):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Run",0,winreg.KEY_SET_VALUE) as key:
                if enabled: winreg.SetValueEx(key,"ClaudeUsage",0,winreg.REG_SZ,f'"{os.path.abspath(os.sys.argv[0])}" --background')
                else:
                    try:winreg.DeleteValue(key,"ClaudeUsage")
                    except FileNotFoundError:pass
        except OSError as exc:log.warning("Could not update startup setting: %s",exc)
        for observer in list(self._observers):observer("launch_at_login")
