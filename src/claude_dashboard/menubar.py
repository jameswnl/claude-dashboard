#!/usr/bin/env python3
"""macOS menu bar app for Claude Code Dashboard."""

import os
import subprocess
import signal
import sys
import webbrowser
from pathlib import Path

import rumps

PORT = 8420
SERVER_PROCESS = None
PID_FILE = Path.home() / ".claude" / f"dashboard-{PORT}.pid"


def _write_pid(pid):
    """Write server PID to file."""
    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(pid))
    except OSError:
        pass


def _read_pid():
    """Read server PID from file. Returns int or None."""
    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is still alive
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        _clear_pid()
        return None


def _clear_pid():
    """Remove PID file."""
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


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
        # Check PID file for externally started server
        return _read_pid() is not None

    def _update_status(self):
        running = self._is_running()
        for key in ("Status: Stopped", "Status: Running"):
            if key in self.menu:
                self.menu[key].title = "Status: Running" if running else "Status: Stopped"
                break
        self.menu["Start Server"].set_callback(None if running else self.start_server)
        self.menu["Stop Server"].set_callback(self.stop_server if running else None)
        self.title = "C>_" if running else "C>."

    @rumps.timer(5)
    def _refresh_status(self, _):
        self._update_status()

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
        _write_pid(SERVER_PROCESS.pid)
        rumps.notification("Claude Dashboard", "", f"Server started on port {PORT}")
        self._update_status()

    @rumps.clicked("Stop Server")
    def stop_server(self, sender):
        global SERVER_PROCESS
        stopped = False
        pid_to_kill = None

        if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
            pid_to_kill = SERVER_PROCESS.pid
            SERVER_PROCESS.terminate()
            try:
                SERVER_PROCESS.wait(timeout=5)
                stopped = True
            except subprocess.TimeoutExpired:
                SERVER_PROCESS.kill()
                SERVER_PROCESS.wait(timeout=3)
                stopped = True
            SERVER_PROCESS = None
        else:
            # Try PID file for externally started server
            pid_to_kill = _read_pid()
            if pid_to_kill:
                try:
                    os.kill(pid_to_kill, signal.SIGTERM)
                    # Wait for process to actually exit
                    for _ in range(50):  # up to 5 seconds
                        import time
                        time.sleep(0.1)
                        try:
                            os.kill(pid_to_kill, 0)
                        except OSError:
                            stopped = True
                            break
                    if not stopped:
                        os.kill(pid_to_kill, signal.SIGKILL)
                        stopped = True
                except OSError:
                    # Process already gone
                    stopped = True

        _clear_pid()
        if stopped:
            rumps.notification("Claude Dashboard", "", "Server stopped")
        else:
            rumps.notification("Claude Dashboard", "", "No server process to stop")
        self._update_status()


def main():
    DashboardApp().run()


if __name__ == "__main__":
    main()
