from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Star, Country, Category
from datetime import datetime, date, timedelta
import calendar


class StarSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.9
    limit = 1000  # Ограничиваем количество URL в одном файле

    def items(self):
        return Star.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.time_update

    def location(self, obj):
        return reverse('star_detail', kwargs={'slug': obj.slug})


class CountrySitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Country.objects.all()

    def location(self, obj):
        return reverse('stars_by_country', kwargs={'slug': obj.slug})


class CategorySitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse('stars_by_category', kwargs={'slug': obj.slug})


class BirthdaySitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.7

    def items(self):
        # Используем annotate + distinct для извлечения только месяца и дня
        from django.db.models.functions import Extract

        # Получаем только уникальные комбинации месяц-день
        unique_dates = Star.objects.filter(is_published=True).annotate(
            month=Extract('birth_date', 'month'),
            day=Extract('birth_date', 'day')
        ).values_list('month', 'day').distinct()

        # Проверяем валидность дат и удаляем дубликаты
        valid_dates = []
        seen = set()

        for month, day in unique_dates:
            if month is None or day is None:
                continue

            # Проверяем валидность
            try:
                if 1 <= month <= 12 and 1 <= day <= 31:
                    # Создаем ключ для отслеживания уникальности
                    key = f"{month}-{day}"
                    if key not in seen:
                        seen.add(key)
                        valid_dates.append((month, day))
            except (ValueError, TypeError):
                # Пропускаем невалидные значения
                pass

        # УДАЛЕНА строка с self.stdout, которая вызывала ошибку
        return valid_dates

    def location(self, obj):
        month, day = obj
        return reverse('birthday', kwargs={'month': month, 'day': day})


class StaticSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return ['star_index', 'about', 'dates', 'celebrities', 'rules', 'names']

    def location(self, item):
        return reverse(item)


class NamesSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        # Получаем все буквы, для которых есть знаменитости
        letters = []
        for letter in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ':
            if Star.objects.filter(is_published=True, name__istartswith=letter).exists():
                letters.append(letter)
        return letters

    def location(self, obj):
        return reverse('names_letter', kwargs={'letter': obj})