import sys
import os
import json
import re
import platform
import subprocess
from pathlib import Path
from typing import Optional
import enc_app_backend
from uti import get_filename_from_filepath, strip_extension

from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QHBoxLayout, QComboBox, QCheckBox,
    QSpinBox, QLineEdit, QMessageBox, QFormLayout, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

CONFIG_FILE = "enc/config.json"
THEME_PATH = "assets/themes/"

# ---------- Utilities ----------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def natural_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def detect_system_theme():
    """Detect system theme (Light or Dark)."""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize")
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "Light" if val else "Dark"
        except Exception:
            return "Light"
    elif platform.system() == "Darwin":
        try:
            p = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True
            )
            return "Dark" if "Dark" in p.stdout else "Light"
        except Exception:
            return "Light"
    else:
        return "Light"

def apply_theme(app, theme_name: str):
    if theme_name == "System Default":
        theme_name = detect_system_theme()
    qss_file = os.path.join(THEME_PATH, f"{theme_name.lower()}.qss")
    if os.path.exists(qss_file):
        with open(qss_file, "r") as f:
            qss = f.read()
        app.setStyleSheet(qss)
    else:
        app.setStyleSheet("")  # fallback to plain white

# ---------- File Drop Label ----------
class DropLabel(QLabel):
    def __init__(self, text="Drop file here"):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 2px dashed #999; padding: 20px;")
        self.setWordWrap(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            parent = self.parent()
            if hasattr(parent, "read_file_path"):
                parent.read_file_path(file_path)

# ---------- Encryption Tab ----------
class EncryptionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.file_content: Optional[bytes] = None
        self.file_path: Optional[str] = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Upload (Drag & Drop or click Upload)"))

        self.drop_area = DropLabel("Drag & Drop file here\n\nor click Upload File")
        self.drop_area.setParent(self)
        layout.addWidget(self.drop_area)

        btn_row = QHBoxLayout()
        self.upload_btn = QPushButton("Upload File")
        self.upload_btn.clicked.connect(self.open_file_dialog)
        btn_row.addWidget(self.upload_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_loaded_file)
        btn_row.addWidget(self.clear_btn)
        layout.addLayout(btn_row)

        self.file_info_lbl = QLabel("No file loaded.")
        self.file_info_lbl.setWordWrap(True)
        layout.addWidget(self.file_info_lbl)

        self.encrypt_btn = QPushButton("Encrypt")
        self.encrypt_btn.clicked.connect(self.encrypt)
        self.encrypt_btn.setEnabled(False)
        layout.addWidget(self.encrypt_btn)

        layout.addWidget(QLabel("Process output (logs / errors)"))
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setMinimumHeight(180)
        layout.addWidget(self.output_box)

        self.setLayout(layout)

    def read_file_path(self, path: str):
        self.read_file(path)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.read_file(file_path)

    def read_file(self, file_path: str):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            self.file_content = data
            self.file_path = file_path
            size = len(data)
            self.file_info_lbl.setText(f"Loaded: {file_path}\nSize: {size} bytes")
            self.output_box.append(f"[INFO] Loaded file: {file_path}")
            self.encrypt_btn.setEnabled(True)
        except Exception as e:
            self.output_box.append(f"[ERROR] Could not read file: {e}")
            self.clear_loaded_file()

    def clear_loaded_file(self):
        self.file_content = None
        self.file_path = None
        self.file_info_lbl.setText("No file loaded.")
        self.output_box.append("\n--- Cleared loaded file ---\n")
        self.encrypt_btn.setEnabled(False)

    def encrypt(self):
        if not self.file_content or not self.file_path:
            QMessageBox.warning(self, "No file", "Please upload a file first.")
            return
        self.output_box.append("[INFO] Starting encryption...")
        try:
            enc_app_backend.GlobalData.status = ""
            enc_app_backend.start_encryption(self.file_content, self.file_path)
            status_msg = enc_app_backend.GlobalData.status.strip()
            if status_msg:
                self.output_box.append(f"[STATUS] {status_msg}")
            else:
                self.output_box.append("[DONE] Encryption completed successfully.")
        except Exception as e:
            self.output_box.append(f"[ERROR] Encryption failed: {e}")

# ---------- Log Tab ----------
class LogTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        top_row = QHBoxLayout()
        self.load_btn = QPushButton("Load logs")
        self.load_btn.clicked.connect(self.load_logs)
        top_row.addWidget(self.load_btn)
        layout.addLayout(top_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.button_container = QWidget()
        self.grid_layout = QGridLayout(self.button_container)
        self.scroll_area.setWidget(self.button_container)
        layout.addWidget(self.scroll_area)

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMinimumHeight(180)
        layout.addWidget(self.log_viewer)

        self.setLayout(layout)
        self.log_map = {}
        self.load_logs()

    def clear_grid(self):
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.log_map.clear()

    def add_buttons(self, entries):
        for i, (label, path) in enumerate(entries):
            btn = QPushButton(label)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked, p=path: self.open_log(p))
            row, col = divmod(i, 2)
            self.grid_layout.addWidget(btn, row, col)
            self.log_map[label] = path

    def load_logs(self):
        candidate = Path(os.getcwd()) / "enc" / "log"
        self.clear_grid()
        if candidate.exists() and candidate.is_dir():
            files = [p for p in candidate.iterdir() if p.is_file() and p.suffix == ".log"]
            if not files:
                self.add_buttons([("(no logs found)", None)])
            else:
                entries = [(strip_extension(get_filename_from_filepath(str(p))), p) for p in files]
                entries.sort(key=lambda x: natural_key(x[0]))
                self.add_buttons(entries)
        else:
            self.add_buttons([("No logs", None)])

    def open_log(self, path):
        if path is None:
            self.log_viewer.setPlainText("No real log to open.")
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                self.log_viewer.setPlainText(f.read())
        except Exception as e:
            self.log_viewer.setPlainText(f"Could not open log: {e}")

# ---------- Settings Tab ----------
class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.subtabs = QTabWidget()

        # Make subtabs expand equally across the width
        self.subtabs.tabBar().setExpanding(True)

        self.subtabs.addTab(self.make_encryption_settings(), "Encryption Options")
        self.subtabs.addTab(self.make_logging_settings(), "Logging")
        self.subtabs.addTab(self.make_appearance_settings(), "Appearance")
        layout.addWidget(self.subtabs)

        # Save / Apply button
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_and_apply)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)
        self.load_settings()

    # Encryption settings
    def make_encryption_settings(self):
        box = QWidget()
        form = QFormLayout()
        self.total_keys_spin = QSpinBox()
        self.total_keys_spin.setRange(2, 1000)
        form.addRow("Total keys:", self.total_keys_spin)

        self.min_keys_spin = QSpinBox()
        self.min_keys_spin.setRange(1, 500)
        form.addRow("Min keys required:", self.min_keys_spin)

        box.setLayout(form)
        return box

    # Logging settings
    def make_logging_settings(self):
        box = QWidget()
        layout = QVBoxLayout()
        path_row = QHBoxLayout()
        self.log_path_edit = QLineEdit()
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_log_path)
        path_row.addWidget(self.log_path_edit)
        path_row.addWidget(browse)
        layout.addLayout(path_row)

        key_row = QHBoxLayout()
        self.key_path_edit = QLineEdit()
        browse_key = QPushButton("Browse")
        browse_key.clicked.connect(self.browse_key_path)
        key_row.addWidget(self.key_path_edit)
        key_row.addWidget(browse_key)
        layout.addLayout(key_row)

        self.chk_log_key_count = QCheckBox("Log key count")
        self.chk_log_min_keys = QCheckBox("Log min required keys")
        self.chk_log_hash = QCheckBox("Log hash (encrypted)")
        self.chk_log_time = QCheckBox("Log operation time")
        self.chk_log_key_loc = QCheckBox("Log key location")
        for chk in [self.chk_log_key_count, self.chk_log_min_keys, self.chk_log_hash,
                    self.chk_log_time, self.chk_log_key_loc]:
            layout.addWidget(chk)

        box.setLayout(layout)
        return box

    def browse_log_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Log Directory")
        if path:
            self.log_path_edit.setText(path)

    def browse_key_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Key Storage Directory")
        if path:
            self.key_path_edit.setText(path)

    # Appearance settings
    def make_appearance_settings(self):
        box = QWidget()
        form = QFormLayout()
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 48)
        form.addRow("Font size:", self.font_spin)

        self.btn_size_spin = QSpinBox()
        self.btn_size_spin.setRange(8, 48)
        form.addRow("Button size:", self.btn_size_spin)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System Default", "Light", "Dark"])
        form.addRow("Theme:", self.theme_combo)

        box.setLayout(form)
        return box

    def load_settings(self):
        cfg = load_config()
        self.total_keys_spin.setValue(cfg.get("total_keys", 10))
        self.min_keys_spin.setValue(cfg.get("min_keys", 5))
        self.log_path_edit.setText(cfg.get("log_location", "enc/log/"))
        self.key_path_edit.setText(cfg.get("enc_file_location", "enc/ops/enc_files/"))
        self.chk_log_key_count.setChecked(cfg.get("log_key_count", True))
        self.chk_log_min_keys.setChecked(cfg.get("log_min_required_keys", True))
        self.chk_log_hash.setChecked(cfg.get("log_enc_file_hash", True))
        self.chk_log_time.setChecked(cfg.get("log_operation_time", True))
        self.chk_log_key_loc.setChecked(cfg.get("log_key_location", True))

        # Appearance
        self.font_spin.setValue(cfg.get("font_size", 12))
        self.btn_size_spin.setValue(cfg.get("btn_size", 12))
        theme = cfg.get("theme", "System Default")
        idx = self.theme_combo.findText(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        # Apply immediately
        self.apply_appearance()

    def get_current_config(self):
        return {
            "total_keys": self.total_keys_spin.value(),
            "min_keys": self.min_keys_spin.value(),
            "log_location": self.log_path_edit.text(),
            "enc_file_location": self.key_path_edit.text(),
            "log_key_count": self.chk_log_key_count.isChecked(),
            "log_min_required_keys": self.chk_log_min_keys.isChecked(),
            "log_enc_file_hash": self.chk_log_hash.isChecked(),
            "log_operation_time": self.chk_log_time.isChecked(),
            "log_key_location": self.chk_log_key_loc.isChecked(),
            "font_size": self.font_spin.value(),
            "btn_size": self.btn_size_spin.value(),
            "theme": self.theme_combo.currentText()
        }

    def save_and_apply(self):
        cfg = self.get_current_config()
        save_config(cfg)
        self.apply_appearance()
        QMessageBox.information(self, "Settings", "Settings saved and applied.")

    def apply_appearance(self):
        app = QApplication.instance()
        cfg = self.get_current_config()
        apply_theme(app, cfg["theme"])
        font_size = cfg["font_size"]
        btn_size = cfg["btn_size"]
        app.setStyleSheet(app.styleSheet() + f"QWidget {{ font-size: {font_size}pt; }} QPushButton {{ font-size: {btn_size}pt; }}")

# ---------- Main Window ----------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Encryption System")
        self.resize(900, 650)
        self.setWindowIcon(QIcon("assets/images/enc_app_frontend.png"))
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Make main tabs expand equally across the width
        self.tabs.tabBar().setExpanding(True)

        self.tabs.addTab(EncryptionTab(), "Encryption")
        self.tabs.addTab(LogTab(), "Log")
        self.tabs.addTab(SettingsTab(), "Settings")
        layout.addWidget(self.tabs)
        self.setLayout(layout)

# ---------- Run ----------
def main():
    app = QApplication(sys.argv)

    cfg = load_config()
    theme = cfg.get("theme", "System Default")
    apply_theme(app, theme)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


