# Skyrim Translate Helpers 🐉📜

Набор Python-скриптов для оптимизации перевода модов Skyrim с помощью нейросетей.

---

## 📦 Скрипты

### 1. `build_database.py` — Сборка базы переводов

**Назначение:**  
Извлекает переводы из базы ESP-ESM Translator 4.35 и сохраняет их в формате JSON в папку `base/`.

> **Требование:** Предварительно конвертируйте базу данных из `.eet` в `.xml`.

**Настройки (в начале скрипта):**

```python
EET_DATABASE_PATH = r"S:\ESP-ESM Translator 4.35\BDD"  # Путь к базе EET
BASE_FOLDER = Path('base')                             # Папка для JSON-файлов
ALLOWED_GRUPS = [...]                                  # Разрешенные группы (GRUP)
