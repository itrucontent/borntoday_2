import os
import sys
import django
import datetime
import re
import pandas as pd
import shutil
from django.db import transaction
from django.conf import settings

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'borntoday.settings')
django.setup()

# Импортируем модели после настройки Django
from star.models import Star, Country, Category


def parse_date(date_str):
    """Преобразует строку даты в объект datetime.date."""
    if not date_str or pd.isna(date_str):
        return None

    # Проверяем формат даты
    if isinstance(date_str, str):
        # Для формата "1978-02-07"
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            year, month, day = map(int, date_str.split('-'))
            return datetime.date(year, month, day)
        # Для формата "1978-02-07 00:00:00"
        elif re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', date_str):
            date_part = date_str.split(' ')[0]
            year, month, day = map(int, date_part.split('-'))
            return datetime.date(year, month, day)
    # Если уже является datetime объектом
    elif isinstance(date_str, datetime.datetime):
        return date_str.date()

    return None


def copy_image(img_filename, star_name):
    """Копирует изображение из папки img в медиа-директорию Django с проверкой на существование."""
    if not img_filename or pd.isna(img_filename):
        return None

    # Путь к исходному файлу
    source_path = os.path.join('img', img_filename)

    # Проверяем, что файл существует
    if not os.path.exists(source_path):
        print(f"Предупреждение: файл {source_path} не найден для '{star_name}'")
        return None

    # Проверяем, существует ли уже такой файл в медиа-директории
    # Ищем в различных подпапках photos
    for root, dirs, files in os.walk(os.path.join(settings.MEDIA_ROOT, 'photos')):
        if img_filename in files:
            # Файл уже существует, возвращаем его относительный путь
            rel_path = os.path.relpath(os.path.join(root, img_filename), settings.MEDIA_ROOT)
            print(f"Файл {img_filename} уже существует, используем существующий для '{star_name}'")
            return rel_path

    # Файл не существует, создаем новый
    # Создаем структуру директорий для целевого пути
    today = datetime.date.today()
    target_dir = os.path.join(settings.MEDIA_ROOT, 'photos',
                              str(today.year),
                              str(today.month).zfill(2),
                              str(today.day).zfill(2))

    # Создаем папку, если она не существует
    os.makedirs(target_dir, exist_ok=True)

    # Полный путь к целевому файлу
    target_path = os.path.join(target_dir, img_filename)

    # Копируем файл
    shutil.copy2(source_path, target_path)

    # Возвращаем относительный путь для сохранения в БД
    relative_path = f'photos/{today.year}/{str(today.month).zfill(2)}/{str(today.day).zfill(2)}/{img_filename}'
    return relative_path


def clear_database():
    """Очищает базу данных от существующих записей."""
    confirmation = input("Вы уверены, что хотите удалить ВСЕ существующие данные? (y/n): ")
    if confirmation.lower() != 'y':
        print("Операция отменена.")
        return False

    print("Удаление существующих данных...")
    Star.objects.all().delete()
    Category.objects.all().delete()
    Country.objects.all().delete()
    print("Данные удалены.")
    return True


@transaction.atomic
def import_stars_from_excel(file_path, clear_existing=False, update_existing=False):
    """Импортирует знаменитостей из Excel-файла."""

    # Очистка существующих данных, если указан флаг
    if clear_existing and not clear_database():
        return

    print(f"Начинаем импорт данных из {file_path}...")

    # Проверяем, существует ли файл
    if not os.path.exists(file_path):
        print(f"Ошибка: файл {file_path} не найден.")
        return

    try:
        # Читаем Excel-файл
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Ошибка при чтении Excel-файла: {e}")
        return

    # Проверяем наличие обязательных колонок
    required_columns = ['Name', 'Country', 'Categories', 'Born', 'Txt']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Ошибка: в файле отсутствуют обязательные колонки: {', '.join(missing_columns)}")
        return

    # Создаем словари для кеширования стран и категорий
    countries_cache = {}
    categories_cache = {}

    # Счетчики для статистики
    created_count = 0
    skipped_count = 0
    updated_count = 0
    error_count = 0

    for index, row in df.iterrows():
        try:
            # Проверяем, существует ли уже такая знаменитость
            existing_star = Star.objects.filter(name=row['Name']).first()

            if existing_star:
                if update_existing:
                    print(f"Обновляем знаменитость: {row['Name']}")

                    # Обновляем текстовые поля
                    existing_star.wikipedia = row['Wiki'] if 'Wiki' in row and not pd.isna(
                        row['Wiki']) else existing_star.wikipedia
                    existing_star.ruwiki = row['Ruwiki'] if 'Ruwiki' in row and not pd.isna(
                        row['Ruwiki']) else existing_star.ruwiki
                    existing_star.rating = row['Rating'] if 'Rating' in row and not pd.isna(
                        row['Rating']) else existing_star.rating
                    existing_star.content = row['Txt'] if 'Txt' in row and not pd.isna(
                        row['Txt']) else existing_star.content

                    # Обновляем даты
                    birth_date = parse_date(row['Born'])
                    if birth_date:
                        existing_star.birth_date = birth_date

                    death_date = parse_date(row['Death']) if 'Death' in row and row['Death'] else None
                    if death_date:
                        existing_star.death_date = death_date

                    # Проверяем, нужно ли обновить фото
                    if 'Img' in row and row['Img'] and not existing_star.photo:
                        photo_path = copy_image(row['Img'], row['Name'])
                        if photo_path:
                            existing_star.photo = photo_path

                    # Сохраняем изменения
                    existing_star.save()

                    # Можно также обновить категории, если нужно
                    if 'Categories' in row and not pd.isna(row['Categories']):
                        category_names = str(row['Categories']).split('|')
                        for category_name in category_names:
                            category_name = category_name.strip()
                            if not category_name:
                                continue

                            if category_name in categories_cache:
                                category = categories_cache[category_name]
                            else:
                                category, created = Category.objects.get_or_create(title=category_name)
                                categories_cache[category_name] = category

                            existing_star.categories.add(category)

                    updated_count += 1
                else:
                    print(f"Знаменитость {row['Name']} уже существует, пропускаем")
                    skipped_count += 1
                continue

            # Обрабатываем страны
            countries = str(row['Country']).split('|') if '|' in str(row['Country']) else [str(row['Country'])]
            country_objects = []

            for country_name in countries:
                country_name = country_name.strip()
                if not country_name:
                    continue

                if country_name in countries_cache:
                    country = countries_cache[country_name]
                else:
                    country, created = Country.objects.get_or_create(name=country_name)
                    countries_cache[country_name] = country
                country_objects.append(country)

            if not country_objects:
                print(f"Предупреждение: не указана страна для {row['Name']}, используем 'Неизвестно'")
                country, created = Country.objects.get_or_create(name='Неизвестно')
                country_objects.append(country)

            # Обрабатываем категории
            category_names = str(row['Categories']).split('|') if '|' in str(row['Categories']) else [
                str(row['Categories'])]
            category_objects = []

            for category_name in category_names:
                category_name = category_name.strip()
                if not category_name:
                    continue

                if category_name in categories_cache:
                    category = categories_cache[category_name]
                else:
                    category, created = Category.objects.get_or_create(title=category_name)
                    categories_cache[category_name] = category
                category_objects.append(category)

            if not category_objects:
                print(f"Предупреждение: не указана категория для {row['Name']}, используем 'Другое'")
                category, created = Category.objects.get_or_create(title='Другое')
                category_objects.append(category)

            # Парсим даты
            birth_date = parse_date(row['Born'])
            if not birth_date:
                print(f"Ошибка: неверный формат даты рождения для {row['Name']}, пропускаем")
                error_count += 1
                continue

            death_date = parse_date(row['Death']) if 'Death' in row and row['Death'] else None

            # Копируем изображение
            photo_path = None
            if 'Img' in row and row['Img']:
                photo_path = copy_image(row['Img'], row['Name'])

            # Создаем объект звезды
            star = Star(
                name=row['Name'],
                country=country_objects[0],  # Основная страна (первая в списке)
                birth_date=birth_date,
                death_date=death_date,
                content=row['Txt'],
                is_published=True,
                wikipedia=row['Wiki'] if 'Wiki' in row and not pd.isna(row['Wiki']) else None,
                ruwiki=row['Ruwiki'] if 'Ruwiki' in row and not pd.isna(row['Ruwiki']) else None,
                rating=row['Rating'] if 'Rating' in row and not pd.isna(row['Rating']) else 0
            )

            # Устанавливаем фото, если оно есть
            if photo_path:
                star.photo = photo_path

            # Сохраняем для создания slug
            star.save()

            # Добавляем категории
            for category in category_objects:
                star.categories.add(category)

            print(f"Создана знаменитость: {star.name}")
            created_count += 1

        except Exception as e:
            print(f"Ошибка при обработке знаменитости {row.get('Name', 'Неизвестно')}: {e}")
            error_count += 1

    print(f"\nИмпорт завершен:")
    print(f"- Создано: {created_count}")
    print(f"- Обновлено: {updated_count}")
    print(f"- Пропущено: {skipped_count}")
    print(f"- Ошибок: {error_count}")


if __name__ == "__main__":
    # Проверяем аргументы командной строки
    clear_existing = False
    update_existing = False
    file_path = 'persons-1000.xlsx'

    # Парсим аргументы командной строки
    for arg in sys.argv[1:]:
        if arg == '--clear' or arg == '-c':
            clear_existing = True
        elif arg == '--update' or arg == '-u':
            update_existing = True
        elif os.path.exists(arg):
            file_path = arg

    # Запускаем импорт
    import_stars_from_excel(file_path, clear_existing, update_existing)