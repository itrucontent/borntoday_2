import sqlite3
import psycopg2
import sys
from tqdm import tqdm

print("Начинаем перенос данных из SQLite в PostgreSQL...")

# SQLite соединение
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL соединение
try:
    pg_conn = psycopg2.connect(
        dbname='borntoday',
        user='borntoday_user',
        password='Born[2025]pass',
        host='localhost',
        port='5432'
    )
    pg_conn.autocommit = True
    pg_cursor = pg_conn.cursor()
except Exception as e:
    print(f"Ошибка подключения к PostgreSQL: {e}")
    sys.exit(1)

# Адаптация схемы под данные SQLite - изменим ограничения длины URL
print("Изменение схемы PostgreSQL для поддержки длинных URL...")
try:
    pg_cursor.execute("ALTER TABLE star_star ALTER COLUMN wikipedia TYPE VARCHAR(1000);")
    pg_cursor.execute("ALTER TABLE star_star ALTER COLUMN ruwiki TYPE VARCHAR(1000);")
    pg_cursor.execute("ALTER TABLE star_star ALTER COLUMN photo TYPE VARCHAR(1000);")
except Exception as e:
    print(f"Предупреждение: не удалось изменить схему: {e}")
    # Продолжаем, не прерываем работу

# Очистка существующих данных
print("Очистка существующих данных...")
try:
    pg_cursor.execute("""
        TRUNCATE TABLE 
            star_feedbackmessage,
            star_star_countries,
            star_star_categories,
            star_star,
            star_country,
            star_category
        RESTART IDENTITY CASCADE;
    """)
except Exception as e:
    print(f"Ошибка при очистке данных: {e}")
    sys.exit(1)

# Миграция стран
print("Миграция стран...")
sqlite_cursor.execute("SELECT id, name, name_2, slug FROM star_country")
countries = sqlite_cursor.fetchall()

for country in tqdm(countries, desc="Страны"):
    id, name, name_2, slug = country
    name_2 = name_2 if name_2 is not None else ''
    slug = slug if slug is not None else ''
    pg_cursor.execute(
        "INSERT INTO star_country (id, name, name_2, slug) VALUES (%s, %s, %s, %s)",
        (id, name, name_2, slug)
    )
print(f"Перенесено {len(countries)} стран")

# Миграция категорий
print("Миграция категорий...")
sqlite_cursor.execute("SELECT id, title, slug FROM star_category")
categories = sqlite_cursor.fetchall()

for category in tqdm(categories, desc="Категории"):
    id, title, slug = category
    slug = slug if slug is not None else ''
    pg_cursor.execute(
        "INSERT INTO star_category (id, title, slug) VALUES (%s, %s, %s)",
        (id, title, slug)
    )
print(f"Перенесено {len(categories)} категорий")

# Миграция звезд - пакетный режим для оптимизации
print("Миграция знаменитостей...")
sqlite_cursor.execute("""
    SELECT id, name, slug, birth_date, death_date, content, photo, 
           rating, wikipedia, ruwiki, is_published, time_create, time_update
    FROM star_star
""")
stars = sqlite_cursor.fetchall()

# Используем пакетную вставку для скорости
BATCH_SIZE = 500
star_batches = [stars[i:i + BATCH_SIZE] for i in range(0, len(stars), BATCH_SIZE)]

for batch_idx, batch in enumerate(tqdm(star_batches, desc="Пакеты звезд")):
    values = []
    for star in batch:
        id, name, slug, birth_date, death_date, content, photo, rating, wikipedia, ruwiki, is_published, time_create, time_update = star

        # Обработка NULL значений и преобразование типов
        rating = rating if rating is not None else 0
        wikipedia = (wikipedia if wikipedia is not None else '')[:900]  # Ограничиваем длину URL
        ruwiki = (ruwiki if ruwiki is not None else '')[:900]
        photo = (photo if photo is not None else '')[:900]
        is_published = True if is_published else False

        values.append((id, name, slug, birth_date, death_date, content, photo, rating,
                       wikipedia, ruwiki, is_published, time_create, time_update))

    # Подготавливаем шаблон для массовой вставки
    args_str = ','.join(
        pg_cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in values)

    # Выполняем пакетную вставку
    pg_cursor.execute("""
        INSERT INTO star_star 
        (id, name, slug, birth_date, death_date, content, photo, rating, 
        wikipedia, ruwiki, is_published, time_create, time_update) 
        VALUES """ + args_str)

print(f"Перенесено {len(stars)} знаменитостей")

# Миграция связей звезда-страна - пакетный режим
print("Миграция связей звезда-страна...")
sqlite_cursor.execute("SELECT star_id, country_id FROM star_star_countries")
star_countries = sqlite_cursor.fetchall()

for batch in tqdm([star_countries[i:i + 1000] for i in range(0, len(star_countries), 1000)],
                  desc="Связи со странами"):
    args_str = ','.join(pg_cursor.mogrify("(%s,%s)", x).decode('utf-8') for x in batch)
    pg_cursor.execute("INSERT INTO star_star_countries (star_id, country_id) VALUES " + args_str)

print(f"Перенесено {len(star_countries)} связей звезда-страна")

# Миграция связей звезда-категория - пакетный режим
print("Миграция связей звезда-категория...")
sqlite_cursor.execute("SELECT star_id, category_id FROM star_star_categories")
star_categories = sqlite_cursor.fetchall()

for batch in tqdm([star_categories[i:i + 1000] for i in range(0, len(star_categories), 1000)],
                  desc="Связи с категориями"):
    args_str = ','.join(pg_cursor.mogrify("(%s,%s)", x).decode('utf-8') for x in batch)
    pg_cursor.execute("INSERT INTO star_star_categories (star_id, category_id) VALUES " + args_str)

print(f"Перенесено {len(star_categories)} связей звезда-категория")

# Миграция сообщений обратной связи
print("Миграция сообщений обратной связи...")
sqlite_cursor.execute("""
    SELECT id, name, email, topic, message, created_at
    FROM star_feedbackmessage
""")
feedbacks = sqlite_cursor.fetchall()

for feedback in tqdm(feedbacks, desc="Сообщения"):
    id, name, email, topic, message, created_at = feedback
    pg_cursor.execute(
        """
        INSERT INTO star_feedbackmessage 
        (id, name, email, topic, message, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (id, name, email, topic, message, created_at)
    )
print(f"Перенесено {len(feedbacks)} сообщений")

# Обновление последовательностей
print("Обновление последовательностей...")
tables = ['star_category', 'star_country', 'star_star', 'star_feedbackmessage']
for table in tables:
    pg_cursor.execute(f"""
        SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                      (SELECT MAX(id) FROM {table}), true);
    """)

# Закрытие соединений
sqlite_cursor.close()
sqlite_conn.close()
pg_cursor.close()
pg_conn.close()

print("Миграция успешно завершена!")