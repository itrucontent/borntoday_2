from django.core.management.base import BaseCommand
from django.core.cache import cache
from datetime import date


class Command(BaseCommand):
    help = 'Очищает кэш для ежедневного обновления'

    def handle(self, *args, **options):
        today = date.today()

        # Очищаем кэш для критического контента
        cache.delete(f'index_page_{today.month}_{today.day}')
        cache.delete(f'birthday_stars_{today.month}_{today.day}_None_None')
        cache.delete('site_stats')

        # Очищаем кэш для категорийных страниц с сортировкой по дню рождения
        # ЗАМЕНЯЕМ НА:
        # Очищаем ключевые кэши
        # Главная страница
        cache.delete(f'index_page_{today.month}_{today.day}')
        # Именинники
        cache.delete(f'birthday_stars_{today.month}_{today.day}_None_None')
        # Статистика
        cache.delete('site_stats')
        cache.delete('star_count')
        # Карта сайта
        cache.delete('names_page')
        # Календарь
        cache.delete('dates_page')
        # Категории со звездами, у которых день рождения скоро
        cache.delete('celebrities_birthday_page1')
        # Очищаем кэш для 10 популярных категорий
        for category in range(1, 11):
            cache.delete(f'category_{category}_birthday_page1')
        # Очищаем кэш для 10 популярных стран
        for country in range(1, 11):
            cache.delete(f'country_{country}_birthday_page1')

        self.stdout.write(
            self.style.SUCCESS(f'Кэш для {today} успешно очищен')
        )