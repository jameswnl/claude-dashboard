#!/usr/bin/env python3
"""macOS menu bar app for Claude Code Dashboard."""

import subprocess
import signal
import sys
import webbrowser

import rumps

PORT = 8420
SERVER_PROCESS = None


class DashboardApp(rumps.App):
    def __init__(self):
        super().__init__("Claude Dashboard", icon=None, title="C>_")
        self.menu = [
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Start Server", callback=self.start_server),
            rumps.MenuItem("Stop Server", callback=self.stop_server),
            None,  # separator
            rumps.MenuItem("Status: Stopped"),
        ]
        self._update_status()

    def _is_running(self):
        global SERVER_PROCESS
        if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
            return True
        # Check if something else is serving on the port
        try:
            import urllib.request
            urllib.request.urlopen(f"http://localhost:{PORT}/", timeout=1)
            return True
        except Exception:
            return False

    def _update_status(self):
        running = self._is_running()
        status = self.menu["Status: Stopped"] if "Status: Stopped" in self.menu else self.menu["Status: Running"]
        new_title = "Status: Running" if running else "Status: Stopped"
        status.title = new_title
        self.menu["Start Server"].set_callback(None if running else self.start_server)
        self.menu["Stop Server"].set_callback(self.stop_server if running else None)
        self.title = "C>_" if running else "C>."

    @rumps.clicked("Open Dashboard")
    def open_dashboard(self, sender):
        if not self._is_running():
            self.start_server(sender)
        webbrowser.open(f"http://localhost:{PORT}")

    @rumps.clicked("Start Server")
    def start_server(self, sender):
        global SERVER_PROCESS
        if self._is_running():
            rumps.notification("Claude Dashboard", "", "Server is already running")
            return
        SERVER_PROCESS = subprocess.Popen(
            [sys.executable, "-m", "claude_dashboard.server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        rumps.notification("Claude Dashboard", "", f"Server started on port {PORT}")
        self._update_status()

    @rumps.clicked("Stop Server")
    def stop_server(self, sender):
        global SERVER_PROCESS
        if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
            SERVER_PROCESS.terminate()
            SERVER_PROCESS.wait(timeout=5)
            SERVER_PROCESS = None
            rumps.notification("Claude Dashboard", "", "Server stopped")
        self._update_status()


def main():
    DashboardApp().run()


if __name__ == "__main__":
    main()
