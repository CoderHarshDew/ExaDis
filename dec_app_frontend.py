# dec_app_frontend.py
import sys
import os
import json
import re
import platform
import subprocess
from pathlib import Path
from typing import Optional, List
import dec_app_backend
from uti import get_filename_from_filepath, strip_extension
import uti

from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QHBoxLayout, QComboBox, QCheckBox,
    QSpinBox, QLineEdit, QMessageBox, QFormLayout, QScrollArea, QGridLayout, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

CONFIG_FILE = "dec/config.json"
THEME_PATH = "assets/themes/"

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
        app.setStyleSheet("")

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

# ---------- Decryption Tab ----------
class DecryptionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.enc_content: Optional[bytes] = None
        self.enc_path: Optional[str] = None
        self.header: Optional[dict] = None
        self.key_shares: List[str] = []

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Decryption (Upload encrypted file, then supply key shares)"))

        # Box 1 - Encrypted file upload
        self.drop_area = DropLabel("Drag & Drop encrypted file here\n\nor click Upload File")
        self.drop_area.setParent(self)
        layout.addWidget(self.drop_area)

        btn_row = QHBoxLayout()
        self.upload_btn = QPushButton("Upload Encrypted File")
        self.upload_btn.clicked.connect(self.open_enc_file_dialog)
        btn_row.addWidget(self.upload_btn)

        self.clear_enc_btn = QPushButton("Clear File")
        self.clear_enc_btn.clicked.connect(self.clear_loaded_enc)
        btn_row.addWidget(self.clear_enc_btn)
        layout.addLayout(btn_row)

        self.file_info_lbl = QLabel("No encrypted file loaded.")
        self.file_info_lbl.setWordWrap(True)
        layout.addWidget(self.file_info_lbl)

        # Box 2 - Keys upload / paste
        layout.addWidget(QLabel("Provide key shares (drag & drop multiple files or paste):"))

        keys_row = QHBoxLayout()
        self.keys_drop = DropLabel("Drag & drop key files here\n(or click Upload Keys)")
        self.keys_drop.setParent(self)
        keys_row.addWidget(self.keys_drop)

        keys_btns = QVBoxLayout()
        self.upload_keys_btn = QPushButton("Upload Keys")
        self.upload_keys_btn.clicked.connect(self.open_keys_dialog)
        keys_btns.addWidget(self.upload_keys_btn)

        self.paste_keys_btn = QPushButton("Paste Keys")
        self.paste_keys_btn.clicked.connect(self.open_paste_keys_dialog)
        keys_btns.addWidget(self.paste_keys_btn)

        self.clear_keys_btn = QPushButton("Clear Keys")
        self.clear_keys_btn.clicked.connect(self.clear_keys)
        keys_btns.addWidget(self.clear_keys_btn)

        keys_row.addLayout(keys_btns)
        layout.addLayout(keys_row)

        self.keys_list_view = QTextEdit()
        self.keys_list_view.setReadOnly(True)
        self.keys_list_view.setMaximumHeight(120)
        layout.addWidget(self.keys_list_view)

        # Decrypt button
        self.decrypt_btn = QPushButton("Decrypt")
        self.decrypt_btn.clicked.connect(self.decrypt)
        self.decrypt_btn.setEnabled(False)
        layout.addWidget(self.decrypt_btn)

        # Box 3 - process output
        layout.addWidget(QLabel("Process output (logs / errors)"))
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setMinimumHeight(180)
        layout.addWidget(self.output_box)

        self.setLayout(layout)

    # file handlers
    def read_file_path(self, path: str):
        # called by drop label
        self.read_enc_file(path)

    def open_enc_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Encrypted File")
        if file_path:
            self.read_enc_file(file_path)

    def read_enc_file(self, file_path: str):
        try:
            header, data = uti.fetch_file(file_path)
            if header is None or data is None:
                self.output_box.append("[ERROR] Could not parse encrypted file header/data.")
                return
            self.header = header
            self.enc_content = data
            self.enc_path = file_path
            self.file_info_lbl.setText(f"Loaded: {file_path}\nMetadata: {json.dumps(header)}")
            self.output_box.append(f"[INFO] Loaded encrypted file: {file_path}")
            self._update_decrypt_button_state()
        except Exception as e:
            self.output_box.append(f"[ERROR] Could not read encrypted file: {e}")
            self.clear_loaded_enc()

    def clear_loaded_enc(self):
        self.enc_content = None
        self.enc_path = None
        self.header = None
        self.file_info_lbl.setText("No encrypted file loaded.")
        self.output_box.append("\n--- Cleared loaded encrypted file ---\n")
        self._update_decrypt_button_state()

    # keys handling
    def open_keys_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select key files (select multiple)")
        if files:
            added = 0
            for f in files:
                try:
                    with open(f, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read().strip()
                        if content:
                            self.key_shares.append(content)
                            added += 1
                except Exception as e:
                    self.output_box.append(f"[WARN] Could not read key file {f}: {e}")
            self._refresh_keys_view()
            self.output_box.append(f"[INFO] Added {added} key files.")
            self._update_decrypt_button_state()

    def open_paste_keys_dialog(self):
        # open a simple dialog to paste multiple keys (one per line)
        txt, ok = QInputDialog.getMultiLineText(self, "Paste key shares",
                                                "Paste one key per line (or many lines per key separated by blank line):")
        if ok and txt:
            # split by blank line (double newline) or single-line keys
            blocks = [b.strip() for b in re.split(r'\n\s*\n', txt) if b.strip()]
            added = 0
            for b in blocks:
                self.key_shares.append(b)
                added += 1
            self._refresh_keys_view()
            self.output_box.append(f"[INFO] Pasted {added} key shares.")
            self._update_decrypt_button_state()

    def clear_keys(self):
        self.key_shares = []
        self._refresh_keys_view()
        self.output_box.append("\n--- Cleared keys ---\n")
        self._update_decrypt_button_state()

    def _refresh_keys_view(self):
        self.keys_list_view.clear()
        for i, k in enumerate(self.key_shares, start=1):
            snippet = k.replace("\n", " ")[:150]
            self.keys_list_view.append(f"Key {i}: {snippet}")

    def _update_decrypt_button_state(self):
        enabled = self.enc_content is not None and len(self.key_shares) > 0 and self.header is not None
        self.decrypt_btn.setEnabled(enabled)

    def decrypt(self):
        if not self.enc_content or not self.enc_path or not self.header:
            QMessageBox.warning(self, "Missing data", "Please upload an encrypted file and keys first.")
            return

        # Determine min_keys from header
        min_keys = self.header.get("min_keys", None)
        if min_keys is None:
            self.output_box.append("[WARN] Encrypted file header does not contain 'min_keys'. Assuming 1.")
            min_keys = 1

        if len(self.key_shares) < min_keys:
            QMessageBox.warning(self, "Insufficient keys", f"Provided {len(self.key_shares)} keys but file requires minimum {min_keys}.")
            self.output_box.append(f"[ERROR] Insufficient keys: provided {len(self.key_shares)}, required {min_keys}")
            return
        try:
            dec_app_backend.GlobalData.status = ""
            self.output_box.append("[INFO] Starting decryption...")
            dec_app_backend.start_decryption(self.enc_content, self.enc_path, self.header, self.key_shares)
            status_msg = dec_app_backend.GlobalData.status.strip()
            if status_msg:
                self.output_box.append(f"[STATUS] {status_msg}")
            else:
                self.output_box.append("[DONE] Decryption completed (check dec/ops/... for results).")
        except Exception as e:
            self.output_box.append(f"[ERROR] Decryption failed: {e}")

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
        candidate = Path(os.getcwd()) / "dec" / "log"
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
        self.subtabs.tabBar().setExpanding(True)

        self.subtabs.addTab(self.make_logging_settings(), "Logging")
        self.subtabs.addTab(self.make_appearance_settings(), "Appearance")
        layout.addWidget(self.subtabs)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_and_apply)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)
        self.load_settings()

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

        box.setLayout(layout)
        return box

    def browse_log_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Log Directory")
        if path:
            self.log_path_edit.setText(path)

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
        self.log_path_edit.setText(cfg.get("log_location", "dec/log/"))
        self.font_spin.setValue(cfg.get("font_size", 12))
        self.btn_size_spin.setValue(cfg.get("btn_size", 12))
        theme = cfg.get("theme", "System Default")
        idx = self.theme_combo.findText(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.apply_appearance()

    def get_current_config(self):
        return {
            "log_location": self.log_path_edit.text(),
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
        self.setWindowTitle("Decryption System")
        self.resize(900, 650)
        self.setWindowIcon(QIcon("assets/images/dec_app_frontend.png"))
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.tabBar().setExpanding(True)

        self.tabs.addTab(DecryptionTab(), "Decryption")
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


