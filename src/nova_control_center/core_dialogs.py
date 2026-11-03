"""Core management dialogs: SQLite logs and optional local PIN lock."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLineEdit,
    QDialogButtonBox,QTableWidget,QTableWidgetItem,QHeaderView,QSpinBox,
    QComboBox,QFormLayout,QMessageBox,QInputDialog
)
from .control_panels import NovaDialog

class LogsDialog(NovaDialog):
    def __init__(self,palette,log_store,preferences,parent=None):
        super().__init__("NOVA / JOURNAL SYSTÈME",palette,parent)
        self.setMinimumSize(780,490)
        self.resize(900,550)
        self.logs=log_store
        self.prefs=preferences
        bar=QHBoxLayout()
        self.level=QComboBox()
        self.level.addItems(["ALL","DEBUG","INFO","WARNING","ERROR","AUDIT"])
        bar.addWidget(QLabel("Niveau"))
        bar.addWidget(self.level)
        self.find=QLineEdit()
        self.find.setPlaceholderText("Rechercher dans les messages…")
        bar.addWidget(self.find,1)
        refresh=QPushButton("↻ Actualiser")
        refresh.clicked.connect(self.reload)
        bar.addWidget(refresh)
        self.content.addLayout(bar)
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(["Date UTC","Niveau","Module","Événement","Message"])
        self.table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.content.addWidget(self.table,1)
        self.level.currentTextChanged.connect(self.reload)
        self.find.returnPressed.connect(self.reload)
        footer=QHBoxLayout()
        footer.addWidget(QLabel(f"SQLite local · rétention {preferences.log_retention_days} jours"))
        footer.addStretch()
        close=QPushButton("Fermer")
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        self.content.addLayout(footer)
        self.reload()
    def reload(self):
        level=self.level.currentText()
        records=self.logs.recent(limit=400,
                                 level=level if level!="ALL" else None,
                                 contains=self.find.text().strip() or None)
        self.table.setRowCount(len(records))
        for row,record in enumerate(records):
            for col,key in enumerate(("ts","level","source","event","message")):
                self.table.setItem(row,col,QTableWidgetItem(str(record.get(key,""))))

class CorePreferencesDialog(NovaDialog):
    def __init__(self,palette,store,preferences,session_manager,on_change,parent=None):
        super().__init__("NOVA / CONFIGURATION DU CORE",palette,parent)
        self.store=store
        self.current=preferences
        self.sessions=session_manager
        self.callback=on_change
        form=QFormLayout()
        self.days=QSpinBox()
        self.days.setRange(1,365)
        self.days.setValue(preferences.log_retention_days)
        form.addRow("Conservation logs (jours)",self.days)
        self.limit=QSpinBox()
        self.limit.setRange(1000,1000000)
        self.limit.setSingleStep(1000)
        self.limit.setValue(preferences.log_max_records)
        form.addRow("Nombre maximum de logs",self.limit)
        self.idle=QSpinBox()
        self.idle.setRange(0,240)
        self.idle.setSuffix(" minutes (0 = non)")
        self.idle.setValue(preferences.lock_after_minutes)
        form.addRow("Verrouillage inactivité",self.idle)
        self.content.addLayout(form)
        self.pin_label=QLabel("Verrouillage facultatif : crée un PIN local de 6 à 16 chiffres.")
        self.pin_label.setWordWrap(True)
        self.content.addWidget(self.pin_label)
        pin_row=QHBoxLayout()
        self.new_pin=QLineEdit()
        self.new_pin.setPlaceholderText("Nouveau PIN")
        self.new_pin.setEchoMode(QLineEdit.EchoMode.Password)
        pin_row.addWidget(self.new_pin)
        self.confirm_pin=QLineEdit()
        self.confirm_pin.setPlaceholderText("Confirmer PIN")
        self.confirm_pin.setEchoMode(QLineEdit.EchoMode.Password)
        pin_row.addWidget(self.confirm_pin)
        self.content.addLayout(pin_row)
        pin_button=QPushButton("Créer / remplacer le PIN")
        pin_button.clicked.connect(self.save_pin)
        self.content.addWidget(pin_button)
        self.content.addStretch()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|
                                 QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        self.content.addWidget(buttons)
    def save_pin(self):
        pin=self.new_pin.text()
        if pin!=self.confirm_pin.text():
            QMessageBox.warning(self,"PIN","Les deux PIN ne correspondent pas.")
            return
        if self.sessions.has_pin():
            old,ok=QInputDialog.getText(self,"Confirmation PIN",
                "Ancien PIN requis :",QLineEdit.EchoMode.Password)
            if not ok:return
            if not self.sessions.unlock(old):
                QMessageBox.warning(self,"PIN","Ancien PIN incorrect.")
                return
        try:self.sessions.set_pin(pin)
        except ValueError as exc:
            QMessageBox.warning(self,"PIN",str(exc))
            return
        self.new_pin.clear()
        self.confirm_pin.clear()
        self.pin_label.setText("✓ PIN enregistré, le bouton Verrouiller est disponible.")
    def save(self):
        self.current.log_retention_days=self.days.value()
        self.current.log_max_records=self.limit.value()
        self.current.lock_after_minutes=self.idle.value()
        self.store.save(self.current)
        self.callback()
        self.accept()

class UnlockDialog(NovaDialog):
    def __init__(self,palette,sessions,parent=None):
        super().__init__("NOVA / SESSION VERROUILLÉE",palette,parent)
        self.sessions=sessions
        self.setMinimumSize(490,250)
        self.resize(510,255)
        label=QLabel("Déverrouillage local : entre ton PIN NOVA.")
        self.content.addWidget(label)
        self.pin=QLineEdit()
        self.pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin.setPlaceholderText("PIN")
        self.content.addWidget(self.pin)
        self.status=QLabel("")
        self.content.addWidget(self.status)
        row=QHBoxLayout()
        close=QPushButton("Quitter NOVA")
        close.clicked.connect(self.reject)
        row.addWidget(close)
        unlock=QPushButton("Déverrouiller")
        unlock.clicked.connect(self.attempt)
        row.addWidget(unlock)
        self.content.addLayout(row)
        self.pin.returnPressed.connect(self.attempt)
    def attempt(self):
        if self.sessions.unlock(self.pin.text()):
            self.pin.clear()
            self.accept()
        else:
            self.pin.clear()
            self.status.setText("PIN incorrect ou tentative temporairement bloquée.")
