import re
import sys
import json
import pickle
import hashlib
import logging
from pathlib import Path

# ==========================================================
# ⚙️ НАСТРОЙКИ
# ==========================================================
BASE_FOLDER = Path('base')
COMPILED_CACHE_FILE = BASE_FOLDER / '_compiled_glossary.pkl'
TEMPLATES_FOLDER = Path('prompts/templates')
EXCEPTIONS_FILE = BASE_FOLDER / 'Exceptions.json'

# ==========================================================
# 📝 СИСТЕМА ЛОГИРОВАНИЯ
# ==========================================================
logger = logging.getLogger("Translation_Tool")
logger.setLevel(logging.DEBUG)
if logger.hasHandlers(): logger.handlers.clear()

file_handler = logging.FileHandler("translation_debug.log", mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s'))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(console_handler)

# ==========================================================
# 📄 1. СИСТЕМА ШАБЛОНОВ ПРОМПТОВ
# ==========================================================
def load_templates():
    """Загружает все шаблоны из папки prompts/templates/."""
    if not TEMPLATES_FOLDER.exists():
        logger.error(f"Папка {TEMPLATES_FOLDER} не найдена!")
        logger.info("Создайте папку и добавьте шаблоны вручную.")
        sys.exit(1)
    
    templates = []
    # Получаем все .txt файлы
    all_txt_files = list(TEMPLATES_FOLDER.glob("*.txt"))
    
    # 🔥 Фильтруем файлы, начинающиеся на "XML" (без учета регистра)
    template_files = [
        f for f in all_txt_files 
        if not f.stem.upper().startswith('XML')
    ]
    
    # Считаем количество отфильтрованных файлов
    ignored_count = len(all_txt_files) - len(template_files)
    
    if not template_files:
        logger.error(f"В папке {TEMPLATES_FOLDER} нет подходящих файлов .txt!")
        if ignored_count > 0:
            logger.warning(f"  (Все {ignored_count} файлов были отфильтрованы как XML)")
        sys.exit(1)
    
    logger.info(f"\nНайдено шаблонов: {len(template_files)}")
    if ignored_count > 0:
        logger.info(f"  (Отфильтровано {ignored_count} файлов, начинающихся на XML)")
    
    for i, template_file in enumerate(template_files, 1):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                logger.warning(f"  [{i}] {template_file.name}: пустой файл")
                continue
            
            description = lines[0].strip()
            if description.lower().startswith('описание:'):
                description = description[9:].strip()
            
            template_content = ''.join(lines[1:])
            
            templates.append({
                'name': template_file.name,
                'description': description,
                'content': template_content
            })
            
            logger.info(f"  [{i}] {template_file.name}: {description}")
            
        except Exception as e:
            logger.warning(f"  [{i}] {template_file.name}: ошибка чтения - {e}")
    
    if not templates:
        logger.error("Не удалось загрузить ни одного шаблона!")
        sys.exit(1)
    
    return templates

def select_template(templates):
    """Позволяет пользователю выбрать шаблон."""
    if len(templates) == 1:
        logger.info(f"\nИспользуется единственный шаблон: {templates[0]['name']}")
        return templates[0]['content']
    
    while True:
        try:
            choice = input(f"\nВыберите номер шаблона (1-{len(templates)}): ").strip()
            index = int(choice) - 1
            
            if 0 <= index < len(templates):
                selected = templates[index]
                logger.info(f"\n✓ Выбран шаблон: {selected['name']}")
                return selected['content']
            else:
                logger.warning(f"Неверный номер. Введите число от 1 до {len(templates)}")
        except ValueError:
            logger.warning("Введите число!")
        except KeyboardInterrupt:
            logger.info("\nОтменено пользователем.")
            sys.exit(0)

# ==========================================================
# 🗄 2. ЗАГРУЗКА СЛОВАРЕЙ С ПРИОРИТЕТАМИ
# ==========================================================
def load_raw_dictionaries():
    """Загружает все JSON из base/ с учетом приоритетов."""
    master_dict = {}
    special_files = {'Custom_Pet9948.json': 2, 'BDD_SkyrimSE_EN-RU.json': 3, 'User_Base.json': 4}
    files_to_load = []
    
    for json_file in BASE_FOLDER.glob("*.json"):
        if json_file.name.startswith('_'): continue
        priority = special_files.get(json_file.name, 1)
        files_to_load.append((priority, json_file))
            
    files_to_load.sort(key=lambda x: x[0])
    
    for priority, json_file in files_to_load:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            count = 0
            for k, v in data.items():
                if not k.startswith('_meta') and isinstance(v, str) and v.strip():
                    master_dict[k] = v
                    count += 1
            logger.info(f"  [Приоритет {priority}] {json_file.name}: {count} терминов")
        except Exception as e:
            logger.warning(f"  [!] Ошибка {json_file.name}: {e}")
            
    return master_dict

# ==========================================================
# 🚫 3. ЗАГРУЗКА ИСКЛЮЧЕНИЙ
# ==========================================================
def load_exceptions():
    """Загружает список слов из Exceptions.json."""
    if not EXCEPTIONS_FILE.exists():
        logger.info("  ℹ️ Exceptions.json не найден. Исключения не применяются.")
        return set()
    
    try:
        with open(EXCEPTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            exceptions = set(item.strip() for item in data if isinstance(item, str) and item.strip())
        elif isinstance(data, dict):
            exceptions = set(k.strip() for k in data.keys() if k.strip())
        else:
            logger.warning("  [!] Exceptions.json имеет неподдерживаемый формат.")
            return set()
            
        logger.info(f"  ✓ Загружено {len(exceptions)} исключений из Exceptions.json")
        return exceptions
    except Exception as e:
        logger.warning(f"  [!] Ошибка чтения Exceptions.json: {e}")
        return set()

# ==========================================================
# 📦 4. РАБОТА С КЕШЕМ
# ==========================================================
def calculate_files_hash():
    """Считает хеш от всех исходных файлов в base/."""
    hasher = hashlib.md5()
    for json_file in sorted(BASE_FOLDER.glob("*.json")):
        if json_file.name.startswith('_'): continue
        hasher.update(json_file.name.encode())
        hasher.update(str(json_file.stat().st_size).encode())
        hasher.update(str(json_file.stat().st_mtime).encode())
    return hasher.hexdigest()

def load_compiled_glossary():
    """Загружает готовый кеш или пересобирает базу."""
    current_hash = calculate_files_hash()
    
    if COMPILED_CACHE_FILE.exists():
        try:
            with open(COMPILED_CACHE_FILE, 'rb') as f:
                cache_data = pickle.load(f)
            
            if cache_data.get('hash') == current_hash:
                logger.info("✓ Загружено из кеша (_compiled_glossary.pkl). Мгновенный старт!")
                return (
                    cache_data['single_words'],
                    cache_data['multi_phrases'],
                    cache_data['words_hash_set']
                )
            else:
                logger.info("⚠️ Исходные файлы изменились. Пересборка кеша...")
        except Exception as e:
            logger.warning(f"  [!] Ошибка чтения кеша: {e}. Пересборка...")

    logger.info("Загрузка базы данных с учетом приоритетов...")
    master_dict = load_raw_dictionaries()
    logger.info(f"  Итого сырых терминов: {len(master_dict)}")
    
    logger.info("Применение исключений...")
    exceptions = load_exceptions()
    if exceptions:
        before_count = len(master_dict)
        master_dict = {k: v for k, v in master_dict.items() if k not in exceptions}
        removed_count = before_count - len(master_dict)
        logger.info(f"  ✓ Удалено {removed_count} терминов по исключениям. Осталось: {len(master_dict)}")
    
    logger.info("Оптимизация словаря для мгновенного поиска...")
    single_words = {}
    multi_phrases = []
    
    for k, v in master_dict.items():
        if ' ' in k:
            multi_phrases.append((k.lower(), k, v))
        else:
            single_words[k.lower()] = (k, v)
            
    multi_phrases.sort(key=lambda x: len(x[0]), reverse=True)
    words_hash_set = set(single_words.keys())
    
    try:
        cache_data = {
            'hash': current_hash,
            'single_words': single_words,
            'multi_phrases': multi_phrases,
            'words_hash_set': words_hash_set
        }
        with open(COMPILED_CACHE_FILE, 'wb') as f:
            pickle.dump(cache_data, f)
        logger.info(f"✓ Кеш сохранен: {COMPILED_CACHE_FILE.name}")
    except Exception as e:
        logger.warning(f"  [!] Не удалось сохранить кеш: {e}")
    
    return single_words, multi_phrases, words_hash_set

# ==========================================================
# 🔍 5. ПОИСК ТЕРМИНОВ (RAG)
# ==========================================================
def extract_relevant_glossary(text, single_words, multi_phrases, words_hash_set):
    """Находит все термины из базы, которые встречаются в тексте."""
    found = {}
    text_lower = text.lower()
    
    # 1. Ищем фразы
    for p_lower, p_orig, p_trans in multi_phrases:
        if p_lower in text_lower:
            found[p_orig] = p_trans
            
    # 2. Ищем слова через хеш-таблицу
    words_in_text = set(re.findall(r'\b[a-z]+\b', text_lower))
    for w in words_in_text:
        if w in words_hash_set:
            orig_key, trans = single_words[w]
            found[orig_key] = trans
            
    return found

# ==========================================================
# 🧠 6. ФОРМИРОВАНИЕ ПРОМПТА
# ==========================================================
def build_system_prompt(glossary, template):
    """Вставляет глоссарий в шаблон промпта."""
    if glossary:
        sorted_items = sorted(glossary.items(), key=lambda x: len(x[0]), reverse=True)
        glossary_text = "LORE GLOSSARY (Use these exact translations):\n" + "\n".join([f"- {k} = {v}" for k, v in sorted_items])
    else:
        glossary_text = "LORE GLOSSARY: (No specific terms found)"

    if "{GLOSSARY}" in template:
        return template.replace("{GLOSSARY}", glossary_text)
    return template + "\n\n" + glossary_text

# ==========================================================
# 📂 7. ОБРАБОТКА .TXT ФАЙЛОВ
# ==========================================================
def process_txt_file(input_path, single_words, multi_phrases, words_hash_set, template):
    """Генерирует промпт для .txt файла."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f_in:
            lines = f_in.readlines()
            
        full_text = "".join(lines)
        
        glossary = extract_relevant_glossary(full_text, single_words, multi_phrases, words_hash_set)
        system_prompt = build_system_prompt(glossary, template)
        
        prompts_dir = Path('prompts')
        prompts_dir.mkdir(exist_ok=True)
        
        prompt_file = prompts_dir / f"{input_path.stem}_PROMPT.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f_out:
            f_out.write("="*80 + "\n")
            f_out.write(" SYSTEM PROMPT (Скопируйте это в нейросеть)\n")
            f_out.write("="*80 + "\n\n")
            f_out.write(system_prompt)
            f_out.write("\n\n" + "="*80 + "\n")
            f_out.write(" USER CONTENT (Текст для перевода)\n")
            f_out.write("="*80 + "\n\n")
            f_out.write(full_text)
            
        logger.info(f"✓ [.txt] Промпт сохранен: {prompt_file.name} (Найдено терминов: {len(glossary)})")
        
    except Exception as e:
        logger.error(f"✗ Ошибка обработки {input_path.name}: {e}")

# ==========================================================
# 📂 8. ОБРАБОТКА .JSON ФАЙЛОВ (ЗАГОТОВКА)
# ==========================================================
def process_json_file(input_path):
    """Заготовка для обработки JSON файлов."""
    logger.info(f"⚙️ [.json] {input_path.name}: обработка JSON будет добавлена позже")

# ==========================================================
# 🚀 ЗАПУСК
# ==========================================================
def main():
    logger.info("="*60)
    logger.info(" TRANSLATION TOOL")
    logger.info(" Поддержка: .txt, .json")
    logger.info("="*60)
    
    # Загружаем кеш базы
    single_words, multi_phrases, words_hash_set = load_compiled_glossary()
    
    input_dir = Path('.')
    
    # Ищем файлы для обработки (только .txt и .json)
    all_files = [
        f for f in input_dir.glob('*.*')
        if f.suffix.lower() in ['.txt', '.json']
        and f.name.lower() not in ['readme.txt', 'prompt_template.txt']
        and not f.name.startswith('_')
    ]
    
    if not all_files:
        logger.warning("Файлы .txt, .json не найдены.")
        return
    
    # Группируем файлы по типу
    txt_files = [f for f in all_files if f.suffix.lower() == '.txt']
    json_files = [f for f in all_files if f.suffix.lower() == '.json']
    
    logger.info(f"\nНайдено файлов:")
    logger.info(f"  .txt: {len(txt_files)}")
    logger.info(f"  .json: {len(json_files)}")
    
    # Для .txt файлов нужен шаблон
    selected_template = None
    if txt_files:
        templates = load_templates()
        selected_template = select_template(templates)
    
    # Обрабатываем .txt файлы
    if txt_files:
        logger.info(f"\n{'='*60}")
        logger.info("Обработка .txt файлов")
        logger.info(f"{'='*60}")
        for file_path in txt_files:
            logger.info(f"▶ {file_path.name}")
            process_txt_file(file_path, single_words, multi_phrases, words_hash_set, selected_template)
    
    # Обрабатываем .json файлы
    if json_files:
        logger.info(f"\n{'='*60}")
        logger.info("Обработка .json файлов")
        logger.info(f"{'='*60}")
        for file_path in json_files:
            logger.info(f"▶ {file_path.name}")
            process_json_file(file_path)
    
    logger.info("\n" + "="*60)
    logger.info(" ВСЕ ФАЙЛЫ ОБРАБОТАНЫ!")
    logger.info(" Забирайте промпты из папки 'prompts/'")
    logger.info("="*60)

if __name__ == "__main__":
    main()