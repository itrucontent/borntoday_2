# star/management/commands/warm_cache.py
from django.core.management.base import BaseCommand
from django.test import Client
from datetime import date


class Command(BaseCommand):
    help = 'Подогревает кэш для основных страниц сайта'

    def handle(self, *args, **options):
        client = Client()
        today = date.today()

        self.stdout.write('Подогрев главной страницы...')
        client.get('/')

        self.stdout.write('Подогрев страницы сегодняшних именинников...')
        client.get(f'/birthday/{today.month}-{today.day}/')

        self.stdout.write('Подогрев страницы календаря...')
        client.get('/dates/')

        self.stdout.write('Подогрев страницы знаменитостей...')
        client.get('/celebrities/')

        self.stdout.write(self.style.SUCCESS('Кэш успешно подогрет'))