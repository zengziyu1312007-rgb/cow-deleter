import ctypes
import os
import sys
import time
import math
import traceback
from pathlib import Path

import pygame

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

FPS = 60
GROUND_MARGIN = 160
COW_SPEED = 7
MIN_BITE_FRAMES = 8
MAX_BITE_FRAMES = 30
EAT_PHASE_TARGET_FRAMES = 300
WALK_OUT_PAUSE_FRAMES = 25

BODY_COLOR = (232, 178, 60)
BODY_SHADE = (196, 142, 40)
HEAD_COLOR = (232, 178, 60)
MUZZLE_COLOR = (150, 160, 175)
HORN_COLOR = (90, 90, 100)
LEG_COLOR = (150, 160, 175)
EYE_COLOR = (40, 30, 20)
MOUTH_COLOR = (120, 30, 30)
TONGUE_COLOR = (210, 90, 100)


def log_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable)
    else:
        base = Path(__file__)
    return base.with_suffix(".error.log")


def log_error(exc: BaseException) -> None:
    try:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
            f.write("\n")
    except Exception:
        pass


def get_target_dir() -> Path:
    env_dir = os.environ.get("NIULAI_TARGET_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(os.environ["USERPROFILE"]) / "Desktop"


SKIP_NAMES = {"desktop.ini", ".ds_store"}


def list_target_files(target_dir: Path) -> list[Path]:
    if not target_dir.exists():
        return []
    return [
        item for item in sorted(target_dir.iterdir())
        if item.name.lower() not in SKIP_NAMES
    ]


def eat_one(item: Path) -> bool:
    try:
        if send2trash is not None:
            send2trash(str(item))
            return True
    except Exception as exc:
        log_error(exc)
    return False


def force_foreground(hwnd: int) -> None:
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        SW_SHOW = 5

        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
        cur_thread = kernel32.GetCurrentThreadId()

        attached = False
        if fg_thread and fg_thread != cur_thread:
            attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))

        user32.ShowWindow(hwnd, SW_SHOW)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)

        if attached:
            user32.AttachThreadInput(cur_thread, fg_thread, False)
    except Exception as exc:
        log_error(exc)


def capture_desktop_image(width: int, height: int):
    """Grab the real desktop before our own window covers it."""
    if ImageGrab is None:
        return None
    try:
        img = ImageGrab.grab()
        return img.resize((width, height))
    except Exception as exc:
        log_error(exc)
        return None


def image_to_surface(img):
    if img is None:
        return None
    try:
        raw = img.tobytes()
        surf = pygame.image.fromstring(raw, img.size, img.mode)
        return surf.convert()
    except Exception as exc:
        log_error(exc)
        return None


def draw_cow(surface: pygame.Surface, cx: int, ground_y: int, mouth_open: bool, tick: int):
    walk = tick * 0.22
    bob = abs(math.sin(walk)) * 10
    hip_y = ground_y - bob
    body_cy = hip_y - 110
    head_cy = hip_y - 235

    # legs (thigh + shin + foot), alternating stride, drawn behind the torso
    for side, phase in ((-1, 0.0), (1, math.pi)):
        swing = math.sin(walk + phase) * 26
        lift = max(0.0, math.sin(walk + phase)) * 14
        hip_x = cx + side * 32
        knee = (hip_x + swing * 0.4, hip_y + 60 - lift * 0.5)
        foot = (hip_x + swing, ground_y - lift)
        pygame.draw.line(surface, BODY_SHADE, (hip_x, hip_y), knee, 34)
        pygame.draw.line(surface, BODY_SHADE, knee, foot, 34)
        foot_rect = pygame.Rect(0, 0, 52, 26)
        foot_rect.center = (foot[0], foot[1] + 6)
        pygame.draw.ellipse(surface, LEG_COLOR, foot_rect)

    # torso (big round belly)
    body_rect = pygame.Rect(0, 0, 170, 190)
    body_rect.center = (cx, body_cy)
    pygame.draw.ellipse(surface, BODY_SHADE, body_rect.inflate(6, 6))
    pygame.draw.ellipse(surface, BODY_COLOR, body_rect)

    # arms swinging opposite to legs, drawn over the torso edges
    for side, phase in ((-1, math.pi), (1, 0.0)):
        swing = math.sin(walk + phase) * 22
        shoulder = (cx + side * 92, body_cy - 55)
        elbow = (shoulder[0] + side * 6, shoulder[1] + 55 + swing * 0.2)
        hand = (elbow[0] + swing * 0.5, elbow[1] + 55)
        pygame.draw.line(surface, BODY_COLOR, shoulder, elbow, 30)
        pygame.draw.line(surface, BODY_COLOR, elbow, hand, 30)
        pygame.draw.circle(surface, LEG_COLOR, (int(hand[0]), int(hand[1])), 18)

    # head
    head_r = 74
    pygame.draw.circle(surface, HEAD_COLOR, (cx, head_cy), head_r)

    for hx in (-34, 34):
        horn_pts = [
            (cx + hx, head_cy - 58),
            (cx + hx * 1.6, head_cy - 100),
            (cx + hx * 0.9, head_cy - 62),
        ]
        pygame.draw.polygon(surface, HORN_COLOR, horn_pts)

    for ex in (-66, 66):
        ear_rect = pygame.Rect(0, 0, 32, 26)
        ear_rect.center = (cx + ex, head_cy - 6)
        pygame.draw.ellipse(surface, BODY_SHADE, ear_rect)

    brow_y = head_cy - 24
    for ex in (-26, 26):
        pygame.draw.line(surface, (90, 65, 30), (cx + ex - 16, brow_y + 6), (cx + ex + 16, brow_y - 6), 6)
        pygame.draw.circle(surface, (255, 255, 255), (cx + ex, brow_y + 20), 11)
        pygame.draw.circle(surface, EYE_COLOR, (cx + ex, brow_y + 20), 5)

    muzzle_rect = pygame.Rect(0, 0, 92, 66)
    muzzle_rect.center = (cx, head_cy + 40)
    pygame.draw.ellipse(surface, MUZZLE_COLOR, muzzle_rect)

    if mouth_open:
        mouth_rect = pygame.Rect(0, 0, 62, 50)
        mouth_rect.center = (muzzle_rect.centerx, muzzle_rect.centery + 8)
        pygame.draw.ellipse(surface, MOUTH_COLOR, mouth_rect)
        tongue_rect = pygame.Rect(0, 0, 34, 18)
        tongue_rect.center = (muzzle_rect.centerx, muzzle_rect.centery + 22)
        pygame.draw.ellipse(surface, TONGUE_COLOR, tongue_rect)
    else:
        pygame.draw.arc(
            surface, (60, 40, 30),
            pygame.Rect(muzzle_rect.centerx - 26, muzzle_rect.centery - 6, 52, 22),
            math.pi * 1.05, math.pi * 1.95, 3,
        )

    for nx in (-16, 16):
        pygame.draw.circle(surface, (60, 60, 70), (muzzle_rect.centerx + nx, muzzle_rect.centery - 14), 4)


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Niu Lai - Desktop Cleaner")

    info = pygame.display.Info()
    width, height = info.current_w, info.current_h

    target_dir = get_target_dir()
    desktop_img = capture_desktop_image(width, height)

    screen = pygame.display.set_mode((width, height), pygame.NOFRAME)

    try:
        hwnd = pygame.display.get_wm_info().get("window")
        if hwnd:
            force_foreground(hwnd)
    except Exception as exc:
        log_error(exc)

    clock = pygame.time.Clock()
    background = image_to_surface(desktop_img)

    ground_y = height - GROUND_MARGIN
    stop_x = width // 2
    cow_x = -320.0
    tick = 0

    state = "walk_in"
    queue: list[Path] = []
    total_to_eat = 0
    eaten_count = 0
    bite_interval = MIN_BITE_FRAMES
    bite_timer = 0
    pause_timer = 0

    font = None
    for name in ("microsoftyahei", "simhei", "arial"):
        try:
            font = pygame.font.SysFont(name, 40)
            if font is not None:
                break
        except Exception:
            continue
    if font is None:
        font = pygame.font.Font(None, 40)

    running = True
    while running:
        clock.tick(FPS)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        mouth_open = False

        if state == "walk_in":
            cow_x += COW_SPEED
            if cow_x >= stop_x:
                cow_x = stop_x
                queue = list_target_files(target_dir)
                total_to_eat = len(queue)
                if queue:
                    bite_interval = max(
                        MIN_BITE_FRAMES,
                        min(MAX_BITE_FRAMES, EAT_PHASE_TARGET_FRAMES // max(1, len(queue))),
                    )
                    state = "eat"
                else:
                    state = "walk_out"

        elif state == "eat":
            bite_timer += 1
            phase = bite_timer % bite_interval
            mouth_open = phase < max(1, bite_interval // 2)
            if phase == 0 and queue:
                item = queue.pop(0)
                if eat_one(item):
                    eaten_count += 1
            if not queue and phase == 0:
                state = "pause"
                pause_timer = 0

        elif state == "pause":
            pause_timer += 1
            mouth_open = False
            if pause_timer >= WALK_OUT_PAUSE_FRAMES:
                state = "walk_out"

        elif state == "walk_out":
            cow_x += COW_SPEED
            if cow_x > width + 400:
                running = False

        if background is not None:
            screen.blit(background, (0, 0))
        else:
            screen.fill((25, 20, 35))

        draw_cow(screen, int(cow_x), ground_y, mouth_open, tick)

        if state in ("eat", "pause", "walk_out") and total_to_eat > 0:
            label = f"哞~ 吃掉了 {eaten_count} / {total_to_eat} 个文件!"
            text = font.render(label, True, (255, 255, 255))
            shadow = font.render(label, True, (0, 0, 0))
            tx = width // 2 - text.get_width() // 2
            screen.blit(shadow, (tx + 2, 42))
            screen.blit(text, (tx, 40))

        pygame.display.flip()

    pygame.quit()


def main() -> int:
    try:
        run()
        return 0
    except Exception as exc:
        log_error(exc)
        try:
            pygame.quit()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
