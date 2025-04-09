import os
import sys
import django
import pandas as pd

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'borntoday.settings')
django.setup()

# Импортируем модели после настройки Django
from star.models import Country


def import_country_forms(file_path='countries.xlsx'):
    """Импортирует родительные падежи стран из Excel-файла."""

    print(f"Начинаем импорт родительных падежей стран из {file_path}...")

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
    required_columns = ['Country', 'Country-2']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Ошибка: в файле отсутствуют обязательные колонки: {', '.join(missing_columns)}")
        return

    # Счетчики для статистики
    updated_count = 0
    not_found_count = 0

    for index, row in df.iterrows():
        country_name = row['Country']
        country_name_2 = row['Country-2']

        # Ищем страну в базе данных
        country = Country.objects.filter(name=country_name).first()

        if country:
            # Обновляем родительный падеж
            country.name_2 = country_name_2
            country.save()
            print(f"Обновлена страна: {country_name} -> {country_name_2}")
            updated_count += 1
        else:
            print(f"Страна '{country_name}' не найдена в базе данных")
            not_found_count += 1

    print("\nИмпорт завершен:")
    print(f"- Обновлено стран: {updated_count}")
    print(f"- Не найдено стран: {not_found_count}")


if __name__ == "__main__":
    # Проверяем, передан ли путь к файлу в аргументах
    file_path = 'countries.xlsx'
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    import_country_forms(file_path)