"""Asynchronous, one-shot CLI process bridge. No CLI GUI is loaded by the HUB."""
from __future__ import annotations
import os
from PySide6.QtCore import QObject,QProcess,Signal,QTimer
from n3xv5_core.cli_protocol import request,encode,decode,ProtocolError

class CliRunner(QObject):
    finished=Signal(str,object)
    failed=Signal(str,str)
    def __init__(self,program,args=(),app_id="iatb-cli",parent=None):
        super().__init__(parent)
        self.program=program;self.args=list(args);self.app_id=app_id
        self.active={};self.counter=0
    def call(self,method,params=None,timeout_ms=10000):
        self.counter+=1
        ident=str(self.counter)
        payload=encode(request(self.app_id,method,params,ident))
        proc=QProcess(self)
        proc.setProgram(self.program)
        proc.setArguments(self.args)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        state={"process":proc,"stdout":bytearray(),"stderr":bytearray(),"timedout":False}
        self.active[ident]=state
        timer=QTimer(proc);timer.setSingleShot(True)
        def timeout():
            state["timedout"]=True
            if proc.state()!=QProcess.ProcessState.NotRunning:proc.kill()
        timer.timeout.connect(timeout)
        def read():
            state["stdout"].extend(bytes(proc.readAllStandardOutput()))
            state["stderr"].extend(bytes(proc.readAllStandardError())[:4096])
            if len(state["stdout"])>1024*1024:proc.kill()
        proc.readyReadStandardOutput.connect(read)
        proc.readyReadStandardError.connect(read)
        def done(code,status):
            timer.stop();read();self.active.pop(ident,None)
            try:
                if state["timedout"]:raise ProtocolError("CLI timeout")
                if code!=0 or status!=QProcess.ExitStatus.NormalExit:
                    raise ProtocolError("CLI exited with code "+str(code))
                data=decode(bytes(state["stdout"]))
                if data["id"]!=ident:raise ProtocolError("Mismatched response id")
                if "error" in data:raise ProtocolError(str(data["error"]))
                if "result" not in data:raise ProtocolError("Missing result")
                self.finished.emit(method,data["result"])
            except (ProtocolError,ValueError) as exc:self.failed.emit(method,str(exc))
            proc.deleteLater()
        proc.finished.connect(done)
        proc.errorOccurred.connect(lambda e: self.failed.emit(method,"CLI launch error: "+str(e)) if proc.state()==QProcess.ProcessState.NotRunning else None)
        proc.start()
        if not proc.waitForStarted(100):return ident
        proc.write(payload);proc.closeWriteChannel()
        timer.start(timeout_ms)
        return ident
    def cancel_all(self):
        for state in list(self.active.values()):state["process"].kill()
