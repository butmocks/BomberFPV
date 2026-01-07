"""Система звуков для BomberFPV с украинскими звуковыми эффектами."""
from __future__ import annotations

import array
import math
import os
import random
from pathlib import Path

import pygame


class SoundManager:
    """Менеджер звуков с генерацией простых звуков если файлы отсутствуют."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.sounds_dir = Path(__file__).parent.parent / "sounds"
        self.sounds_dir.mkdir(exist_ok=True)
        
        # Украинские фразы для черного юмора
        self.hit_phrases = [
            "Бабах!",
            "Попав!",
            "В ціль!",
            "Ще один!",
            "Гарно!",
            "Так тримати!",
        ]
        
        self.miss_phrases = [
            "Майже...",
            "Трохи не влучив",
            "Спробуй ще",
        ]
        
        self.sounds: dict[str, pygame.mixer.Sound | None] = {}
        self._init_sounds()
    
    def _init_sounds(self) -> None:
        """Инициализация звуков - загрузка или генерация."""
        if not self.enabled:
            return
        
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        except Exception:
            self.enabled = False
            return
        
        # Попытка загрузить звуки из файлов, если нет - генерируем
        self.sounds["explosion"] = self._load_or_generate("explosion.wav", self._gen_explosion)
        self.sounds["drop"] = self._load_or_generate("drop.wav", self._gen_drop)
        self.sounds["drone"] = self._load_or_generate("drone.wav", self._gen_drone)
        self.sounds["hit"] = self._load_or_generate("hit.wav", self._gen_hit)
        self.sounds["upgrade"] = self._load_or_generate("upgrade.wav", self._gen_upgrade)
    
    def _load_or_generate(
        self, filename: str, generator
    ) -> pygame.mixer.Sound | None:
        """Загружает звук из файла или генерирует его."""
        sound_path = self.sounds_dir / filename
        if sound_path.exists():
            try:
                return pygame.mixer.Sound(str(sound_path))
            except Exception:
                pass
        
        # Генерируем звук программно
        try:
            return generator()
        except Exception:
            return None
    
    def _gen_explosion(self) -> pygame.mixer.Sound:
        """Генерирует звук взрыва."""
        sample_rate = 22050
        duration = 0.4
        samples = int(sample_rate * duration)
        
        arr = array.array("h")
        for i in range(samples):
            # Низкочастотный взрыв с затуханием
            t = i / sample_rate
            freq = 60 + random.random() * 40
            amp = math.exp(-t * 8) * (0.3 + random.random() * 0.2)
            val = int(amp * 32767 * math.sin(2 * math.pi * freq * t))
            arr.append(val)
            arr.append(val)  # стерео
        
        sound = pygame.sndarray.make_sound(arr)
        sound.set_volume(0.6)
        return sound
    
    def _gen_drop(self) -> pygame.mixer.Sound:
        """Генерирует звук сброса бомбы."""
        sample_rate = 22050
        duration = 0.15
        samples = int(sample_rate * duration)
        
        arr = array.array("h")
        for i in range(samples):
            t = i / sample_rate
            # Короткий клик
            val = int(8000 * math.exp(-t * 20) * math.sin(2 * math.pi * 400 * t))
            arr.append(val)
            arr.append(val)
        
        sound = pygame.sndarray.make_sound(arr)
        sound.set_volume(0.4)
        return sound
    
    def _gen_drone(self) -> pygame.mixer.Sound:
        """Генерирует звук дрона (жужжание)."""
        sample_rate = 22050
        duration = 0.3
        samples = int(sample_rate * duration)
        
        arr = array.array("h")
        for i in range(samples):
            t = i / sample_rate
            # Высокочастотное жужжание
            freq = 200 + math.sin(t * 10) * 30
            val = int(5000 * math.exp(-t * 3) * math.sin(2 * math.pi * freq * t))
            arr.append(val)
            arr.append(val)
        
        sound = pygame.sndarray.make_sound(arr)
        sound.set_volume(0.3)
        return sound
    
    def _gen_hit(self) -> pygame.mixer.Sound:
        """Генерирует звук попадания."""
        sample_rate = 22050
        duration = 0.2
        samples = int(sample_rate * duration)
        
        arr = array.array("h")
        for i in range(samples):
            t = i / sample_rate
            # Резкий клик с тоном
            val = int(12000 * math.exp(-t * 15) * (
                math.sin(2 * math.pi * 800 * t) * 0.7 +
                math.sin(2 * math.pi * 1200 * t) * 0.3
            ))
            arr.append(val)
            arr.append(val)
        
        sound = pygame.sndarray.make_sound(arr)
        sound.set_volume(0.5)
        return sound
    
    def _gen_upgrade(self) -> pygame.mixer.Sound:
        """Генерирует звук апгрейда."""
        sample_rate = 22050
        duration = 0.5
        samples = int(sample_rate * duration)
        
        arr = array.array("h")
        for i in range(samples):
            t = i / sample_rate
            # Восходящий тон
            freq = 300 + t * 400
            val = int(10000 * math.exp(-t * 2) * math.sin(2 * math.pi * freq * t))
            arr.append(val)
            arr.append(val)
        
        sound = pygame.sndarray.make_sound(arr)
        sound.set_volume(0.5)
        return sound
    
    def play(self, name: str) -> None:
        """Воспроизводит звук по имени."""
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            try:
                sound.play()
            except Exception:
                pass
    
    def get_random_phrase(self, category: str) -> str:
        """Возвращает случайную украинскую фразу."""
        phrases = getattr(self, f"{category}_phrases", [])
        return random.choice(phrases) if phrases else ""
