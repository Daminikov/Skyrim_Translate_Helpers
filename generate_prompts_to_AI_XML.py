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
INPUT_FOLDER = Path('input')

# ==========================================================
# 📝 СИСТЕМА ЛОГИРОВАНИЯ
# ==========================================================
logger = logging.getLogger("XML_Translation_Tool")
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
# 📄 1. СИСТЕМА ШАБЛОНОВ ПРОМПТОВ (ТОЛЬКО XML_*)
# ==========================================================
def load_templates():
    """Загружает только шаблоны, начинающиеся на XML."""
    if not TEMPLATES_FOLDER.exists():
        logger.error(f"Папка {TEMPLATES_FOLDER} не найдена!")
        logger.info("Создайте папку и добавьте шаблоны вручную.")
        sys.exit(1)
    
    templates = []
    all_txt_files = list(TEMPLATES_FOLDER.glob("*.txt"))
    
    # 🔥 Фильтруем: берем ТОЛЬКО файлы, начинающиеся на "XML" (без учета регистра)
    template_files = [
        f for f in all_txt_files 
        if f.stem.upper().startswith('XML')
    ]
    
    if not template_files:
        logger.error(f"В папке {TEMPLATES_FOLDER} нет файлов, начинающихся на XML!")
        sys.exit(1)
    
    logger.info(f"\nНайдено XML-шаблонов: {len(template_files)}")
    
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
        logger.error("Не удалось загрузить ни одного XML-шаблона!")
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
# 📂 7. ПАРСИНГ XML ФАЙЛА
# ==========================================================
def parse_xml_file(input_path):
    """
    Парсит XML файл и извлекает все <ORIGINAL> с номерами строк.
    Возвращает список словарей: [{'line_num': 56, 'original': 'text'}, ...]
    """
    entries = []
    
    try:
        with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            # Ищем <ORIGINAL>...</ORIGINAL>
            match = re.search(r'<ORIGINAL>(.*?)</ORIGINAL>', line)
            if match:
                original_text = match.group(1).strip()
                if original_text:
                    entries.append({
                        'line_num': line_num,
                        'original': original_text
                    })
        
        logger.info(f"  Найдено {len(entries)} тегов <ORIGINAL> в {input_path.name}")
        return entries
        
    except Exception as e:
        logger.error(f"✗ Ошибка чтения {input_path.name}: {e}")
        return []

# ==========================================================
# 📝 8. ГЕНЕРАЦИЯ ПРОМПТА ДЛЯ XML
# ==========================================================
def process_xml_file(input_path, single_words, multi_phrases, words_hash_set, template):
    """Обрабатывает XML файл: извлекает оригиналы, генерирует промпт и создает пустой файл для перевода."""
    try:
        # Парсим XML
        entries = parse_xml_file(input_path)
        
        if not entries:
            logger.warning(f"  ⚠️ В {input_path.name} не найдено тегов <ORIGINAL>")
            return None
        
        # Формируем текст для перевода в формате String_number_XX | текст
        translation_lines = []
        for entry in entries:
            translation_lines.append(f"String_number_{entry['line_num']} | {entry['original']}")
        
        full_text = "\n".join(translation_lines)
        
        # Извлекаем глоссарий
        glossary = extract_relevant_glossary(full_text, single_words, multi_phrases, words_hash_set)
        system_prompt = build_system_prompt(glossary, template)
        
        # Сохраняем промпт
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
        
        logger.info(f"✓ Промпт сохранен: {prompt_file.name}")
        logger.info(f"  Извлечено оригиналов: {len(entries)}")
        logger.info(f"  Найдено терминов в глоссарии: {len(glossary)}")
        
        # 🔥 СОЗДАЕМ ПУСТОЙ ФАЙЛ ДЛЯ ПЕРЕВОДА В ПАПКЕ input/ (только с шапкой)
        INPUT_FOLDER.mkdir(exist_ok=True)
        translated_file = INPUT_FOLDER / f"{input_path.stem}_translated.txt"
        
        with open(translated_file, 'w', encoding='utf-8') as f_out:
            f_out.write("# Вставьте переводы вместо оригинального текста после символа |\n")
            f_out.write("# Формат: String_number_НОМЕР | ВАШ ПЕРЕВОД\n")
            f_out.write("# НЕ МЕНЯЙТЕ номера строк и формат!\n")
            f_out.write("#" + "="*70 + "\n")
        
        logger.info(f"✓ Пустой файл для перевода создан: {translated_file.name}")
        logger.info(f"  Заполните его переводами и нажмите 'да' для вставки в XML")
        
        # Возвращаем entries для последующей вставки переводов
        return entries
        
    except Exception as e:
        logger.error(f"✗ Ошибка обработки {input_path.name}: {e}")
        return None

# ==========================================================
# 📥 9. ВСТАВКА ПЕРЕВОДОВ ОБРАТНО В XML
# ==========================================================
def insert_translations_back(xml_path, entries, input_folder=INPUT_FOLDER):
    """
    Читает переведенный файл из input/ и вставляет переводы обратно в XML.
    """
    translated_file = input_folder / f"{xml_path.stem}_translated.txt"
    
    if not translated_file.exists():
        logger.error(f"✗ Файл перевода не найден: {translated_file}")
        return False
    
    try:
        # Читаем переведенный файл
        with open(translated_file, 'r', encoding='utf-8') as f:
            translated_lines = f.readlines()
        
        # Парсим переводы: извлекаем номер строки и текст
        translations = {}
        for line in translated_lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # Формат: String_number_56 | перевод
            match = re.match(r'String_number_(\d+)\s*\|\s*(.*)', line)
            if match:
                line_num = int(match.group(1))
                translation = match.group(2).strip()
                translations[line_num] = translation
        
        logger.info(f"  Загружено {len(translations)} переводов из {translated_file.name}")
        
        # Читаем исходный XML
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_lines = f.readlines()
        
        # Вставляем переводы
        inserted_count = 0
        for entry in entries:
            line_num = entry['line_num']
            
            if line_num not in translations:
                logger.warning(f"  ⚠️ Нет перевода для строки {line_num}")
                continue
            
            translation = translations[line_num]
            
            # Ищем <TRADUIT> после строки с ORIGINAL
            for i in range(line_num - 1, min(line_num + 10, len(xml_lines))):
                line = xml_lines[i]
                
                # Проверяем, есть ли <TRADUIT> на этой строке
                traduit_match = re.search(r'<TRADUIT>(.*?)</TRADUIT>', line)
                if traduit_match:
                    # Заменяем содержимое
                    old_content = traduit_match.group(1)
                    new_line = line.replace(f'<TRADUIT>{old_content}</TRADUIT>', f'<TRADUIT>{translation}</TRADUIT>')
                    xml_lines[i] = new_line
                    inserted_count += 1
                    break
                
                # Проверяем пустой тег <TRADUIT />
                traduit_empty_match = re.search(r'<TRADUIT\s*/>', line)
                if traduit_empty_match:
                    # Заменяем на <TRADUIT>перевод</TRADUIT>
                    new_line = line.replace('<TRADUIT />', f'<TRADUIT>{translation}</TRADUIT>')
                    xml_lines[i] = new_line
                    inserted_count += 1
                    break
        
        # Сохраняем измененный XML
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.writelines(xml_lines)
        
        logger.info(f"✓ Вставлено {inserted_count} переводов в {xml_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Ошибка вставки переводов: {e}")
        return False

# ==========================================================
# 🚀 ЗАПУСК
# ==========================================================
def main():
    logger.info("="*60)
    logger.info(" XML TRANSLATION TOOL")
    logger.info("="*60)
    
    # Загружаем кеш базы
    single_words, multi_phrases, words_hash_set = load_compiled_glossary()
    
    input_dir = Path('.')
    
    # Ищем только XML файлы
    xml_files = [
        f for f in input_dir.glob('*.xml')
        if not f.name.startswith('_')
    ]
    
    if not xml_files:
        logger.warning("XML файлы не найдены.")
        return
    
    logger.info(f"\nНайдено XML файлов: {len(xml_files)}")
    
    # Загружаем XML-шаблоны
    templates = load_templates()
    selected_template = select_template(templates)
    
    # Обрабатываем каждый XML файл
    for xml_file in xml_files:
        logger.info(f"\n{'='*60}")
        logger.info(f"▶ Обработка: {xml_file.name}")
        logger.info(f"{'='*60}")
        
        entries = process_xml_file(xml_file, single_words, multi_phrases, words_hash_set, selected_template)
        
        if entries:
            # Спрашиваем, загружать ли переводы
            logger.info(f"\nПромпт создан. Переведите текст и сохраните в:")
            logger.info(f"  {INPUT_FOLDER / f'{xml_file.stem}_translated.txt'}")
            
            while True:
                try:
                    answer = input("\nЗагрузить перевод в XML? (да/нет): ").strip().lower()
                    if answer in ['да', 'д', 'yes', 'y']:
                        # Создаем папку input, если её нет
                        INPUT_FOLDER.mkdir(exist_ok=True)
                        
                        # Проверяем наличие файла перевода
                        translated_file = INPUT_FOLDER / f"{xml_file.stem}_translated.txt"
                        if not translated_file.exists():
                            logger.error(f"✗ Файл перевода не найден: {translated_file}")
                            logger.info(f"  Создайте файл и вставьте туда переведенный текст.")
                            continue
                        
                        # Вставляем переводы
                        success = insert_translations_back(xml_file, entries)
                        if success:
                            logger.info("✓ Переводы успешно вставлены в XML!")
                        break
                    elif answer in ['нет', 'н', 'no', 'n']:
                        logger.info("Пропуск вставки переводов.")
                        break
                    else:
                        logger.warning("Введите 'да' или 'нет'")
                except KeyboardInterrupt:
                    logger.info("\nОтменено пользователем.")
                    break
    
    logger.info("\n" + "="*60)
    logger.info(" ВСЕ XML ФАЙЛЫ ОБРАБОТАНЫ!")
    logger.info("="*60)

if __name__ == "__main__":
    main()