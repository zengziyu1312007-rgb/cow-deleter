import math
import os
import sys
import time
import traceback
import ctypes
from pathlib import Path

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt, QTimer, QUrl
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRegion,
    QTransform,
)
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QApplication, QFileDialog, QWidget

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None


FPS = 60
POINT_FRAMES = 58
TRANSFORM_FRAMES = 72
EAT_FRAMES = 150
PAUSE_FRAMES = 65
FAREWELL_FRAMES = 105
COW_SPEED_IN = 14
COW_SPEED_OUT = 9

WHITE = QColor(255, 255, 255)
CREAM = QColor(255, 247, 220)
INK = QColor(37, 39, 43)
GREEN = QColor(55, 176, 78)
DARK_GREEN = QColor(25, 105, 55)
RED = QColor(239, 55, 43)
GOLD = QColor(255, 205, 69)


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / relative_path


def log_path() -> Path:
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            directory = Path.home() / "Library" / "Logs"
        elif sys.platform == "win32":
            directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NiuLaiCleaner"
        else:
            directory = Path.home() / ".local" / "state" / "NiuLaiCleaner"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "NiuLaiCleaner.error.log"
    return Path(__file__).with_suffix(".error.log")


def log_error(exc: BaseException) -> None:
    try:
        with open(log_path(), "a", encoding="utf-8") as file:
            file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=file)
            file.write("\n")
    except Exception:
        pass


def register_windows_context_menu() -> None:
    if sys.platform != "win32":
        return
    try:
        import winreg

        if getattr(sys, "frozen", False):
            command = f'"{sys.executable}" "%1"'
            icon = f'"{sys.executable}",0'
        else:
            command = f'"{sys.executable}" "{Path(__file__).resolve()}" "%1"'
            icon = "shell32.dll,32"
        key_path = r"Software\Classes\*\shell\SummonCow"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "召唤牛来吃掉")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, command)
    except Exception as exc:
        log_error(exc)


def safe_delete(item: Path) -> bool:
    try:
        if send2trash is not None and item.exists():
            send2trash(str(item))
            return True
    except Exception as exc:
        log_error(exc)
    return False


def requested_file() -> Path | None:
    for argument in sys.argv[1:]:
        if argument.startswith("-"):
            continue
        candidate = Path(argument).expanduser()
        if candidate.exists():
            return candidate
    return None


def configure_macos_overlay(window: QWidget) -> None:
    """Keep the transparent overlay on the user's currently active macOS Space."""
    if sys.platform != "darwin":
        return
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        def send(receiver, selector: bytes, restype=ctypes.c_void_p, argtypes=(), args=()):
            function = objc.objc_msgSend
            function.restype = restype
            function.argtypes = [ctypes.c_void_p, ctypes.c_void_p, *argtypes]
            return function(receiver, objc.sel_registerName(selector), *args)

        application_class = objc.objc_getClass(b"NSApplication")
        application = send(application_class, b"sharedApplication")
        # Accessory apps do not pull the user away from Finder or switch Spaces.
        send(application, b"setActivationPolicy:", None, (ctypes.c_long,), (1,))

        native_view = ctypes.c_void_p(int(window.winId()))
        native_window = send(native_view, b"window")
        # CanJoinAllSpaces | Stationary | FullScreenAuxiliary | IgnoresCycle
        behavior = (1 << 0) | (1 << 4) | (1 << 8) | (1 << 6)
        send(native_window, b"setCollectionBehavior:", None, (ctypes.c_ulong,), (behavior,))
        send(native_window, b"setHidesOnDeactivate:", None, (ctypes.c_bool,), (False,))
        send(native_window, b"setAcceptsMouseMovedEvents:", None, (ctypes.c_bool,), (True,))
        send(native_window, b"orderFrontRegardless", None)
        send(native_window, b"makeKeyWindow", None)
    except Exception as exc:
        log_error(exc)


def reveal_macos_desktop() -> list[int]:
    """Temporarily hide regular app windows while leaving Finder's Desktop visible."""
    if sys.platform != "darwin":
        return []
    hidden_pids: list[int] = []
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        def send(receiver, selector: bytes, restype=ctypes.c_void_p, argtypes=(), args=()):
            function = objc.objc_msgSend
            function.restype = restype
            function.argtypes = [ctypes.c_void_p, ctypes.c_void_p, *argtypes]
            return function(receiver, objc.sel_registerName(selector), *args)

        workspace_class = objc.objc_getClass(b"NSWorkspace")
        workspace = send(workspace_class, b"sharedWorkspace")
        applications = send(workspace, b"runningApplications")
        count = send(applications, b"count", ctypes.c_ulong)
        current_pid = os.getpid()

        for index in range(count):
            running_app = send(
                applications,
                b"objectAtIndex:",
                ctypes.c_void_p,
                (ctypes.c_ulong,),
                (index,),
            )
            pid = send(running_app, b"processIdentifier", ctypes.c_int)
            if pid == current_pid:
                continue
            activation_policy = send(running_app, b"activationPolicy", ctypes.c_long)
            is_hidden = send(running_app, b"isHidden", ctypes.c_bool)
            if activation_policy != 0 or is_hidden:
                continue
            bundle_object = send(running_app, b"bundleIdentifier")
            bundle_bytes = send(bundle_object, b"UTF8String", ctypes.c_char_p) if bundle_object else None
            bundle_identifier = bundle_bytes.decode("utf-8") if bundle_bytes else ""
            if bundle_identifier == "com.apple.finder":
                continue
            # AppKit applies hide/unhide asynchronously; remember the target even
            # when the immediate BOOL result has not caught up with the request.
            send(running_app, b"hide", ctypes.c_bool)
            hidden_pids.append(pid)
    except Exception as exc:
        log_error(exc)
    return hidden_pids


def restore_macos_applications(pids: list[int]) -> None:
    """Restore only the applications hidden by reveal_macos_desktop()."""
    if sys.platform != "darwin" or not pids:
        return
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        def send(receiver, selector: bytes, restype=ctypes.c_void_p, argtypes=(), args=()):
            function = objc.objc_msgSend
            function.restype = restype
            function.argtypes = [ctypes.c_void_p, ctypes.c_void_p, *argtypes]
            return function(receiver, objc.sel_registerName(selector), *args)

        running_application_class = objc.objc_getClass(b"NSRunningApplication")
        for pid in pids:
            running_app = send(
                running_application_class,
                b"runningApplicationWithProcessIdentifier:",
                ctypes.c_void_p,
                (ctypes.c_int,),
                (pid,),
            )
            if running_app:
                send(running_app, b"unhide", ctypes.c_bool)
    except Exception as exc:
        log_error(exc)


class CowOverlay(QWidget):
    def __init__(self, target_file: Path):
        super().__init__()
        self.target_file = target_file
        self.state = "aim"
        self.state_timer = 0
        self.tick = 0
        self.target_pos: QPointF | None = None
        self.ground_y = 0.0
        self.cow_x = -400.0
        self.direction = 1
        self.stop_x = 0.0
        self.deleted = False
        self.deletion_attempted = False
        self.miss_flash = 0
        self.auto_demo = os.environ.get("NIULAI_AUTODEMO") == "1"
        self.hidden_application_pids: list[int] = []
        self.yes_rect = QRect()
        self.no_rect = QRect()

        self.setWindowTitle("牛来清理文件")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))

        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        target_height = min(330, max(250, self.height() // 3))
        self.poses = {}
        for name in ("walk", "point", "graze", "run"):
            pixmap = QPixmap(str(resource_path(f"assets/cow-{name}.png")))
            height = target_height - 22 if name == "graze" else target_height
            self.poses[name] = pixmap.scaledToHeight(
                height,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.aim_background = QPixmap(str(resource_path("assets/cow-aim-background-v1.png")))

        self.mama_sound = self.make_sound("mama.wav")
        self.shoot_sound = self.make_sound("shoot.wav")
        self.hoof_sound = self.make_sound("hoof.wav", loop=True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(round(1000 / FPS))

    def make_sound(self, filename: str, loop: bool = False) -> QSoundEffect:
        effect = QSoundEffect(self)
        effect.setSource(QUrl.fromLocalFile(str(resource_path(f"assets/{filename}"))))
        effect.setVolume(0.78)
        if loop:
            effect.setLoopCount(-2)
        return effect

    def start_hoofbeats(self) -> None:
        self.hoof_sound.stop()
        self.hoof_sound.play()

    def stop_hoofbeats(self) -> None:
        self.hoof_sound.stop()

    def choose_target_position(self, position: QPointF) -> None:
        self.target_pos = position
        self.ground_y = max(330.0, min(self.height() - 28.0, position.y() + 112.0))
        point_width = self.poses["point"].width()
        if position.x() >= self.width() / 2:
            self.direction = 1
            self.cow_x = -self.poses["walk"].width() - 80.0
            self.stop_x = position.x() - 74.0 - point_width / 2
        else:
            self.direction = -1
            self.cow_x = self.width() + self.poses["walk"].width() + 80.0
            self.stop_x = position.x() + 74.0 + point_width / 2
        self.state = "cow_in"
        self.state_timer = 0
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.start_hoofbeats()
        self.update_interaction_mask()

    def reset_aim(self) -> None:
        self.stop_hoofbeats()
        self.target_pos = None
        self.state = "aim"
        self.state_timer = 0
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        self.clearMask()

    def advance(self) -> None:
        self.tick += 1
        self.state_timer += 1
        self.miss_flash = max(0, self.miss_flash - 1)

        if self.auto_demo:
            if self.state == "aim" and self.state_timer == 42:
                self.choose_target_position(QPointF(self.width() * 0.7, self.height() * 0.58))
            elif self.state == "confirm" and self.state_timer == 45:
                self.state = "transform"
                self.state_timer = 0
                self.shoot_sound.play()

        if self.state == "cow_in":
            self.cow_x += COW_SPEED_IN * self.direction
            reached = self.cow_x >= self.stop_x if self.direction == 1 else self.cow_x <= self.stop_x
            if reached:
                self.cow_x = self.stop_x
                self.stop_hoofbeats()
                self.state = "point"
                self.state_timer = 0
                self.mama_sound.play()
        elif self.state == "point" and self.state_timer >= POINT_FRAMES:
            self.state = "confirm"
            self.state_timer = 0
        elif self.state == "transform" and self.state_timer >= TRANSFORM_FRAMES:
            self.state = "eat"
            self.state_timer = 0
        elif self.state == "eat":
            if self.state_timer >= 52 and not self.deletion_attempted:
                self.deleted = safe_delete(self.target_file)
                self.deletion_attempted = True
            if self.state_timer >= EAT_FRAMES:
                self.state = "pause"
                self.state_timer = 0
        elif self.state == "pause" and self.state_timer >= PAUSE_FRAMES:
            self.state = "farewell"
            self.state_timer = 0
        elif self.state == "farewell" and self.state_timer >= FAREWELL_FRAMES:
            self.state = "cow_out"
            self.state_timer = 0
            self.start_hoofbeats()
        elif self.state == "cow_out":
            self.cow_x += COW_SPEED_OUT * self.direction
            gone = self.cow_x > self.width() + 420 if self.direction == 1 else self.cow_x < -420
            if gone:
                self.stop_hoofbeats()
                self.state = "done"
                self.state_timer = 0
        elif self.state == "done" and self.state_timer >= 1:
            self.close()
            QApplication.quit()

        self.update_interaction_mask()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.state == "aim":
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.state == "aim":
            self.choose_target_position(event.position())
        elif self.state == "confirm":
            point = event.position().toPoint()
            if self.yes_rect.contains(point):
                self.state = "transform"
                self.state_timer = 0
                self.shoot_sound.play()
            elif self.no_rect.contains(point):
                self.reset_aim()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self.state == "confirm":
                self.reset_aim()
            else:
                self.close()

    def closeEvent(self, event) -> None:
        self.stop_hoofbeats()
        self.mama_sound.stop()
        self.shoot_sound.stop()
        restore_macos_applications(self.hidden_application_pids)
        self.hidden_application_pids.clear()
        event.accept()

    def font(self, size: int, bold: bool = False) -> QFont:
        family = "PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei"
        result = QFont(family, size)
        result.setBold(bold)
        return result

    def draw_pill(self, painter: QPainter, text: str, subtext: str = "") -> None:
        width = min(760, self.width() - 70)
        height = 104 if subtext else 76
        rect = QRectF((self.width() - width) / 2, 24, width, height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 190, 45, 210))
        painter.drawRoundedRect(rect.translated(7, 8), 24, 24)
        painter.setPen(QPen(QColor(76, 48, 33), 4))
        painter.setBrush(QColor(255, 250, 222, 248))
        painter.drawRoundedRect(rect, 24, 24)

        badge = QRectF(rect.left() + 18, rect.top() + 16, 126, 34)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(240, 87, 67))
        painter.drawRoundedRect(badge, 15, 15)
        painter.setPen(WHITE)
        painter.setFont(self.font(13, True))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "牛来删除局")

        painter.setPen(QColor(76, 48, 33))
        painter.setFont(self.font(23, True))
        title_rect = rect.adjusted(154, 7, -20, -34 if subtext else -7)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, text)
        if subtext:
            painter.setPen(QColor(31, 128, 73))
            painter.setFont(self.font(14, True))
            painter.drawText(rect.adjusted(154, 58, -20, -9), Qt.AlignmentFlag.AlignCenter, subtext)

    def draw_crosshair(self, painter: QPainter, center: QPointF) -> None:
        pulse = 3 * math.sin(self.tick * 0.15)
        radius = 30 + pulse
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(RED, 3))
        painter.drawEllipse(center, radius, radius)
        painter.drawEllipse(center, 5, 5)
        gap, length = radius + 8, 24
        painter.drawLine(QPointF(center.x() - gap - length, center.y()), QPointF(center.x() - gap, center.y()))
        painter.drawLine(QPointF(center.x() + gap, center.y()), QPointF(center.x() + gap + length, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - gap - length), QPointF(center.x(), center.y() - gap))
        painter.drawLine(QPointF(center.x(), center.y() + gap), QPointF(center.x(), center.y() + gap + length))

    def draw_aim_background(self, painter: QPainter) -> None:
        if self.aim_background.isNull():
            return
        scaled = self.aim_background.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        fade_in = min(1.0, self.state_timer / 42)
        pulse = 0.018 * math.sin(self.tick * 0.07)
        painter.save()
        painter.setOpacity((0.38 + pulse) * fade_in)
        painter.drawPixmap(x, y, scaled)
        painter.restore()

    def oriented_pose(self, name: str) -> QPixmap:
        pose = self.poses[name]
        if self.direction == -1:
            return pose.transformed(QTransform().scale(-1, 1), Qt.TransformationMode.SmoothTransformation)
        return pose

    def pose_for_state(self) -> tuple[str, bool]:
        if self.state == "cow_in":
            return "walk", True
        if self.state in {"point", "confirm", "transform"}:
            return "point", False
        if self.state == "eat":
            return "graze", False
        if self.state == "cow_out":
            return "run", True
        return "walk", False

    def cow_rect(self, name: str, moving: bool) -> QRectF:
        pose = self.oriented_pose(name)
        bounce = abs(math.sin(self.tick * 0.24)) * 9 if moving else math.sin(self.tick * 0.08) * 2
        return QRectF(
            self.cow_x - pose.width() / 2,
            self.ground_y - pose.height() - bounce,
            pose.width(),
            pose.height(),
        )

    def draw_cow(self, painter: QPainter, name: str, moving: bool) -> QRectF:
        pose = self.oriented_pose(name)
        rect = self.cow_rect(name, moving)
        shadow_width = pose.width() * 0.62
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 25, 18, 70))
        painter.drawEllipse(QRectF(self.cow_x - shadow_width / 2, self.ground_y - 12, shadow_width, 22))
        painter.drawPixmap(rect.toRect(), pose)
        return rect

    def draw_grass(self, painter: QPainter, amount: float) -> None:
        if self.target_pos is None:
            return
        amount = max(0.0, min(1.0, amount))
        x = self.target_pos.x()
        base_y = self.target_pos.y() + 36
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(25, 105, 55, int(210 * amount)))
        painter.drawEllipse(QRectF(x - 65, base_y - 7, 130, 16))
        for index in range(19):
            offset = (index - 9) * 6
            height = (25 + index % 5 * 8) * amount
            sway = math.sin(self.tick * 0.12 + index) * 5
            color = GREEN if index % 2 else DARK_GREEN
            color.setAlpha(int(255 * amount))
            painter.setPen(QPen(color, 4))
            painter.drawLine(QPointF(x + offset, base_y), QPointF(x + offset + sway, base_y - height))

    def cow_bubble_rect(self, width: int, height: int) -> QRectF:
        pose_name, moving = self.pose_for_state()
        cow = self.cow_rect(pose_name, moving)
        x = cow.center().x() - width / 2
        y = cow.top() - height - 14
        x = max(18.0, min(self.width() - width - 18.0, x))
        if y < 18:
            if cow.center().x() < self.width() / 2:
                x = min(self.width() - width - 18.0, cow.right() + 18.0)
            else:
                x = max(18.0, cow.left() - width - 18.0)
            y = max(18.0, min(self.height() - height - 18.0, cow.top() + 25.0))
        return QRectF(x, y, width, height)

    def bubble_rect_for_state(self) -> QRectF | None:
        if self.state == "point":
            return self.cow_bubble_rect(370, 94)
        if self.state == "confirm":
            return self.cow_bubble_rect(min(510, self.width() - 36), 226)
        if self.state in {"transform", "eat", "pause", "farewell", "cow_out"}:
            return self.cow_bubble_rect(370, 94)
        return None

    def draw_bubble_background(self, painter: QPainter, bubble: QRectF) -> None:
        pose_name, moving = self.pose_for_state()
        cow = self.cow_rect(pose_name, moving)
        body = bubble.adjusted(0, 0, 0, -16)
        tail_x = max(body.left() + 28, min(body.right() - 28, cow.center().x()))

        shadow = QPainterPath()
        shadow.addRoundedRect(body.translated(7, 8), 22, 22)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 183, 38, 205))
        painter.drawPath(shadow)

        path = QPainterPath()
        path.addRoundedRect(body, 22, 22)
        tail = QPainterPath()
        tail.moveTo(tail_x - 14, body.bottom() - 1)
        tail.lineTo(tail_x, bubble.bottom())
        tail.lineTo(tail_x + 14, body.bottom() - 1)
        tail.closeSubpath()
        path.addPath(tail)
        painter.setBrush(QColor(255, 250, 220, 250))
        painter.setPen(QPen(QColor(78, 49, 33), 4))
        painter.drawPath(path)

        # Little hand-drawn emphasis marks make the bubble read like a comic.
        painter.setPen(QPen(QColor(240, 87, 67), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(body.left() + 24, body.top() - 7), QPointF(body.left() + 11, body.top() - 20))
        painter.drawLine(QPointF(body.left() + 48, body.top() - 10), QPointF(body.left() + 43, body.top() - 27))
        painter.setPen(QPen(QColor(43, 160, 89), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(body.right() - 22, body.top() - 6), QPointF(body.right() - 7, body.top() - 18))

    def draw_cow_bubble(self, painter: QPainter, text: str, subtext: str = "") -> None:
        bubble = self.bubble_rect_for_state()
        if bubble is None:
            return
        self.draw_bubble_background(painter, bubble)
        body = bubble.adjusted(14, 8, -14, -24)
        painter.setPen(QColor(76, 48, 33))
        painter.setFont(self.font(21, True))
        painter.drawText(body.adjusted(0, 0, 0, -22 if subtext else 0), Qt.AlignmentFlag.AlignCenter, text)
        if subtext:
            painter.setPen(DARK_GREEN)
            painter.setFont(self.font(13))
            painter.drawText(body.adjusted(0, 39, 0, 0), Qt.AlignmentFlag.AlignCenter, subtext)

    def update_interaction_mask(self) -> None:
        if self.state == "aim" or self.target_pos is None:
            self.clearMask()
            return

        pose_name, moving = self.pose_for_state()
        cow = self.cow_rect(pose_name, moving).adjusted(-28, -28, 28, 28).toAlignedRect()
        region = QRegion(cow)
        if self.state in {"cow_in", "point", "confirm", "transform", "eat", "pause"}:
            target = QRect(
                int(self.target_pos.x() - 115),
                int(self.target_pos.y() - 115),
                230,
                230,
            )
            region |= QRegion(target)
        bubble = self.bubble_rect_for_state()
        if bubble is not None:
            region |= QRegion(bubble.adjusted(-30, -30, 30, 18).toAlignedRect())
        self.setMask(region)

    def draw_confirmation(self, painter: QPainter) -> None:
        bubble = self.bubble_rect_for_state()
        if bubble is None:
            return
        self.draw_bubble_background(painter, bubble)
        body = bubble.adjusted(0, 0, 0, -16)
        painter.setPen(QColor(76, 48, 33))
        painter.setFont(self.font(22, True))
        painter.drawText(body.adjusted(18, 10, -18, -146), Qt.AlignmentFlag.AlignCenter, "妈！真吃这个？")
        painter.setPen(DARK_GREEN)
        painter.setFont(self.font(14))
        filename = self.target_file.name
        if len(filename) > 28:
            filename = filename[:25] + "…"
        painter.drawText(body.adjusted(22, 61, -22, -103), Qt.AlignmentFlag.AlignCenter, f"「{filename}」")
        painter.setPen(QColor(92, 104, 104))
        painter.setFont(self.font(12))
        painter.drawText(body.adjusted(18, 103, -18, -61), Qt.AlignmentFlag.AlignCenter, "我一口下去，它就进废纸篓")

        button_y = int(body.bottom() - 54)
        button_width = int((body.width() - 54) / 2)
        self.yes_rect = QRect(int(body.left() + 18), button_y, button_width, 42)
        self.no_rect = QRect(int(body.left() + 36 + button_width), button_y, button_width, 42)
        self.draw_button(painter, self.yes_rect, "喂！别客气", QColor(240, 87, 67))
        self.draw_button(painter, self.no_rect, "等等，瞄歪了", QColor(43, 160, 137))

    def draw_button(self, painter: QPainter, rect: QRect, text: str, color: QColor) -> None:
        painter.setPen(QPen(QColor(76, 48, 33), 3))
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(rect), 23, 23)
        painter.setPen(WHITE)
        painter.setFont(self.font(14, True))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def draw_dust_cloud(self, painter: QPainter) -> None:
        pose = self.oriented_pose("run")
        behind = self.cow_x - self.direction * (pose.width() * 0.48)
        painter.setPen(QPen(QColor(78, 49, 33, 90), 2))
        for index, radius in enumerate((18, 13, 9, 6)):
            drift = index * 24 * self.direction
            bob = math.sin(self.tick * 0.3 + index) * 5
            center = QPointF(behind - drift, self.ground_y - 12 - bob)
            painter.setBrush(QColor(255, 241, 194, 205 - index * 30))
            painter.drawEllipse(center, radius, radius * 0.72)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self.state == "aim":
            # Only aiming briefly owns the full screen. Every later phase is a
            # small shaped overlay around the cow, target and speech bubble.
            painter.fillRect(self.rect(), QColor(1, 16, 16, 38))
            self.draw_aim_background(painter)
            self.draw_pill(painter, "瞄准那份“不想要了”的文件", self.target_file.name)
            self.draw_crosshair(painter, QPointF(self.mapFromGlobal(QCursor.pos())))
            return

        if self.target_pos is None:
            return

        if self.state == "cow_in":
            self.draw_cow(painter, "walk", moving=True)
        elif self.state in {"point", "confirm", "transform"}:
            if self.state == "transform":
                progress = min(1.0, self.state_timer / TRANSFORM_FRAMES)
                glow = QColor(75, 230, 103, int(120 * (1 - progress * 0.4)))
                painter.setPen(QPen(glow, 5))
                painter.setBrush(QColor(85, 240, 115, int(45 * progress)))
                painter.drawEllipse(self.target_pos, 28 + progress * 45, 28 + progress * 45)
                self.draw_grass(painter, progress)
            self.draw_cow(painter, "point", moving=False)
            if self.state == "point":
                self.draw_cow_bubble(painter, "妈！这玩意儿能吃吗？")
            elif self.state == "confirm":
                self.draw_confirmation(painter)
            else:
                self.draw_cow_bubble(painter, "收到！先变成草～")
        elif self.state == "eat":
            grass_amount = max(0.0, 1.0 - self.state_timer / (EAT_FRAMES * 0.72))
            self.draw_grass(painter, grass_amount)
            self.draw_cow(painter, "graze", moving=False)
            self.draw_cow_bubble(painter, "嚼嚼嚼嚼……")
        elif self.state == "pause":
            self.draw_cow(painter, "walk", moving=False)
            self.draw_cow_bubble(painter, "嗝——删得真香！" if self.deleted else "这草硌牙，没删动…")
        elif self.state == "farewell":
            self.draw_cow(painter, "walk", moving=False)
            self.draw_cow_bubble(painter, "任务完成，牛走！")
        elif self.state == "cow_out":
            self.draw_dust_cloud(painter)
            self.draw_cow(painter, "run", moving=True)
            self.draw_cow_bubble(painter, "哒哒哒，溜了～")


def main() -> int:
    register_windows_context_menu()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    target = requested_file()
    if target is None:
        filename, _ = QFileDialog.getOpenFileName(None, "选择要让牛清理的文件", str(Path.home() / "Desktop"))
        if not filename:
            return 0
        target = Path(filename)

    hidden_application_pids: list[int] = []
    try:
        overlay = CowOverlay(target)
        overlay.show()
        configure_macos_overlay(overlay)
        hidden_application_pids = reveal_macos_desktop()
        overlay.hidden_application_pids = hidden_application_pids
        overlay.raise_()
        return app.exec()
    except Exception as exc:
        log_error(exc)
        return 1
    finally:
        restore_macos_applications(hidden_application_pids)


if __name__ == "__main__":
    sys.exit(main())
