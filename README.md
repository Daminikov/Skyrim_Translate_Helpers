📦 Скрипты
1. build_database.py — Сборка базы переводов
Назначение:
Извлекает переводы из базы ESP-ESM Translator 4.35 и сохраняет их в формате JSON в папку base/.

Требование: Предварительно конвертируйте базу данных из .eet в .xml.

Настройки (в начале скрипта):

python
EET_DATABASE_PATH = r"S:\ESP-ESM Translator 4.35\BDD"  # Путь к базе EET
BASE_FOLDER = Path('base')                             # Папка для JSON-файлов
ALLOWED_GRUPS = [...]                                  # Разрешенные группы (GRUP)
Когда запускать:

При первом использовании

После обновления базы ESP-ESM Translator

После добавления новых модов в базу

2. generate_prompts_to_AI_TXT.py — Генерация промптов для .txt
Генерирует готовые промпты для нейросетей (Grok, ChatGPT, Claude) на основе .txt-файлов. Автоматически подгружает релевантный глоссарий из базы для каждого файла.

Приоритет словарей:

Приоритет	Источник
1	Все обычные JSON-файлы
2	Custom_Pet9948.json
3	BDD_SkyrimSE_EN-RU.json
4	User_Base.json (перезаписывает всё!)
Исключения:
Слова из Exceptions.json не попадают в глоссарий промпта.

Шаблоны:
Лежат в prompts/templates/. Первая строка — описание (игнорируется в промпте).

Результат:
В папке prompts/ появляется файл {имя_файла}_PROMPT.txt.

Использование:

Откройте сгенерированный промпт

Скопируйте блок SYSTEM PROMPT в нейросеть

Скопируйте блок USER CONTENT вторым сообщением

Получите перевод с сохранением формата КЛЮЧ | Текст

3. generate_prompts_to_AI_XML.py — Генерация промптов для XML
Обрабатывает файлы переводов .xml из ESP-ESM Translator.

Особенности:

Использует только шаблоны с префиксом XML_ (например, XML_skyrim.txt)

Извлекает тексты из тегов <ORIGINAL>

Вставляет переводы обратно в теги <TRADUIT>

Процесс работы:

Извлечение оригиналов
Скрипт находит все теги <ORIGINAL> в XML:

xml
<ORIGINAL>Thanks for downloading Completionist</ORIGINAL>
<TRADUIT />
Генерация промпта
Формирует строки с номерами:

text
String_number_56 | Thanks for downloading Completionist
String_number_57 | Another text here
Глоссарий извлекается автоматически (как в скрипте 2).

Создание файла для перевода
В папке input/ создаётся {имя}_translated.txt. Вставьте туда перевод.

Вставка переводов обратно
Скрипт спросит:

text
Загрузить перевод в XML? (да/нет):
При ответе «да»:

Читает файл из input/

Извлекает номер строки и перевод

Находит соответствующий тег <TRADUIT> в XML

Вставляет перевод: <TRADUIT>Ваш перевод</TRADUIT>

💡 Полезные советы
🔥 User_Base.json — ваш главный инструмент
Если нейросеть переводит что-то неправильно, добавьте правильный перевод в User_Base.json. Этот файл имеет высший приоритет и перезаписывает любые совпадения из других баз.

🧹 Exceptions.json — чистый глоссарий
Если какие-то слова засоряют промпт и не нужны (например, "Note", "Valid Items"), добавьте их в Exceptions.json. Они не попадут в глоссарий, но нейросеть всё равно переведёт их правильно в контексте.

📝 Шаблоны промптов
Создавайте разные шаблоны для разных задач:

Файл шаблона	Назначение
skyrim.txt	Стандартный перевод Skyrim
XML_skyrim.txt	Для XML-файлов (игнорируется в txt-скрипте)
custom.txt	Экспериментальный шаблон
📂 Структура проекта
text
Skyrim_Translate_Helpers/
├── base/                      # JSON-базы переводов
│   ├── BDD_SkyrimSE_EN-RU.json
│   ├── Custom_Pet9948.json
│   └── User_Base.json
├── prompts/
│   ├── templates/             # Шаблоны промптов
│   │   ├── skyrim.txt
│   │   └── XML_skyrim.txt
│   └── {filename}_PROMPT.txt  # Сгенерированные промпты
├── input/                     # Файлы для перевода
│   └── {filename}_translated.txt
├── Exceptions.json            # Слова-исключения
├── build_database.py
├── generate_prompts_to_AI_TXT.py
└── generate_prompts_to_AI_XML.py
⚙️ Требования
Python 3.6+

ESP-ESM Translator 4.35 (база данных)

