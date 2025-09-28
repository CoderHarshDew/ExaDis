import sys
import os
import json
import platform
import subprocess
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QHBoxLayout, QLineEdit, QMessageBox, QFormLayout,
    QScrollArea, QGridLayout, QDialog, QStackedLayout, QTextEdit, QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

import server_system_backend as backend
from uti import get_filename_from_filepath, strip_extension

# -------------------- Global constants --------------------
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "server_system" / "config.json"
THEME_PATH = BASE_DIR / "assets" / "themes"
ICON_PATH = BASE_DIR / "assets" / "images" / "server.png"

# Tab name constants (explicitly define main vs sub tabs)
TAB_UPLOAD = "Upload"
TAB_FILES = "Files"
TAB_REQUESTS = "Requests"
TAB_SETTINGS = "Settings"
TAB_SERVER_STATUS = "Server Status"

SUBTAB_APPEARANCE = "Appearance"
SUBTAB_ACCOUNT = "Account Settings"


# -------------------- Utilities --------------------
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"theme": "System Default"}
    return {"theme": "System Default"}


def save_config(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


def detect_system_theme():
    """Return 'Light' or 'Dark' heuristically based on platform."""
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "Light" if val else "Dark"
        elif platform.system() == "Darwin":
            p = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                               capture_output=True, text=True)
            return "Dark" if "Dark" in p.stdout else "Light"
    except Exception:
        pass
    return "Light"


def apply_theme(app: QApplication, theme_name: str):
    """Apply QSS theme from THEME_PATH; System Default maps to detected theme."""
    if theme_name == "System Default":
        theme_name = detect_system_theme()
    qss_file = THEME_PATH / f"{theme_name.lower()}.qss"
    if qss_file.exists():
        try:
            with open(qss_file, "r") as f:
                app.setStyleSheet(f.read())
        except Exception:
            app.setStyleSheet("")
    else:
        app.setStyleSheet("")


# -------------------- DropLabel --------------------
class DropLabel(QLabel):
    def __init__(self, text="Drop file here"):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 2px dashed #888; padding: 20px;")
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


# -------------------- Auth Dialog --------------------
class AuthDialog(QDialog):
    """Login / Signup dialog with Username, Account ID, Password, Confirm Password."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign Up / Log In")
        self.resize(460, 420)
        layout = QVBoxLayout()

        self.stack = QStackedLayout()
        self._make_login_widget()
        self._make_signup_widget()

        layout.addLayout(self.stack)

        btn_row = QHBoxLayout()
        self.to_login_btn = QPushButton("Go to Login")
        self.to_login_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.to_signup_btn = QPushButton("Go to Sign Up")
        self.to_signup_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_row.addWidget(self.to_login_btn)
        btn_row.addWidget(self.to_signup_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.login_success = False
        self.logged_in_user = None

    def _make_login_widget(self):
        w = QWidget()
        form = QFormLayout()
        self.login_username = QLineEdit()
        self.login_id = QLineEdit()
        self.login_pw = QLineEdit()
        self.login_pw.setEchoMode(QLineEdit.Password)

        form.addRow("Username:", self.login_username)
        form.addRow("Account ID:", self.login_id)
        form.addRow("Password:", self.login_pw)

        self.login_msg = QLabel("")
        form.addRow(self.login_msg)

        login_btn = QPushButton("Log In")
        login_btn.clicked.connect(self.attempt_login)
        form.addRow(login_btn)

        w.setLayout(form)
        self.stack.addWidget(w)

    def _make_signup_widget(self):
        w = QWidget()
        form = QFormLayout()
        self.su_username = QLineEdit()
        self.su_id = QLineEdit()
        self.su_pw = QLineEdit()
        self.su_pw.setEchoMode(QLineEdit.Password)
        self.su_pw_confirm = QLineEdit()
        self.su_pw_confirm.setEchoMode(QLineEdit.Password)
        self.su_email = QLineEdit()
        self.su_phone = QLineEdit()

        form.addRow("Username:", self.su_username)
        form.addRow("Account ID:", self.su_id)
        form.addRow("Password:", self.su_pw)
        form.addRow("Confirm Password:", self.su_pw_confirm)
        form.addRow("Email:", self.su_email)
        form.addRow(QLabel("<small>OTP via email - work in progress</small>"))
        form.addRow("Phone (10 digits):", self.su_phone)
        form.addRow(QLabel("<small>Phone OTP - work in progress</small>"))

        self.signup_msg = QLabel("")
        form.addRow(self.signup_msg)

        signup_btn = QPushButton("Create Account")
        signup_btn.clicked.connect(self.attempt_signup)
        form.addRow(signup_btn)

        w.setLayout(form)
        self.stack.addWidget(w)

    def attempt_login(self):
        username = self.login_username.text().strip()
        acc_id = self.login_id.text().strip()
        pw = self.login_pw.text()
        if not username or not acc_id or not pw:
            self.login_msg.setText("Enter username, account id and password")
            return
        try:
            backend.GlobalData.status = ""
            ok = backend.log_in(username, acc_id, pw)
            status = backend.GlobalData.status.strip()
            if status:
                self.login_msg.setText(f"Status: {status}")
                return
            if ok:
                self.login_success = True
                self.logged_in_user = acc_id
                self.accept()
            else:
                self.login_msg.setText("Invalid credentials")
        except Exception as e:
            self.login_msg.setText(f"Error: {e}")

    def attempt_signup(self):
        username = self.su_username.text().strip()
        acc_id = self.su_id.text().strip()
        pw = self.su_pw.text()
        pw_confirm = self.su_pw_confirm.text()
        email = self.su_email.text().strip()
        phone = self.su_phone.text().strip()

        if not username or not acc_id or not pw or not pw_confirm or not email or not phone:
            self.signup_msg.setText("All fields required")
            return
        if pw != pw_confirm:
            self.signup_msg.setText("Passwords do not match")
            return
        try:
            phone_int = int(phone)
        except Exception:
            self.signup_msg.setText("Phone must be numeric")
            return
        try:
            backend.GlobalData.status = ""
            # sign_up expects: username, acc_id, pw, pw_confirm, email, phone
            backend.sign_up(username, acc_id, pw, pw_confirm, email, phone_int)
            status = backend.GlobalData.status.strip()
            if status:
                self.signup_msg.setText(f"Status: {status}")
                return
            self.signup_msg.setText("Account created. Please go to Login.")
            self.stack.setCurrentIndex(0)
        except Exception as e:
            self.signup_msg.setText(f"Error: {e}")


# -------------------- Upload Tab --------------------
class UploadTab(QWidget):
    def __init__(self, current_user_getter):
        super().__init__()
        self.get_current_user = current_user_getter
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

        self.do_upload_btn = QPushButton("Send to Server (Upload)")
        self.do_upload_btn.clicked.connect(self.do_upload)
        self.do_upload_btn.setEnabled(False)
        layout.addWidget(self.do_upload_btn)

        self.setLayout(layout)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.read_file(file_path)

    def read_file_path(self, path: str):
        self.read_file(path)

    def read_file(self, file_path: str):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            self.file_content = data
            self.file_path = file_path
            fn = get_filename_from_filepath(file_path)
            size = len(data)
            self.file_info_lbl.setText(f"Loaded: {fn}\nSize: {size} bytes")
            self.do_upload_btn.setEnabled(True)
        except Exception as e:
            self.file_info_lbl.setText(f"Error: {e}")
            self.clear_loaded_file()

    def clear_loaded_file(self):
        self.file_content = None
        self.file_path = None
        self.file_info_lbl.setText("No file loaded.")
        self.do_upload_btn.setEnabled(False)

    def do_upload(self):
        if not self.file_content or not self.file_path:
            QMessageBox.warning(self, "No file", "Please upload a file first.")
            return
        try:
            basename = get_filename_from_filepath(self.file_path)
            backend.file_upload(self.file_content, basename)
            QMessageBox.information(self, "Upload", "File uploaded successfully.")
            self.clear_loaded_file()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Upload failed: {e}")


# -------------------- Files Tab --------------------
class FilesTab(QWidget):
    def __init__(self, current_user_getter):
        super().__init__()
        self.get_current_user = current_user_getter
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.reload_btn = QPushButton("Reload Files")
        self.reload_btn.clicked.connect(self.load_files)
        top_row.addWidget(self.reload_btn)
        layout.addLayout(top_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(160)
        layout.addWidget(self.details)

        self.req_btn = QPushButton("Make request to make downloadable")
        self.req_btn.clicked.connect(self.make_request_for_selected)
        self.req_btn.setEnabled(False)
        layout.addWidget(self.req_btn)

        self.setLayout(layout)
        self.file_map = {}
        self.selected_file_dir = None
        self.load_files()

    def clear_grid(self):
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.file_map.clear()
        self.selected_file_dir = None
        self.details.clear()
        self.req_btn.setEnabled(False)

    def add_buttons(self, entries):
        for i, (label, file_dir) in enumerate(entries):
            btn = QPushButton(label)
            btn.setMinimumHeight(36)
            # ensure closure binds current file_dir
            btn.clicked.connect(lambda checked, d=file_dir: self.open_file_details(d))
            row, col = divmod(i, 2)
            self.grid_layout.addWidget(btn, row, col)
            self.file_map[label] = file_dir

    def load_files(self):
        self.clear_grid()
        server_dir = Path(backend.GlobalData.directory)
        files_root = server_dir / "files"
        entries = []
        if files_root.exists() and files_root.is_dir():
            for sub in sorted(files_root.iterdir()):
                if sub.is_dir():
                    fd = sub / "file_data.json"
                    label = sub.name
                    if fd.exists():
                        try:
                            with open(fd, "r") as f:
                                fdj = json.load(f)
                            label = strip_extension(fdj.get("File Name", sub.name))
                        except Exception:
                            pass
                    entries.append((label, str(sub) + os.sep))
        if not entries:
            self.add_buttons([("(no files found)", None)])
        else:
            entries.sort(key=lambda x: x[0].lower())
            self.add_buttons(entries)

    def open_file_details(self, file_dir):
        self.selected_file_dir = file_dir
        out = []
        try:
            fd = Path(file_dir) / "file_data.json"
            if fd.exists():
                with open(fd, "r") as f:
                    fdj = json.load(f)
                out.append("File Details:")
                for k, v in fdj.items():
                    out.append(f"  {k}: {v}")
            rq = Path(file_dir) / "req.json"
            if rq.exists():
                with open(rq, "r") as f:
                    rj = json.load(f)
                out.append(f"\nRequest Status: {json.dumps(rj)}")
            else:
                out.append("\nRequest Status: — none")
        except Exception as e:
            out.append(f"Error reading details: {e}")

        self.details.setPlainText("\n".join(out))
        self.req_btn.setEnabled(bool(self.selected_file_dir))

    def make_request_for_selected(self):
        if not self.selected_file_dir:
            return
        acc = self.get_current_user()
        try:
            backend.put_make_downloadable_request(self.selected_file_dir, acc)
            QMessageBox.information(self, "Request", "Request file created/updated.")
            self.open_file_details(self.selected_file_dir)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create request: {e}")


# -------------------- Requests Tab --------------------
class RequestsTab(QWidget):
    def __init__(self, current_user_getter):
        super().__init__()
        self.get_current_user = current_user_getter
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Requests overview"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_requests)
        layout.addWidget(self.refresh_btn)

        self.setLayout(layout)
        self.load_requests()

    def clear_grid(self):
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def load_requests(self):
        self.clear_grid()
        server_dir = Path(backend.GlobalData.directory)
        files_root = server_dir / "files"
        if not files_root.exists():
            return
        row = 0
        for sub in sorted(files_root.iterdir()):
            if sub.is_dir():
                rq = sub / "req.json"
                if rq.exists():
                    try:
                        with open(rq, "r") as f:
                            rj = json.load(f)
                        fname = sub.name
                        lbl = QLabel(f"{fname}: {json.dumps(rj)}")
                        approve_btn = QPushButton("Approve")
                        deny_btn = QPushButton("Deny")
                        # bind file_dir into lambda to avoid late-binding
                        approve_btn.clicked.connect(lambda checked, d=str(sub)+os.sep: self.update_status(d, True))
                        deny_btn.clicked.connect(lambda checked, d=str(sub)+os.sep: self.update_status(d, False))
                        self.grid.addWidget(lbl, row, 0)
                        self.grid.addWidget(approve_btn, row, 1)
                        self.grid.addWidget(deny_btn, row, 2)
                        row += 1
                    except Exception:
                        pass

    def update_status(self, file_dir, signal):
        acc = self.get_current_user()
        try:
            backend.update_download_perms(acc, signal, file_dir)
            QMessageBox.information(self, "Updated", f"Set status to {signal}")
            self.load_requests()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update: {e}")


# -------------------- Settings Tab (with sub-buttons) --------------------
class SettingsTab(QWidget):

    def __init__(self, current_user, parent_window):
        super().__init__()
        self.current_user = current_user
        self.parent_window = parent_window  # MainWindow instance

        layout = QVBoxLayout()

        # --- sub navigation buttons ---
        nav_layout = QHBoxLayout()
        self.appearance_btn = QPushButton(SUBTAB_APPEARANCE)
        self.account_btn = QPushButton(SUBTAB_ACCOUNT)

        for btn in (self.appearance_btn, self.account_btn):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            nav_layout.addWidget(btn)

        layout.addLayout(nav_layout)

        # --- stacked subtabs ---
        self.stack = QStackedLayout()
        self.appearance_tab = self._make_appearance_tab()
        self.account_tab = self._make_account_tab()

        self.stack.addWidget(self.appearance_tab)  # index 0
        self.stack.addWidget(self.account_tab)     # index 1

        # put stacked layout into a container widget and add to layout
        stack_container = QWidget()
        stack_container.setLayout(self.stack)
        layout.addWidget(stack_container)

        self.setLayout(layout)

        # connect sub-buttons
        self.appearance_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.account_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))

    def _make_appearance_tab(self):
        w = QWidget()
        v = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel("Select Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System Default", "Light", "Dark"])

        # load initial config
        try:
            cfg = load_config()
            cur = cfg.get("theme", "System Default")
            idx = self.theme_combo.findText(cur)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
        except Exception:
            pass

        row.addWidget(self.theme_combo)
        v.addLayout(row)

        save_btn = QPushButton("Save Theme")
        save_btn.clicked.connect(self.save_theme)
        v.addWidget(save_btn)

        w.setLayout(v)
        return w

    def _make_account_tab(self):
        w = QWidget()
        form = QFormLayout()
        self.old_pw = QLineEdit()
        self.old_pw.setEchoMode(QLineEdit.Password)
        self.new_username = QLineEdit()
        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.Password)
        self.new_email = QLineEdit()
        self.new_phone = QLineEdit()

        form.addRow("Old Password:", self.old_pw)
        form.addRow("New Username:", self.new_username)
        form.addRow("New Password:", self.new_pw)
        form.addRow("New Email:", self.new_email)
        form.addRow("New Phone:", self.new_phone)

        update_btn = QPushButton("Update Account")
        update_btn.clicked.connect(self.update_account)
        form.addRow(update_btn)

        logout_btn = QPushButton("Log Out")
        logout_btn.clicked.connect(self.parent_window.logout)
        form.addRow(logout_btn)

        w.setLayout(form)
        return w

    def save_theme(self):
        theme = self.theme_combo.currentText()
        cfg = load_config()
        cfg["theme"] = theme
        save_config(cfg)
        app = QApplication.instance()
        apply_theme(app, theme)
        QMessageBox.information(self, "Theme", f"Theme set to {theme}")

    def update_account(self):
        old_pw = self.old_pw.text()
        new_username = self.new_username.text().strip()
        new_pw = self.new_pw.text()
        email = self.new_email.text().strip()
        phone = self.new_phone.text().strip()
        phone_no = int(phone) if phone else 0

        try:
            backend.update_acc_details(new_username, old_pw, self.current_user, new_pw, email, phone_no)
            QMessageBox.information(self, "Account", "Account details updated")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update account: {e}")




# -------------------- Server Status Tab --------------------
class ServerStatusTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Server Status:"))

        self.status_view = QTextEdit()
        self.status_view.setReadOnly(True)
        layout.addWidget(self.status_view)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_status)
        layout.addWidget(self.refresh_btn)

        self.setLayout(layout)
        self.refresh_status()

    def refresh_status(self):
        s = getattr(backend.GlobalData, "status", "")
        if not s:
            s = "(no status yet)"
        self.status_view.setPlainText(s)


# -------------------- Main Window --------------------
class MainWindow(QWidget):


    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.logged_out = False

        self.setWindowTitle("Server - Uploader")
        self.resize(960, 700)

        # Set global app icon if available
        try:
            if ICON_PATH.exists():
                self.setWindowIcon(QIcon(str(ICON_PATH)))
        except Exception:
            pass

        # main vertical layout
        main_layout = QVBoxLayout()

        # --- top navigation buttons ---
        nav_layout = QHBoxLayout()
        self.upload_btn = QPushButton(TAB_UPLOAD)
        self.files_btn = QPushButton(TAB_FILES)
        self.requests_btn = QPushButton(TAB_REQUESTS)
        self.settings_btn = QPushButton(TAB_SETTINGS)
        self.status_btn = QPushButton(TAB_SERVER_STATUS)

        for btn in (self.upload_btn, self.files_btn, self.requests_btn, self.settings_btn, self.status_btn):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            nav_layout.addWidget(btn)

        main_layout.addLayout(nav_layout)

        # --- stacked pages ---
        self.stack = QStackedLayout()
        self.upload_tab = UploadTab(self.get_current_user)
        self.files_tab = FilesTab(self.get_current_user)
        self.requests_tab = RequestsTab(self.get_current_user)
        self.settings_tab = SettingsTab(self.current_user, self)
        self.status_tab = ServerStatusTab()

        self.stack.addWidget(self.upload_tab)    # index 0
        self.stack.addWidget(self.files_tab)     # index 1
        self.stack.addWidget(self.requests_tab)  # index 2
        self.stack.addWidget(self.settings_tab)  # index 3
        self.stack.addWidget(self.status_tab)    # index 4

        # wrap stacked layout in a widget and add to layout
        stack_container = QWidget()
        stack_container.setLayout(self.stack)
        main_layout.addWidget(stack_container)

        self.setLayout(main_layout)

        # connect buttons to stack switching
        self.upload_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.files_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.requests_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        self.status_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))

    def get_current_user(self):
        return self.current_user

    def logout(self):
        # mark logout and quit the Qt event loop
        self.logged_out = True
        QApplication.quit()




# -------------------- Session runner --------------------
def run_once():
    # Create a fresh QApplication for each session
    app = QApplication(sys.argv)

    # set global app icon (taskbar/dock)
    if ICON_PATH.exists():
        try:
            app.setWindowIcon(QIcon(str(ICON_PATH)))
        except Exception:
            pass

    # ensure server directories and accounts file
    server_dir = Path(getattr(backend.GlobalData, "directory", "server_system"))
    server_dir = Path(server_dir)
    server_dir.mkdir(parents=True, exist_ok=True)
    (server_dir / "files").mkdir(parents=True, exist_ok=True)
    acc_file = server_dir / "accounts.json"
    if not acc_file.exists():
        with open(acc_file, "w") as f:
            json.dump({}, f, indent=4)

    # load/apply theme
    cfg = load_config()
    apply_theme(app, cfg.get("theme", "System Default"))

    # show login dialog (blocking)
    auth = AuthDialog()
    if auth.exec_() != QDialog.Accepted or not auth.login_success:
        # user cancelled login -> do not restart
        return False

    # open main window for the logged-in user
    user = auth.logged_in_user
    window = MainWindow(user)
    window.show()

    # run Qt until quit (logout or normal close)
    app.exec_()

    # return whether logout was requested
    return getattr(window, "logged_out", False)


def main():
    # loop: each run creates a fresh QApplication instance (workaround for Qt limitations)
    while True:
        restart = run_once()
        if not restart:
            break


if __name__ == "__main__":
    main()