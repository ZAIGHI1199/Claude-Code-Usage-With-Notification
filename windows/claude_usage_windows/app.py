"""PySide6 Windows tray application for Claude usage."""
from __future__ import annotations
import argparse, sys
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Qt, QTimer
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
    QPushButton,QProgressBar,QSystemTrayIcon,QMenu,QFrame,QMessageBox,QStyle,QInputDialog)
from PySide6.QtCore import QUrl
from .preferences import Preferences
from .store import UsageStore, READY, FAILED, SIGNED_OUT
from . import credentials, browser

class UiBridge(QObject):
    dispatch=Signal(object)

class UsagePanel(QMainWindow):
    def __init__(self,store:UsageStore,prefs:Preferences,tray:QSystemTrayIcon):
        super().__init__(); self.store=store; self.prefs=prefs; self.tray=tray
        self.setWindowTitle("Claude Usage"); self.setMinimumWidth(360); self.setMaximumWidth(420)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QMainWindow,QWidget { background:#171a21; color:#edf0f5; font-family:'Segoe UI'; }
            QLabel#muted { color:#9ba5b5; font-size:11px; }
            QLabel#metric { font-size:27px; font-weight:650; }
            QFrame#card { background:#232936; border:1px solid #30394a; border-radius:10px; }
            QProgressBar { background:#3b4556; border:0; border-radius:4px; height:8px; text-align:center; }
            QProgressBar::chunk { background:#72b58d; border-radius:4px; }
            QPushButton { background:#30394a; border:1px solid #465166; border-radius:7px; padding:8px 12px; }
            QPushButton:hover { background:#3b465a; }
            QPushButton#primary { background:#d97757; border-color:#d97757; color:#151515; font-weight:600; }
        """)
        root=QWidget(); self.setCentralWidget(root); layout=QVBoxLayout(root); layout.setContentsMargins(18,16,18,16); layout.setSpacing(12)
        head=QHBoxLayout(); title=QLabel("Claude Usage"); title.setStyleSheet("font-size:18px;font-weight:650")
        head.addWidget(title); head.addStretch(); self.status=QLabel("Checking…"); self.status.setObjectName("muted"); head.addWidget(self.status); layout.addLayout(head)
        self.cards=QVBoxLayout(); self.cards.setSpacing(9); layout.addLayout(self.cards)
        self.context_card=self._card("Claude Code context window"); self.context_value=QLabel("Not available"); self.context_value.setObjectName("metric"); self.context_bar=QProgressBar(); self.context_bar.setRange(0,100); self.context_bar.setTextVisible(False)
        self.context_card.layout().addWidget(self.context_value); self.context_card.layout().addWidget(self.context_bar); layout.addWidget(self.context_card)
        self.error=QLabel(""); self.error.setWordWrap(True); self.error.setStyleSheet("color:#e6a17f"); layout.addWidget(self.error)
        actions=QHBoxLayout(); self.refresh_button=QPushButton("Refresh"); self.refresh_button.clicked.connect(self.store.refresh); actions.addWidget(self.refresh_button)
        self.sign_button=QPushButton("Sign in with Chrome"); self.sign_button.setObjectName("primary"); self.sign_button.clicked.connect(self.sign_in); actions.addWidget(self.sign_button)
        self.manual_button=QPushButton("Use sign-in code"); self.manual_button.clicked.connect(self.manual_sign_in); actions.addWidget(self.manual_button)
        self.import_button=QPushButton("Import Claude Code login"); self.import_button.clicked.connect(self.import_login); actions.addWidget(self.import_button)
        layout.addLayout(actions)
        self.footer=QLabel("Usage is retrieved from Anthropic. Context data is read locally."); self.footer.setObjectName("muted"); self.footer.setWordWrap(True); layout.addWidget(self.footer)
        self.store.subscribe(self.render); self.render()
    def _card(self,title:str)->QFrame:
        frame=QFrame(); frame.setObjectName("card"); box=QVBoxLayout(frame); box.setContentsMargins(13,11,13,11); label=QLabel(title); label.setObjectName("muted"); box.addWidget(label); return frame
    def _clear_cards(self):
        while self.cards.count():
            item=self.cards.takeAt(0); widget=item.widget()
            if widget:widget.deleteLater()
    def _usage_card(self,title,fraction,resets_at):
        card=self._card(title); value=QLabel(f"{round(fraction*100)}%"); value.setObjectName("metric"); bar=QProgressBar(); bar.setRange(0,100); bar.setValue(round(fraction*100)); bar.setTextVisible(False)
        card.layout().addWidget(value); card.layout().addWidget(bar)
        if resets_at:
            reset=QLabel("Resets " + resets_at.astimezone().strftime("%a %H:%M")); reset.setObjectName("muted"); card.layout().addWidget(reset)
        return card
    def render(self):
        self._clear_cards(); snapshot=self.store.snapshot
        if snapshot:
            for window in snapshot.windows:self.cards.addWidget(self._usage_card(window.title,window.fraction,window.resets_at))
            if snapshot.extra and snapshot.extra.is_enabled and snapshot.extra.fraction is not None:
                self.cards.addWidget(self._usage_card("Extra usage",snapshot.extra.fraction,None))
        context=self.store.context_usage
        if context:
            self.context_value.setText(f"{context.percent}%  ·  {context.project}"); self.context_bar.setValue(context.percent)
            self.context_card.show()
        else:
            self.context_value.setText("No recent Claude Code session"); self.context_bar.setValue(0); self.context_card.show()
        self.status.setText({READY:"Connected",FAILED:"Needs attention",SIGNED_OUT:"Not connected"}.get(self.store.phase,"Loading…"))
        self.error.setText(self.store.error or self.store.sign_in_error or "")
        self.sign_button.setVisible(not self.store.is_signed_in); self.manual_button.setVisible(not self.store.is_signed_in); self.import_button.setVisible(not self.store.is_signed_in and self.store.import_available)
        self.refresh_button.setEnabled(self.store.is_signed_in)
        if self.store.last_updated:self.footer.setText("Updated " + self.store.last_updated.astimezone().strftime("%H:%M:%S") + " · Context read locally")
        session=self.store.snapshot.session if self.store.snapshot else None
        tray_text=f"Claude Usage · {session.percent}% session" if session else "Claude Usage"
        self.tray.setToolTip(tray_text)
    def _open_auth_url(self, url: str) -> None:
        if browser.open_in_chrome(url):
            return
        # Keep sign-in possible on machines without Chrome; use their configured browser.
        opened = QDesktopServices.openUrl(QUrl(url))
        if not opened:
            QMessageBox.critical(self, "Browser unavailable", "Google Chrome was not found and Windows could not open the default browser.")

    def sign_in(self):
        self.store.sign_in_with_browser(self._open_auth_url)

    def manual_sign_in(self):
        session = self.store.begin_manual_sign_in()
        self._open_auth_url(session.url)
        code, accepted = QInputDialog.getText(
            self,
            "Complete Claude sign-in",
            "After signing in, copy the code shown by Claude (including the #state suffix) and paste it here:",
        )
        if accepted and code.strip():
            self.store.complete_manual_sign_in(code.strip(), session)

    def import_login(self):self.store.import_claude_code_login()
    def showEvent(self,event):super().showEvent(event); self.store.refresh_if_stale()

class TrayApp:
    def __init__(self,app:QApplication):
        self.app=app; self.bridge=UiBridge(); self.bridge.dispatch.connect(lambda fn:fn())
        self.prefs=Preferences(); self.store=UsageStore(self.prefs,post=lambda fn:self.bridge.dispatch.emit(fn))
        icon=app.style().standardIcon(QStyle.SP_ComputerIcon); self.tray=QSystemTrayIcon(icon,app); self.tray.setToolTip("Claude Usage")
        menu=QMenu(); show=QAction("Open Claude Usage",menu); show.triggered.connect(self.toggle_panel); menu.addAction(show)
        refresh=QAction("Refresh",menu); refresh.triggered.connect(self.store.refresh); menu.addAction(refresh)
        menu.addSeparator(); quit_action=QAction("Quit",menu); quit_action.triggered.connect(app.quit); menu.addAction(quit_action)
        self.tray.setContextMenu(menu); self.tray.activated.connect(self.on_tray); self.tray.show()
        self.panel=UsagePanel(self.store,self.prefs,self.tray)
        self.timer=QTimer(); self.timer.timeout.connect(self.store.refresh); self.timer.start(self.prefs.refresh_interval*1000)
        self.store.refresh_context()
        if self.store.is_signed_in:self.store.refresh()
        else:self.panel.render()
    def on_tray(self,reason):
        if reason in (QSystemTrayIcon.Trigger,QSystemTrayIcon.DoubleClick):self.toggle_panel()
    def toggle_panel(self):
        if self.panel.isVisible():self.panel.hide()
        else:
            screen=self.app.primaryScreen().availableGeometry(); self.panel.adjustSize(); self.panel.move(screen.right()-self.panel.width()-18,screen.bottom()-self.panel.height()-55); self.panel.show(); self.panel.raise_(); self.panel.activateWindow()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--background",action="store_true"); args,_=parser.parse_known_args()
    app=QApplication(sys.argv[:1]); app.setApplicationName("Claude Usage"); app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None,"Claude Usage","Windows system tray is unavailable."); return 1
    runtime=TrayApp(app)
    if not args.background:runtime.toggle_panel()
    return app.exec()

if __name__=="__main__":raise SystemExit(main())
