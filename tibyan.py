import ctypes
import json
import os
import random
import sys
import time
import urllib.request

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QPixmap, QFont, QColor, QIcon, QAction,
    QPainter, QBrush, QPen
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QPushButton, QComboBox, QDialog, QGraphicsDropShadowEffect,
    QSystemTrayIcon, QMenu
)

# Optional win32gui for active window tracking on Windows
try:
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# GitHub Raw URLs for misconception lists
EN_LIST_URL = "https://raw.githubusercontent.com/Ibrahim-arius101/Tibyan/refs/heads/main/misinfo_en.txt"
AR_LIST_URL = "https://raw.githubusercontent.com/Ibrahim-arius101/Tibyan/refs/heads/main/misinfo_ar.txt"


def get_app_folder():
    """Finds the exact folder where Tibyan.exe (or tibyan.py) is located."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_folder()
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
EN_FILE = os.path.join(APP_DIR, "misinfo_en.txt")
AR_FILE = os.path.join(APP_DIR, "misinfo_ar.txt")
COOLDOWN_INTERVAL = 30 * 60  # 30 minutes in seconds


def update_misconception_lists():
    """Downloads the latest English and Arabic lists from GitHub."""
    targets = [
        (EN_LIST_URL, EN_FILE),
        (AR_LIST_URL, AR_FILE),
    ]

    try:
        counts = []
        for url, save_path in targets:
            req = urllib.request.Request(url, headers={"User-Agent": "Tibyan-Updater"})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8")

            # Verify the downloaded file actually has Misinformation,Correction lines
            lines = [line.strip() for line in content.splitlines() if "," in line]
            if not lines:
                raise ValueError("Downloaded file contained no valid Misinformation,Correction lines.")

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)

            counts.append(len(lines))

        ctypes.windll.user32.MessageBoxW(
            0,
            f"Lists updated successfully!\n\nEnglish facts: {counts[0]}\nArabic facts: {counts[1]}",
            "Tibyan Updater",
            0x40,
        )
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Could not download updates. Check your internet connection.\n\nDetails: {e}",
            "Tibyan Update Failed",
            0x10,
        )


class SetupDialog(QDialog):
    """Configuration dialog for Language and Theme."""
    def __init__(self, current_config=None):
        super().__init__()
        self.current_config = current_config or {"lang": "en", "theme": "dark"}
        self.setWindowTitle("Tibyan - Setup")
        self.setFixedSize(350, 260)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )

        layout = QVBoxLayout()
        layout.setSpacing(15)

        title_label = QLabel("Tibyan Settings")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("العربية (Arabic)", "ar")
        lang_idx = self.lang_combo.findData(self.current_config.get("lang", "en"))
        if lang_idx >= 0:
            self.lang_combo.setCurrentIndex(lang_idx)
        layout.addWidget(QLabel("Select Language:"))
        layout.addWidget(self.lang_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Theme", "dark")
        self.theme_combo.addItem("Light Theme", "light")
        theme_idx = self.theme_combo.findData(self.current_config.get("theme", "dark"))
        if theme_idx >= 0:
            self.theme_combo.setCurrentIndex(theme_idx)
        layout.addWidget(QLabel("Select Theme (Background):"))
        layout.addWidget(self.theme_combo)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def save_config(self):
        config = {
            "lang": self.lang_combo.currentData(),
            "theme": self.theme_combo.currentData()
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        self.accept()


class MisinfoWidget(QWidget):
    """Borderless, high-DPI crisp pop-up widget with clean gold text palettes."""
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.bg_label = QLabel(self)
        theme = self.config.get("theme", "dark")
        bg_path = os.path.join(APP_DIR, f"{theme}.png")

        # High DPI Pixel Ratio detection
        dpr = self.devicePixelRatio()

        if os.path.exists(bg_path):
            base_pixmap = QPixmap(bg_path)

            logical_target_width = 600
            physical_target_width = int(logical_target_width * dpr)

            pixmap = base_pixmap.scaledToWidth(
                physical_target_width,
                Qt.TransformationMode.SmoothTransformation
            )
            pixmap.setDevicePixelRatio(dpr)

            self.bg_label.setPixmap(pixmap)

            w = int(pixmap.width() / dpr)
            h = int(pixmap.height() / dpr)
            self.resize(w, h)
            self.bg_label.resize(w, h)
        else:
            self.resize(600, 320)

        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(65, 55, 65, 55)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        is_arabic = self.config.get("lang") == "ar"
        font_family = "Segoe UI" if not is_arabic else "Tahoma"

        misinfo, correction = self.get_random_info()

        # Premium Gold Color Palettes per Theme
        if theme == "dark":
            misinfo_color = "#FFD700"     # Vibrant Bright Gold
            correction_color = "#FFEAA7"  # Soft Champagne Gold
            shadow_color = QColor(0, 0, 0, 230)
        else:
            misinfo_color = "#F4D03F"     # Bright Royal Gold
            correction_color = "#FFF5C0"  # Soft Warm Cream Gold
            shadow_color = QColor(0, 0, 0, 210)

        # Misinformation Label (Centered)
        self.misinfo_label = QLabel(f"❌  {misinfo}", self)
        self.misinfo_label.setFont(QFont(font_family, 14, QFont.Weight.Bold))
        self.misinfo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.misinfo_label.setWordWrap(True)
        self.misinfo_label.setStyleSheet(f"color: {misinfo_color};")

        shadow1 = QGraphicsDropShadowEffect(self)
        shadow1.setBlurRadius(8)
        shadow1.setOffset(1, 2)
        shadow1.setColor(shadow_color)
        self.misinfo_label.setGraphicsEffect(shadow1)

        layout.addWidget(self.misinfo_label)

        # Correction Label (Centered)
        self.correction_label = QLabel(f"✔  {correction}", self)
        self.correction_label.setFont(QFont(font_family, 14, QFont.Weight.Bold))
        self.correction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.correction_label.setWordWrap(True)
        self.correction_label.setStyleSheet(f"color: {correction_color};")

        shadow2 = QGraphicsDropShadowEffect(self)
        shadow2.setBlurRadius(8)
        shadow2.setOffset(1, 2)
        shadow2.setColor(shadow_color)
        self.correction_label.setGraphicsEffect(shadow2)

        layout.addWidget(self.correction_label)

        self.center_on_screen()

    def get_random_info(self):
        lang = self.config.get("lang", "en")
        filename = AR_FILE if lang == "ar" else EN_FILE

        if not os.path.exists(filename):
            if lang == "ar":
                return "الجزرة تحسن الرؤية الليلية بشكل خارق.", "هذه أسطورة نشأت خلال الحرب العالمية الثانية لتغطية تكنولوجيا الرادار."
            else:
                return "Goldfish have a 3-second memory.", "Goldfish can actually remember things for months."

        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and "," in line]
            if not lines:
                raise ValueError("Empty file")

            chosen_line = random.choice(lines)
            parts = chosen_line.split(",", 1)
            return parts[0].strip(), parts[1].strip()
        except Exception as e:
            return "Error loading data file.", str(e)

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def mousePressEvent(self, event):
        """Click anywhere on the widget to close it."""
        self.close()


class AppManager:
    """Manages system tray, background window tracking, and 30-minute cooldown."""
    def __init__(self):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self.app = QApplication(sys.argv)
        # Keep app running in tray when the pop-up widget closes
        self.app.setQuitOnLastWindowClosed(False)

        self.check_and_run_setup()
        self.setup_tray()

        self.last_window = self.get_active_window()
        self.last_popup_time = 0
        self.popup = None

        # Check active window changes every 1.5 seconds
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_active_window)
        self.monitor_timer.start(1500)

        # Show initial pop-up on launch
        self.show_popup()

    def create_tray_icon(self):
        """Generates a crisp emerald & gold badge icon for the system tray."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Deep Emerald Circle with Gold Border
        painter.setBrush(QBrush(QColor("#143D22")))
        painter.setPen(QPen(QColor("#F4D03F"), 5))
        painter.drawEllipse(QRectF(4, 4, size - 8, size - 8))

        # Center Gold Check/Spark Emblem
        painter.setPen(QColor("#FFD700"))
        painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "✦")

        painter.end()
        return QIcon(pixmap)

    def setup_tray(self):
        """Initializes the Windows System Tray icon and right-click menu."""
        self.tray_icon = QSystemTrayIcon(self.create_tray_icon(), self.app)
        self.tray_icon.setToolTip("Tibyan")

        tray_menu = QMenu()

        show_action = QAction("Show Pop-up Now", self.app)
        show_action.triggered.connect(self.show_popup)
        tray_menu.addAction(show_action)

        update_action = QAction("Update Misconception Lists", self.app)
        update_action.triggered.connect(update_misconception_lists)
        tray_menu.addAction(update_action)

        settings_action = QAction("Settings (Language / Theme)", self.app)
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        exit_action = QAction("Exit", self.app)
        exit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        """Double-clicking the tray icon triggers a pop-up immediately."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_popup()

    def open_settings(self):
        dialog = SetupDialog(self.load_config())
        if dialog.exec():
            self.show_popup()

    def quit_app(self):
        self.tray_icon.hide()
        self.app.quit()

    def check_and_run_setup(self):
        if not os.path.exists(CONFIG_FILE):
            dialog = SetupDialog()
            dialog.exec()

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"lang": "en", "theme": "dark"}

    def get_active_window(self):
        if HAS_WIN32:
            try:
                hwnd = win32gui.GetForegroundWindow()
                return win32gui.GetWindowText(hwnd)
            except Exception:
                return ""
        return ""

    def check_active_window(self):
        current_window = self.get_active_window()

        if current_window and current_window != self.last_window:
            self.last_window = current_window

            current_time = time.time()
            if current_time - self.last_popup_time >= COOLDOWN_INTERVAL:
                self.show_popup()

    def show_popup(self):
        if self.popup is not None:
            self.popup.close()
        self.last_popup_time = time.time()
        config = self.load_config()
        self.popup = MisinfoWidget(config)
        self.popup.show()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    manager = AppManager()
    manager.run()