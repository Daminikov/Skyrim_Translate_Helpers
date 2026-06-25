# Skyrim_Translate_Helpers

Скрипты Python для более удобного и автоматизированного перевода модификаций с помощью нейросетей (Grok, ChatGPT, Claude и.т.д).

---

## 📁 Структура проекта

```text
S:\Translate\
│
├── build_database.py                    # Скрипт 1: Извлечение базы из ESP-ESM Translator
├── generate_prompts_to_AI_TXT.py        # Скрипт 2: Генерация промптов для .txt файлов
├── generate_prompts_to_AI_XML.py        # Скрипт 3: Работа с .xml файлами
│
├── base/                          # Папка с базами переводов
│   ├── BDD_SkyrimSE_EN-RU.json    # Основная база Skyrim SE (Приоритет 3)
│   ├── Custom_Pet9948.json        # База мода Custom Pet (Приоритет 2)
│   ├── User_Base.json             # Ваш личный словарь (Приоритет 4 - ВЫСШИЙ)
│   ├── Exceptions.json            # Слова-исключения (не попадают в промпт)
│   └── _compiled_glossary.pkl     # Кеш оптимизированного словаря
│
├── prompts/                       # Папка с результатами
│   ├── templates/                 # Шаблоны промптов
│   │   ├── skyrim.txt             # Шаблон для Skyrim
│   │   ├── XML_skyrim.txt         # XML-шаблон (игнорируется в txt-скрипте)
│   │   └── custom.txt             # Ваш кастомный шаблон
│   ├── имя_PROMPT.txt             # Сгенерированный промпт
│   └── ...
│
├── input/                     # Папка для вставки переводов (XML)
│   ├── имя_translated.txt
│   └── ...
│
├── translation_debug.log      # Лог работы скриптов
└── *.txt, *.xml               # Ваши исходные файлы для перевода
```
## 🛠 Скрипт 1: build_database.py
🎯 Назначение
Извлекает переводы из базы ESP-ESM Translator 4.35 и сохраняет их в удобные JSON-файлы в папке base/. Предварительно необходимо конвертировать базу данных из формата .eet в .xml.

⚙️ Настройки (в начале скрипта)
```
EET_DATABASE_PATH = r"S:\ESP-ESM Translator 4.35\BDD"  # Путь к базе EET
BASE_FOLDER = Path('base')                             # Куда сохранять JSON

# Разрешенные группы (GRUP). Берем то, что будет в базе:
ALLOWED_GRUPS = [...]
```
