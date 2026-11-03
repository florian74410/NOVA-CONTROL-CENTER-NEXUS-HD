"""Asynchronous Qt client for the IATB-CLI Unix domain socket.

One shared connection per HUB; responses are routed to frame callbacks by request ID.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtNetwork import QLocalSocket

class HubSocketClient(QObject):
    result = Signal(str, object)
    failed = Signal(str, str)
    connected = Signal()
    disconnected = Signal()

    def __init__(self, socket_path=None, parent=None):
        super().__init__(parent)
        self.path = str(socket_path or Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "iatb-cli.sock")
        self.socket = QLocalSocket(self)
        self.socket.readyRead.connect(self._read)
        self.socket.connected.connect(self.connected.emit)
        self.socket.disconnected.connect(self.disconnected.emit)
        self.socket.errorOccurred.connect(self._socket_error)
        self.buffer = bytearray()
        self.pending = {}
        self.counter = 0

    def connect_server(self):
        if self.socket.state() == QLocalSocket.LocalSocketState.UnconnectedState:
            self.socket.connectToServer(self.path)

    def request(self, method, params=None, timeout_ms=30000):
        self.counter += 1
        ident = str(self.counter)
        payload = {"n3xv5": 1, "id": ident, "app": "iatb-cli",
                   "method": method, "params": params or {}}
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._timeout(ident))
        self.pending[ident] = (method, timer)
        timer.start(timeout_ms)
        if self.socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
            # Send only after connected; never block Qt's UI thread.
            def send_when_connected():
                try:
                    self.socket.connected.disconnect(send_when_connected)
                except (TypeError, RuntimeError):
                    pass
                if ident in self.pending:
                    self.socket.write((json.dumps(payload, ensure_ascii=False)+"\n").encode())
            self.socket.connected.connect(send_when_connected)
            self.connect_server()
        else:
            self.socket.write((json.dumps(payload, ensure_ascii=False)+"\n").encode())
        return ident

    def _timeout(self, ident):
        entry = self.pending.pop(ident, None)
        if entry:
            entry[1].deleteLater()
            self.failed.emit(entry[0], "Socket request timeout")

    def _socket_error(self, error):
        message = self.socket.errorString()
        for ident, (method, timer) in list(self.pending.items()):
            timer.stop()
            timer.deleteLater()
            self.failed.emit(method, message)
        self.pending.clear()

    def _read(self):
        self.buffer.extend(bytes(self.socket.readAll()))
        if len(self.buffer) > 1024*1024:
            self.buffer.clear()
            self._socket_error(None)
            self.socket.abort()
            return
        while b"\n" in self.buffer:
            line, _, rest = self.buffer.partition(b"\n")
            self.buffer = bytearray(rest)
            try:
                response = json.loads(line)
                ident = str(response["id"])
                entry = self.pending.pop(ident, None)
                if not entry:
                    continue
                method, timer = entry
                timer.stop()
                timer.deleteLater()
                if "error" in response:
                    self.failed.emit(method, str(response["error"]))
                else:
                    self.result.emit(method, response.get("result", {}))
            except (ValueError, KeyError, TypeError):
                continue
