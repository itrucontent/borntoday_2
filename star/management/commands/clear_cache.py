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
        cache.delete_pattern('*_birthday_*')

        self.stdout.write(
            self.style.SUCCESS(f'Кэш для {today} успешно очищен')
        )