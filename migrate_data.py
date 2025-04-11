import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "borntoday.settings")

import django

django.setup()

from django.apps import apps
from django.db import connection, connections
from star.models import Country, Category, Star, FeedbackMessage


def clear_database():
    """Очищает все таблицы в PostgreSQL перед миграцией."""
    print("Очистка существующих данных в PostgreSQL...")
    with connection.cursor() as cursor:
        # Отключаем ограничения внешних ключей во время операции
        cursor.execute("SET CONSTRAINTS ALL DEFERRED;")

        # Сбрасываем все таблицы приложения star
        cursor.execute("""
            TRUNCATE TABLE 
                star_feedbackmessage,
                star_star_countries,
                star_star_categories,
                star_star,
                star_country,
                star_category
            RESTART IDENTITY CASCADE;
        """)

    print("База данных PostgreSQL очищена.")


def migrate_countries():
    print("Миграция стран...")
    with connections['sqlite'].cursor() as cursor:
        cursor.execute("SELECT id, name, name_2, slug FROM star_country")
        rows = cursor.fetchall()

    for row in rows:
        id, name, name_2, slug = row
        country = Country(id=id, name=name, name_2=name_2 or "", slug=slug or "")
        country.save(force_insert=True)
    print(f"Перенесено {len(rows)} стран")


def migrate_categories():
    print("Миграция категорий...")
    with connections['sqlite'].cursor() as cursor:
        cursor.execute("SELECT id, title, slug FROM star_category")
        rows = cursor.fetchall()

    for row in rows:
        id, title, slug = row
        category = Category(id=id, title=title, slug=slug or "")
        category.save(force_insert=True)
    print(f"Перенесено {len(rows)} категорий")


def migrate_stars():
    print("Миграция знаменитостей...")
    with connections['sqlite'].cursor() as cursor:
        cursor.execute("""
            SELECT id, name, slug, birth_date, death_date, content, photo, 
                   rating, wikipedia, ruwiki, is_published, time_create, time_update
            FROM star_star
        """)
        rows = cursor.fetchall()

    # Перенос основных данных
    total = len(rows)
    for i, row in enumerate(rows):
        if i % 100 == 0:
            print(f"Обработано {i}/{total} звезд...")

        id, name, slug, birth_date, death_date, content, photo, rating, wikipedia, ruwiki, is_published, time_create, time_update = row

        # Создаем объект Star
        star = Star(
            id=id,
            name=name,
            slug=slug,
            birth_date=birth_date,
            death_date=death_date,
            content=content,
            photo=photo,
            rating=rating or 0,
            wikipedia=wikipedia,
            ruwiki=ruwiki,
            is_published=bool(is_published),  # Преобразуем int в boolean
            time_create=time_create,
            time_update=time_update,
        )
        # Сохраняем без связей M2M
        star.save(force_insert=True)

    # Теперь переносим связи many-to-many
    print("Перенос связей стран...")
    with connections['sqlite'].cursor() as cursor:
        cursor.execute("SELECT star_id, country_id FROM star_star_countries")
        country_rows = cursor.fetchall()

    for star_id, country_id in country_rows:
        star = Star.objects.get(id=star_id)
        country = Country.objects.get(id=country_id)
        star.countries.add(country)

    print("Перенос связей категорий...")
    with connections['sqlite'].cursor() as cursor:
        cursor.execute("SELECT star_id, category_id FROM star_star_categories")
        category_rows = cursor.fetchall()

    for star_id, category_id in category_rows:
        star = Star.objects.get(id=star_id)
        category = Category.objects.get(id=category_id)
        star.categories.add(category)

    print(f"Перенесено {len(rows)} знаменитостей")


def migrate_feedback():
    print("Миграция сообщений обратной связи...")
    with connections['sqlite'].cursor() as cursor:
        cursor.execute("""
            SELECT id, name, email, topic, message, created_at
            FROM star_feedbackmessage
        """)
        rows = cursor.fetchall()

    for row in rows:
        id, name, email, topic, message, created_at = row
        feedback = FeedbackMessage(
            id=id,
            name=name,
            email=email,
            topic=topic,
            message=message,
            created_at=created_at
        )
        feedback.save(force_insert=True)
    print(f"Перенесено {len(rows)} сообщений")


if __name__ == "__main__":
    print("Начинаем миграцию данных из SQLite в PostgreSQL...")

    # Обновляем settings для использования SQLite в качестве источника
    from django.conf import settings

    databases = settings.DATABASES.copy()
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'borntoday',
            'USER': 'borntoday_user',
            'PASSWORD': 'Born[2025]pass',
            'HOST': 'localhost',
            'PORT': '5432',
        },
        'sqlite': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(settings.BASE_DIR, 'db.sqlite3'),
        }
    }

    # Выполняем миграцию
    try:
        clear_database()  # Сначала очищаем существующие данные
        migrate_countries()
        migrate_categories()
        migrate_stars()
        migrate_feedback()
        print("Миграция данных успешно завершена!")
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
        import traceback

        traceback.print_exc()

    # Восстанавливаем настройки
    settings.DATABASES = databases