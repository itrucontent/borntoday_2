from django.core.management.base import BaseCommand
from django.core.cache import cache
from datetime import date


class Command(BaseCommand):
    help = 'Очищает кэш для ежедневного обновления и карты сайта'

    def handle(self, *args, **options):
        # Начинаем с полной очистки всего кэша
        cache.clear()

        today = date.today()
        self.stdout.write(f'Полностью очищен кэш Redis')

        # Принудительно очищаем ключевые кэши для страниц
        cache.delete(f'index_page_{today.month}_{today.day}')
        cache.delete(f'birthday_stars_{today.month}_{today.day}_None_None')
        cache.delete('site_stats')
        cache.delete('star_count')
        cache.delete('names_page')
        cache.delete('dates_page')
        cache.delete('celebrities_birthday_page1')

        # Очищаем кэши для категорий и стран
        for category in range(1, 11):
            cache.delete(f'category_{category}_birthday_page1')
        for country in range(1, 11):
            cache.delete(f'country_{country}_birthday_page1')

        # Очищаем кэши для карты сайта
        # Для индексного файла и всех его вариаций
        cache.delete('django.contrib.sitemaps.views.index')
        cache.delete('sitemap_index_alt')

        # Для секционных файлов
        for section in ['stars', 'countries', 'categories', 'birthdays', 'static', 'names']:
            cache.delete(f'django.contrib.sitemaps.views.sitemap.{section}')
            # Для пагинированных секций
            for i in range(1, 30):  # Предполагая до 30 страниц
                cache.delete(f'django.contrib.sitemaps.views.sitemap.{section}.{i}')

        self.stdout.write(
            self.style.SUCCESS(f'Кэш для {today} и карты сайта успешно очищен')
        )