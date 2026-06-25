# Skyrim_Translate_Helpers

Скрипты Python для более удобного и автоматизированного перевода модификаций с помощью нейросетей (Grok, ChatGPT, Claude).

---

## 📁 Структура проекта

```text
S:\Translate\
│
├── build_database.py          # Скрипт 1: Извлечение базы из ESP-ESM Translator
├── generate_prompts.py        # Скрипт 2: Генерация промптов для .txt файлов
├── xml_translate.py           # Скрипт 3: Работа с .xml файлами
│
├── base/                      # Папка с базами переводов
│   ├── BDD_SkyrimSE_EN-RU.json    # Основная база Skyrim SE (Приоритет 3)
│   ├── Custom_Pet9948.json        # База мода Custom Pet (Приоритет 2)
│   ├── User_Base.json             # Ваш личный словарь (Приоритет 4 - ВЫСШИЙ)
│   ├── Exceptions.json            # Слова-исключения (не попадают в промпт)
│   └── _compiled_glossary.pkl     # Кеш оптимизированного словаря
│
├── prompts/                   # Папка с результатами
│   ├── templates/                 # Шаблоны промптов
│   │   ├── skyrim.txt                 # Шаблон для Skyrim
│   │   ├── XML_skyrim.txt             # XML-шаблон (игнорируется в txt-скрипте)
│   │   └── custom.txt                 # Ваш кастомный шаблон
│   ├── Completionist_PROMPT.txt   # Сгенерированный промпт
│   └── ...
│
├── input/                     # Папка для вставки переводов (XML)
│   ├── Completionist_translated.txt
│   └── ...
│
├── translation_debug.log      # Лог работы скриптов
└── *.txt, *.xml               # Ваши исходные файлы для перевода
