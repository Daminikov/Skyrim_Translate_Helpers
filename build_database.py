import re
import sys
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# ==========================================================
# НАСТРОЙКИ
# ==========================================================
# Путь к папке BDD от ESP-ESM Translator
EET_DATABASE_PATH = r"S:\ESP-ESM Translator 4.35\BDD"

# Папка, куда будут сохранены готовые JSON-словари
BASE_FOLDER = Path('base')

# Разрешенные группы (GRUP). Берем только то, что содержит имена, предметы, локации и квесты.
ALLOWED_GRUPS = {
    # Персонажи и расы
    'NPC_', 'RACE',
    # Оружие, броня, предметы
    'WEAP', 'ARMO', 'AMMO', 'BOOK', 'ALCH', 'INGR', 'MISC', 'KEYM', 'SLGM', 'SCRL', 'LIGH',
    # Магия, заклинания, эффекты
    'SPEL', 'ENCH', 'MGEF', 'PERK', 'PROJ', 'HAZD', 'EXPL',
    # Мир, локации, погода
    'CELL', 'WRLD', 'REGN', 'WTHR', 'CLMT', 'WATR',
    # Фракции, квесты, диалоги
    'QUST'
}

# ==========================================================
# ФУНКЦИИ ОЧИСТКИ XML
# ==========================================================
def clean_xml_string(raw_xml):
    """Удаляет мусорные символы и битые числовые ссылки, которые ломают парсер XML."""
    # 1. Удаляем сырые недопустимые управляющие символы
    illegal_xml_re = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')
    clean_xml = illegal_xml_re.sub('', raw_xml)
    
    # 2. Исправляем битые числовые ссылки (например, &#x1; или &#2;)
    def fix_char_ref(match):
        ref = match.group(1)
        try:
            code = int(ref[1:], 16) if ref.lower().startswith('x') else int(ref)
            if code in (0x9, 0xA, 0xD) or (0x20 <= code <= 0xD7FF) or (0xE000 <= code <= 0xFFFD) or (0x10000 <= code <= 0x10FFFF):
                return match.group(0)
            return ''
        except ValueError:
            return ''
            
    clean_xml = re.sub(r'&#(x?[0-9a-fA-F]+);', fix_char_ref, clean_xml)
    return clean_xml

# ==========================================================
# ОСНОВНОЙ ПРОЦЕСС ИЗВЛЕЧЕНИЯ
# ==========================================================
def build_database():
    print("=" * 60)
    print(" ГЕНЕРАЦИЯ БАЗЫ ПЕРЕВОДОВ ИЗ ESP-ESM TRANSLATOR")
    print("=" * 60)
    
    eet_folder = Path(EET_DATABASE_PATH)
    if not eet_folder.exists():
        print(f"\n[!] ОШИБКА: Папка базы данных не найдена:")
        print(f"    {EET_DATABASE_PATH}")
        print(f"    Проверьте путь в переменной EET_DATABASE_PATH.")
        return
        
    xml_files = list(eet_folder.glob("*.xml"))
    if not xml_files:
        print(f"\n[!] ОШИБКА: В папке не найдено ни одного .xml файла.")
        return
        
    print(f"\nНайдено XML файлов: {len(xml_files)}")
    print(f"Целевая папка для JSON: {BASE_FOLDER.absolute()}\n")
    
    BASE_FOLDER.mkdir(exist_ok=True)
    total_translations = 0
    start_time = time.time()
    
    for xml_file in xml_files:
        print(f"▶ Обработка: {xml_file.name} ...", end=" ", flush=True)
        file_translations = {}
        
        try:
            # Читаем и чистим XML
            with open(xml_file, 'r', encoding='utf-8', errors='replace') as f:
                raw_xml = f.read()
                
            clean_xml = clean_xml_string(raw_xml)
            
            # Парсим очищенный XML
            root = ET.fromstring(clean_xml)
            
            # Ищем все записи (поддерживаем и старые <BP>, и новые <BDD>)
            for elem in root.iter():
                original_elem = elem.find('ORIGINAL')
                traduit_elem = elem.find('TRADUIT')
                
                if original_elem is None or traduit_elem is None:
                    continue
                    
                original_text = (original_elem.text or '').strip()
                traduit_text = (traduit_elem.text or '').strip()
                
                # Базовые проверки
                if not original_text or not traduit_text:
                    continue
                if original_text.lower() == traduit_text.lower():
                    continue
                if len(original_text) < 2:
                    continue
                if not any(c.isalnum() for c in original_text):
                    continue
                    
                # 🛡️ ФИЛЬТР ПО CHAMP (Берем только полные имена FULL)
                champ_elem = elem.find('CHAMP')
                champ_name = (champ_elem.text or '').strip() if champ_elem is not None else ''
                if champ_name and champ_name != 'FULL':
                    continue
                    
                # 🛡️ ФИЛЬТР ПО GRUP (Если есть, должен быть в списке разрешенных)
                grup_elem = elem.find('GRUP')
                grup_name = (grup_elem.text or '').strip() if grup_elem is not None else ''
                if grup_name and grup_name not in ALLOWED_GRUPS:
                    continue
                    
                # Сохраняем (первое найденное имеет приоритет)
                if original_text not in file_translations:
                    file_translations[original_text] = traduit_text
                    
        except ET.ParseError as e:
            print(f"\n  [!] Ошибка парсинга XML: {e}")
            continue
        except Exception as e:
            print(f"\n  [!] Непредвиденная ошибка: {e}")
            continue
            
        if file_translations:
            # Формируем данные для JSON
            output_data = {
                "_meta": {
                    "source": "ESP-ESM Translator",
                    "source_file": xml_file.name,
                    "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "entries": len(file_translations),
                    "note": "Сгенерировано автоматически. Можно редактировать вручную."
                }
            }
            output_data.update(file_translations)
            
            # Сохраняем JSON
            json_filename = f"{xml_file.stem}.json"
            json_path = BASE_FOLDER / json_filename
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
                
            print(f"OK! Извлечено {len(file_translations)} переводов -> {json_filename}")
            total_translations += len(file_translations)
        else:
            print("Пропущено (нет подходящих записей).")
            
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f" ГОТОВО!")
    print(f" Всего извлечено уникальных переводов: {total_translations}")
    print(f" Время выполнения: {elapsed:.2f} сек.")
    print(f" Файлы сохранены в: {BASE_FOLDER.absolute()}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    build_database()