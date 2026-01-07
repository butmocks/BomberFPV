from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame


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
    stats: DroneStats = DroneStats()
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
    pygame.display.set_caption("BomberFPV — prototype")

    w, h = 1100, 700
    screen = pygame.display.set_mode((w, h))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("DejaVu Sans", 18)
    font_big = pygame.font.SysFont("DejaVu Sans", 24, bold=True)

    # playfield + sidebar
    sidebar_w = 320
    play = pygame.Rect(0, 0, w - sidebar_w, h)
    sidebar = pygame.Rect(w - sidebar_w, 0, sidebar_w, h)

    drone = Drone(x=play.centerx, y=play.centery)
    bombs: list[Bomb] = []
    targets: list[Target] = [spawn_target(play) for _ in range(10)]

    score = 0
    upgrade_open = False

    # upgrades (cost grows)
    up_levels = {"speed": 0, "reload": 0, "radius": 0}

    def upgrade_cost(stat: str) -> int:
        base = {"speed": 120, "reload": 140, "radius": 160}[stat]
        return base + up_levels[stat] * base

    def apply_upgrade(stat: str) -> None:
        nonlocal score
        c = upgrade_cost(stat)
        if score < c:
            return
        score -= c
        up_levels[stat] += 1

        if stat == "speed":
            drone.stats.speed = min(520.0, drone.stats.speed + 35.0)
        elif stat == "reload":
            drone.stats.reload_time = max(0.25, drone.stats.reload_time - 0.12)
        elif stat == "radius":
            drone.stats.bomb_radius = min(110.0, drone.stats.bomb_radius + 6.0)

    running = True
    while running:
        dt = clock.tick(120) / 1000.0

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
                        apply_upgrade("speed")
                    elif e.key == pygame.K_2:
                        apply_upgrade("reload")
                    elif e.key == pygame.K_3:
                        apply_upgrade("radius")
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

        keys = pygame.key.get_pressed()
        if not upgrade_open:
            # movement: WASD / arrows
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
            for b in impacted:
                # score for targets in radius (single bomb can hit multiple)
                for i, t in enumerate(targets):
                    if i in removed:
                        continue
                    if dist((b.x, b.y), (t.x, t.y)) <= (b.radius + t.r):
                        score += t.points
                        removed.add(i)

            if removed:
                targets = [t for i, t in enumerate(targets) if i not in removed]

            # keep population
            while len(targets) < 10:
                targets.append(spawn_target(play))

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
        draw_text(screen, "BomberFPV (prototype)", (x0, y), font_big, WHITE)
        y += 36

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
                "Заметка: боеприпас 'падает' ~0.55s — нужно сбрасывать чуть заранее.",
                (bx + 20, ty),
                font,
                (200, 200, 200),
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()

