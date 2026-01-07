"""Точка входа для мобильного приложения BomberFPV."""
import sys
import os

# Добавляем путь к src для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game import run

if __name__ == "__main__":
    run()
