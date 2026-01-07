from __future__ import annotations

import argparse
import math
import os
import random
import sys
from dataclasses import dataclass, field

import pygame

# Импорт системы звуков
try:
    from .sounds import SoundManager
except ImportError:
    from sounds import SoundManager


WHITE = (240, 240, 240)
BLACK = (20, 20, 20)
GRAY = (70, 70, 70)
DARK = (30, 30, 30)
RED = (220, 70, 70)
GREEN = (70, 220, 120)
YELLOW = (235, 220, 90)
CYAN = (80, 210, 230)


SCORE_TABLE: list[tuple[str, int, tuple[int, int, int]]] = [
    ("Чмоня", 10, GREEN),
    ("Палатка", 20, YELLOW),
    ("Боеприпасы", 50, CYAN),
    ("Техника", 100, RED),
]

# Черный юмор - украинские фразы
HUMOR_PHRASES = {
    "start": [
        "Добро пожаловать на фронт, пілот!",
        "Сьогодні твоя черга стати героєм... або статистикою.",
        "Пам'ятай: кожна бомба має свій адрес.",
    ],
    "hit": [
        "Бабах! Ще один влучний удар!",
        "Попав! Ворог тепер в кращому світі... або просто в іншому.",
        "В ціль! Це було красиво, як смерть.",
        "Ще один! Колекція трофеїв росте.",
        "Гарно! Вони більше не будуть скаржитися.",
    ],
    "miss": [
        "Майже... Спробуй ще раз, може пощастить.",
        "Трохи не влучив. Наступного разу буде краще... або гірше.",
        "Спробуй ще. Практика робить майстра... або труп.",
    ],
    "upgrade": [
        "Апгрейд куплено! Тепер ти смертельніший.",
        "Покращення активовано! Вороги в жаху... якщо вони ще живі.",
        "Нова зброя! Тепер ти можеш вбивати ефективніше.",
    ],
    "combo": [
        "Комбо! Вони падають як мухи!",
        "Влучний удар! Колекція трупів росте!",
        "Мультикілл! Ти майстер знищення!",
    ],
}


@dataclass
class DroneStats:
    speed: float = 240.0  # px/s
    reload_time: float = 1.20  # seconds
    bomb_radius: float = 42.0  # px
    bomb_fall_time: float = 0.55  # seconds (timing window)


@dataclass
class Drone:
    x: float
    y: float
    heading: float = 0.0  # radians
    stats: DroneStats = field(default_factory=DroneStats)
    reload_left: float = 0.0

    def can_drop(self) -> bool:
        return self.reload_left <= 0.0

    def tick_reload(self, dt: float) -> None:
        self.reload_left = max(0.0, self.reload_left - dt)

    def start_reload(self) -> None:
        self.reload_left = self.stats.reload_time


@dataclass
class Bomb:
    x: float
    y: float
    t_left: float  # until "impact"
    radius: float

    def update(self, dt: float) -> None:
        self.t_left -= dt

    def impacted(self) -> bool:
        return self.t_left <= 0.0


@dataclass
class Target:
    kind: str
    points: int
    color: tuple[int, int, int]
    x: float
    y: float
    vx: float
    vy: float
    r: float

    def update(self, dt: float, bounds: pygame.Rect) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt

        # bounce in bounds
        if self.x - self.r < bounds.left:
            self.x = bounds.left + self.r
            self.vx *= -1
        if self.x + self.r > bounds.right:
            self.x = bounds.right - self.r
            self.vx *= -1
        if self.y - self.r < bounds.top:
            self.y = bounds.top + self.r
            self.vy *= -1
        if self.y + self.r > bounds.bottom:
            self.y = bounds.bottom - self.r
            self.vy *= -1


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def spawn_target(area: pygame.Rect) -> Target:
    kind, pts, color = random.choice(SCORE_TABLE)
    r = {"Чмоня": 10, "Палатка": 14, "Боеприпасы": 12, "Техника": 18}.get(kind, 12)
    x = random.uniform(area.left + r, area.right - r)
    y = random.uniform(area.top + r, area.bottom - r)
    spd = random.uniform(25.0, 65.0)
    ang = random.uniform(0, math.tau)
    return Target(
        kind=kind,
        points=pts,
        color=color,
        x=x,
        y=y,
        vx=math.cos(ang) * spd,
        vy=math.sin(ang) * spd,
        r=float(r),
    )


def format_reload(drone: Drone) -> str:
    if drone.can_drop():
        return "ГОТОВ"
    return f"{drone.reload_left:0.2f}s"


def draw_text(
    surf: pygame.Surface, text: str, pos: tuple[int, int], font: pygame.font.Font, color=WHITE
) -> None:
    surf.blit(font.render(text, True, color), pos)


def run() -> None:
    pygame.init()
    pygame.display.set_caption("BomberFPV — Український варіант")
    
    # Определение мобильного устройства
    is_mobile = hasattr(pygame, "ANDROID") or os.environ.get("ANDROID_ROOT")
    
    # Адаптивный размер экрана для мобильных
    if is_mobile:
        info = pygame.display.Info()
        w, h = info.current_w, info.current_h
        if w > h:
            w, h = h, w  # портретная ориентация
    else:
        w, h = 1100, 700
    
    screen = pygame.display.set_mode((w, h), pygame.RESIZABLE if not is_mobile else 0)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("DejaVu Sans", 18)
    font_big = pygame.font.SysFont("DejaVu Sans", 24, bold=True)
    font_humor = pygame.font.SysFont("DejaVu Sans", 16, italic=True)
    
    # Инициализация звуков
    sound_manager = SoundManager(enabled=True)
    
    # Сообщения для отображения
    humor_message = ""
    humor_timer = 0.0

    # playfield + sidebar
    sidebar_w = 320
    play = pygame.Rect(0, 0, w - sidebar_w, h)
    sidebar = pygame.Rect(w - sidebar_w, 0, sidebar_w, h)

    drone = Drone(x=play.centerx, y=play.centery)
    bombs: list[Bomb] = []
    targets: list[Target] = [spawn_target(play) for _ in range(10)]

    score = 0
    upgrade_open = False
    
    # Мобильные элементы управления
    touch_controls = {
        "move_stick": None,  # виртуальный джойстик для движения
        "bomb_button": None,  # кнопка сброса бомбы
        "upgrade_button": None,  # кнопка апгрейдов
    }
    
    # Инициализация виртуальных кнопок для мобильных
    if is_mobile:
        stick_radius = min(w, h) * 0.12
        touch_controls["move_stick"] = {
            "center": (stick_radius + 20, h - stick_radius - 20),
            "radius": stick_radius,
            "active": False,
            "offset": (0, 0),
        }
        button_size = min(w, h) * 0.08
        touch_controls["bomb_button"] = {
            "rect": pygame.Rect(w - button_size - 20, h - button_size - 20, button_size, button_size),
            "pressed": False,
        }
        touch_controls["upgrade_button"] = {
            "rect": pygame.Rect(w - button_size - 20, 20, button_size, button_size),
            "pressed": False,
        }
    
    # Показываем приветственное сообщение
    humor_message = random.choice(HUMOR_PHRASES["start"])
    humor_timer = 3.0
    sound_manager.play("drone")

    # upgrades (cost grows)
    up_levels = {"speed": 0, "reload": 0, "radius": 0}

    def upgrade_cost(stat: str) -> int:
        base = {"speed": 120, "reload": 140, "radius": 160}[stat]
        return base + up_levels[stat] * base

    def apply_upgrade(stat: str) -> bool:
        nonlocal score
        c = upgrade_cost(stat)
        if score < c:
            return False
        score -= c
        up_levels[stat] += 1

        if stat == "speed":
            drone.stats.speed = min(520.0, drone.stats.speed + 35.0)
        elif stat == "reload":
            drone.stats.reload_time = max(0.25, drone.stats.reload_time - 0.12)
        elif stat == "radius":
            drone.stats.bomb_radius = min(110.0, drone.stats.bomb_radius + 6.0)
        return True

    running = True
    elapsed = 0.0
    frames = 0
    while running:
        dt = clock.tick(120) / 1000.0
        elapsed += dt
        frames += 1

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if upgrade_open:
                        upgrade_open = False
                    else:
                        running = False
                elif e.key == pygame.K_u:
                    upgrade_open = not upgrade_open
                elif upgrade_open:
                    if e.key == pygame.K_1:
                        if apply_upgrade("speed"):
                            sound_manager.play("upgrade")
                            humor_message = random.choice(HUMOR_PHRASES["upgrade"])
                            humor_timer = 2.0
                    elif e.key == pygame.K_2:
                        if apply_upgrade("reload"):
                            sound_manager.play("upgrade")
                            humor_message = random.choice(HUMOR_PHRASES["upgrade"])
                            humor_timer = 2.0
                    elif e.key == pygame.K_3:
                        if apply_upgrade("radius"):
                            sound_manager.play("upgrade")
                            humor_message = random.choice(HUMOR_PHRASES["upgrade"])
                            humor_timer = 2.0
                else:
                    if e.key == pygame.K_SPACE and drone.can_drop():
                        bombs.append(
                            Bomb(
                                x=drone.x,
                                y=drone.y,
                                t_left=drone.stats.bomb_fall_time,
                                radius=drone.stats.bomb_radius,
                            )
                        )
                        drone.start_reload()
                        sound_manager.play("drop")
            # Мобильные сенсорные события
            elif is_mobile:
                if e.type == pygame.MOUSEBUTTONDOWN:
                    pos = e.pos
                    # Проверка кнопки бомбы
                    if touch_controls["bomb_button"] and touch_controls["bomb_button"]["rect"].collidepoint(pos):
                        touch_controls["bomb_button"]["pressed"] = True
                        if drone.can_drop():
                            bombs.append(
                                Bomb(
                                    x=drone.x,
                                    y=drone.y,
                                    t_left=drone.stats.bomb_fall_time,
                                    radius=drone.stats.bomb_radius,
                                )
                            )
                            drone.start_reload()
                            sound_manager.play("drop")
                    # Проверка кнопки апгрейдов
                    elif touch_controls["upgrade_button"] and touch_controls["upgrade_button"]["rect"].collidepoint(pos):
                        touch_controls["upgrade_button"]["pressed"] = True
                        upgrade_open = not upgrade_open
                    # Проверка джойстика движения
                    elif touch_controls["move_stick"]:
                        stick = touch_controls["move_stick"]
                        dist_to_center = math.hypot(
                            pos[0] - stick["center"][0], pos[1] - stick["center"][1]
                        )
                        if dist_to_center <= stick["radius"] * 1.5:
                            stick["active"] = True
                            dx = pos[0] - stick["center"][0]
                            dy = pos[1] - stick["center"][1]
                            mag = math.hypot(dx, dy)
                            if mag > 0:
                                stick["offset"] = (dx / mag, dy / mag)
                            else:
                                stick["offset"] = (0, 0)
                elif e.type == pygame.MOUSEMOTION:
                    if touch_controls["move_stick"] and touch_controls["move_stick"]["active"]:
                        pos = e.pos
                        stick = touch_controls["move_stick"]
                        dx = pos[0] - stick["center"][0]
                        dy = pos[1] - stick["center"][1]
                        mag = math.hypot(dx, dy)
                        max_mag = stick["radius"]
                        if mag > max_mag:
                            dx = dx / mag * max_mag
                            dy = dy / mag * max_mag
                        if mag > 0:
                            stick["offset"] = (dx / max_mag, dy / max_mag)
                elif e.type == pygame.MOUSEBUTTONUP:
                    if touch_controls["move_stick"]:
                        touch_controls["move_stick"]["active"] = False
                        touch_controls["move_stick"]["offset"] = (0, 0)
                    if touch_controls["bomb_button"]:
                        touch_controls["bomb_button"]["pressed"] = False
                    if touch_controls["upgrade_button"]:
                        touch_controls["upgrade_button"]["pressed"] = False

        keys = pygame.key.get_pressed()
        if not upgrade_open:
            # movement: WASD / arrows или сенсорный джойстик
            if is_mobile and touch_controls["move_stick"]["active"]:
                dx, dy = touch_controls["move_stick"]["offset"]
            else:
                dx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(
                    keys[pygame.K_a] or keys[pygame.K_LEFT]
                )
                dy = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(
                    keys[pygame.K_w] or keys[pygame.K_UP]
                )

            if dx != 0.0 or dy != 0.0:
                mag = math.hypot(dx, dy)
                dx /= mag
                dy /= mag
                drone.heading = math.atan2(dy, dx)
                drone.x += dx * drone.stats.speed * dt
                drone.y += dy * drone.stats.speed * dt

            # keep in playfield
            drone.x = clamp(drone.x, play.left + 10, play.right - 10)
            drone.y = clamp(drone.y, play.top + 10, play.bottom - 10)

        drone.tick_reload(dt)

        for t in targets:
            t.update(dt, play)

        # bombs update + impacts
        for b in bombs:
            b.update(dt)

        impacted: list[Bomb] = [b for b in bombs if b.impacted()]
        bombs = [b for b in bombs if not b.impacted()]

        # resolve impacts
        if impacted:
            removed: set[int] = set()
            hits_count = 0
            for b in impacted:
                sound_manager.play("explosion")
                # score for targets in radius (single bomb can hit multiple)
                for i, t in enumerate(targets):
                    if i in removed:
                        continue
                    if dist((b.x, b.y), (t.x, t.y)) <= (b.radius + t.r):
                        score += t.points
                        removed.add(i)
                        hits_count += 1
                        sound_manager.play("hit")

            if removed:
                targets = [t for i, t in enumerate(targets) if i not in removed]
                # Черный юмор при попадании
                if hits_count > 1:
                    humor_message = random.choice(HUMOR_PHRASES["combo"])
                else:
                    humor_message = random.choice(HUMOR_PHRASES["hit"])
                humor_timer = 2.0

            # keep population
            while len(targets) < 10:
                targets.append(spawn_target(play))
        
        # Обновление таймера сообщений
        if humor_timer > 0:
            humor_timer -= dt

        # draw
        screen.fill(BLACK)
        pygame.draw.rect(screen, DARK, play)
        pygame.draw.rect(screen, (18, 18, 18), sidebar)
        pygame.draw.line(screen, GRAY, (sidebar.left, 0), (sidebar.left, h), 2)

        # targets
        for t in targets:
            pygame.draw.circle(screen, t.color, (int(t.x), int(t.y)), int(t.r))
            if t.kind == "Палатка":
                pygame.draw.rect(
                    screen,
                    t.color,
                    pygame.Rect(int(t.x - t.r), int(t.y - t.r), int(t.r * 2), int(t.r * 2)),
                    border_radius=4,
                )
            elif t.kind == "Техника":
                pygame.draw.rect(
                    screen,
                    t.color,
                    pygame.Rect(int(t.x - t.r), int(t.y - t.r / 2), int(t.r * 2), int(t.r)),
                    border_radius=2,
                )

        # bombs (falling indicator + impact marker)
        for b in bombs:
            # falling: draw a shrinking "altitude ring"
            k = clamp(b.t_left / drone.stats.bomb_fall_time, 0.0, 1.0)
            r = int(6 + 18 * k)
            pygame.draw.circle(screen, WHITE, (int(b.x), int(b.y)), r, 2)

        # drone
        dpos = (int(drone.x), int(drone.y))
        pygame.draw.circle(screen, WHITE, dpos, 9)
        hx = int(drone.x + math.cos(drone.heading) * 16)
        hy = int(drone.y + math.sin(drone.heading) * 16)
        pygame.draw.line(screen, WHITE, dpos, (hx, hy), 3)

        # bomb radius preview (timing aid)
        pygame.draw.circle(screen, (255, 255, 255, 40), dpos, int(drone.stats.bomb_radius), 1)

        # sidebar UI
        x0 = sidebar.left + 16
        y = 16
        draw_text(screen, "BomberFPV", (x0, y), font_big, WHITE)
        y += 28
        draw_text(screen, "🇺🇦 Український варіант", (x0, y), font, YELLOW)
        y += 30

        draw_text(screen, f"Очки: {score}", (x0, y), font_big, WHITE)
        y += 34

        draw_text(screen, f"Сброс (Space): {format_reload(drone)}", (x0, y), font, WHITE)
        y += 26
        draw_text(screen, f"Скорость: {drone.stats.speed:.0f}", (x0, y), font, WHITE)
        y += 22
        draw_text(screen, f"Перезарядка: {drone.stats.reload_time:.2f}s", (x0, y), font, WHITE)
        y += 22
        draw_text(screen, f"Радиус: {drone.stats.bomb_radius:.0f}", (x0, y), font, WHITE)
        y += 22
        draw_text(screen, f"Время падения: {drone.stats.bomb_fall_time:.2f}s", (x0, y), font, WHITE)
        y += 30

        draw_text(screen, "Таблица очков:", (x0, y), font_big, WHITE)
        y += 30
        for name, pts, color in SCORE_TABLE:
            pygame.draw.circle(screen, color, (x0 + 8, y + 10), 6)
            draw_text(screen, f"{name} — {pts}", (x0 + 22, y + 2), font, WHITE)
            y += 24

        y += 18
        draw_text(screen, "Управление:", (x0, y), font_big, WHITE)
        y += 30
        draw_text(screen, "WASD/стрелки — полёт", (x0, y), font, WHITE)
        y += 22
        draw_text(screen, "Space — сброс боеприпаса", (x0, y), font, WHITE)
        y += 22
        draw_text(screen, "U — апгрейды", (x0, y), font, WHITE)
        y += 22
        draw_text(screen, "Esc — выход/закрыть меню", (x0, y), font, WHITE)
        
        # Отображение сообщений с черным юмором
        if humor_timer > 0 and humor_message:
            msg_surf = font_humor.render(humor_message, True, CYAN)
            msg_rect = msg_surf.get_rect(center=(play.centerx, play.top + 40))
            # Полупрозрачный фон
            bg = pygame.Surface((msg_rect.width + 20, msg_rect.height + 10), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            screen.blit(bg, (msg_rect.x - 10, msg_rect.y - 5))
            screen.blit(msg_surf, msg_rect)

        if upgrade_open:
            overlay = pygame.Surface((play.width, play.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            bw, bh = 560, 300
            bx = play.centerx - bw // 2
            by = play.centery - bh // 2
            pygame.draw.rect(screen, (15, 15, 15), (bx, by, bw, bh), border_radius=10)
            pygame.draw.rect(screen, GRAY, (bx, by, bw, bh), 2, border_radius=10)

            ty = by + 18
            draw_text(screen, "Апгрейды (1/2/3). U/Esc — закрыть.", (bx + 18, ty), font_big, WHITE)
            ty += 44

            def line(k: str, key: str, desc: str) -> None:
                nonlocal ty
                c = upgrade_cost(k)
                ok = score >= c
                col = WHITE if ok else (160, 160, 160)
                draw_text(
                    screen,
                    f"[{key}] {desc}  (ур. {up_levels[k]})  цена: {c}",
                    (bx + 20, ty),
                    font,
                    col,
                )
                ty += 34

            line("speed", "1", "Скорость +")
            line("reload", "2", "Перезарядка -")
            line("radius", "3", "Радиус +")

            ty += 10
            draw_text(
                screen,
                "Заметка: боеприпас 'падает' ~0.55s — треба скидати трохи завчасно.",
                (bx + 20, ty),
                font,
                (200, 200, 200),
            )
            ty += 24
            draw_text(
                screen,
                "Пам'ятай: кожна бомба має свій адрес!",
                (bx + 20, ty),
                font_humor,
                (180, 180, 255),
            )
        
        # Отрисовка мобильных элементов управления
        if is_mobile:
            # Виртуальный джойстик
            if touch_controls["move_stick"]:
                stick = touch_controls["move_stick"]
                center = stick["center"]
                radius = stick["radius"]
                # Фон джойстика
                pygame.draw.circle(screen, (40, 40, 40, 200), center, radius)
                pygame.draw.circle(screen, GRAY, center, radius, 2)
                # Ручка джойстика
                if stick["active"]:
                    handle_pos = (
                        int(center[0] + stick["offset"][0] * radius * 0.7),
                        int(center[1] + stick["offset"][1] * radius * 0.7),
                    )
                else:
                    handle_pos = center
                pygame.draw.circle(screen, WHITE, handle_pos, int(radius * 0.3))
            
            # Кнопка бомбы
            if touch_controls["bomb_button"]:
                btn = touch_controls["bomb_button"]
                color = RED if btn["pressed"] else (RED[0] // 2, RED[1] // 2, RED[2] // 2)
                pygame.draw.rect(screen, color, btn["rect"], border_radius=8)
                pygame.draw.rect(screen, WHITE, btn["rect"], 2, border_radius=8)
                text = font.render("💣", True, WHITE)
                text_rect = text.get_rect(center=btn["rect"].center)
                screen.blit(text, text_rect)
            
            # Кнопка апгрейдов
            if touch_controls["upgrade_button"]:
                btn = touch_controls["upgrade_button"]
                color = YELLOW if btn["pressed"] else (YELLOW[0] // 2, YELLOW[1] // 2, YELLOW[2] // 2)
                pygame.draw.rect(screen, color, btn["rect"], border_radius=8)
                pygame.draw.rect(screen, WHITE, btn["rect"], 2, border_radius=8)
                text = font.render("⚙", True, WHITE)
                text_rect = text.get_rect(center=btn["rect"].center)
                screen.blit(text, text_rect)

        pygame.display.flip()

    pygame.quit()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BomberFPV — top-down FPV bomber prototype")
    p.add_argument(
        "--smoke",
        action="store_true",
        help="Run a short headless smoke test (auto-exit).",
    )
    p.add_argument(
        "--seconds",
        type=float,
        default=0.75,
        help="Smoke test duration in seconds (only with --smoke).",
    )
    p.add_argument(
        "--frames",
        type=int,
        default=0,
        help="Smoke test max frames (0 = ignore, only with --smoke).",
    )
    return p.parse_args(argv)


def smoke(seconds: float = 0.75, frames: int = 0) -> None:
    # Run the main loop shortly with a dummy video driver to validate init/draw/update.
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    pygame.init()
    pygame.display.set_caption("BomberFPV — smoke")

    w, h = 640, 360
    sidebar_w = 220
    play = pygame.Rect(0, 0, w - sidebar_w, h)
    screen = pygame.display.set_mode((w, h))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("DejaVu Sans", 18)

    drone = Drone(x=play.centerx, y=play.centery)
    targets: list[Target] = [spawn_target(play) for _ in range(5)]
    bombs: list[Bomb] = []

    t = 0.0
    f = 0
    while t < max(0.01, seconds) and (frames <= 0 or f < frames):
        dt = clock.tick(120) / 1000.0
        t += dt
        f += 1
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return

        # simple autopilot circle + periodic drops
        ang = t * 1.2
        drone.x = clamp(play.centerx + math.cos(ang) * 120, play.left + 10, play.right - 10)
        drone.y = clamp(play.centery + math.sin(ang) * 80, play.top + 10, play.bottom - 10)
        drone.heading = ang
        drone.tick_reload(dt)
        if (int(t * 10) % 6 == 0) and drone.can_drop():
            bombs.append(
                Bomb(
                    x=drone.x,
                    y=drone.y,
                    t_left=drone.stats.bomb_fall_time,
                    radius=drone.stats.bomb_radius,
                )
            )
            drone.start_reload()

        for tr in targets:
            tr.update(dt, play)
        for b in bombs:
            b.update(dt)
        bombs = [b for b in bombs if not b.impacted()]

        screen.fill(BLACK)
        pygame.draw.rect(screen, DARK, play)
        for tr in targets:
            pygame.draw.circle(screen, tr.color, (int(tr.x), int(tr.y)), int(tr.r))
        for b in bombs:
            pygame.draw.circle(screen, WHITE, (int(b.x), int(b.y)), 10, 2)
        pygame.draw.circle(screen, WHITE, (int(drone.x), int(drone.y)), 8)
        screen.blit(font.render("smoke test…", True, WHITE), (play.left + 8, play.top + 8))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    args = parse_args()
    if args.smoke:
        smoke(seconds=args.seconds, frames=args.frames)
    else:
        run()

