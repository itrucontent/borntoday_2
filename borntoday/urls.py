from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap, index as sitemap_index
from django.views.decorators.cache import cache_page
from django.views.generic.base import RedirectView
from django.http import HttpResponse
from star.sitemaps import StarSitemap, CountrySitemap, CategorySitemap, BirthdaySitemap, StaticSitemap, NamesSitemap

# Определяем словарь с картами сайта
sitemaps = {
    'stars': StarSitemap,
    'countries': CountrySitemap,
    'categories': CategorySitemap,
    'birthdays': BirthdaySitemap,
    'static': StaticSitemap,
    'names': NamesSitemap,
}


def debug_birthdays(request):
    from django.http import HttpResponse
    from star.sitemaps import BirthdaySitemap

    # Создаем экземпляр и получаем элементы
    sitemap = BirthdaySitemap()
    items = sitemap.items()

    # Выводим информацию
    response = f"Количество уникальных дат: {len(items)}<br>"
    for month, day in items[:20]:  # Показываем первые 20 элементов
        response += f"{month}-{day}<br>"

    return HttpResponse(response)


def debug_birthdays_detail(request):
    from django.http import HttpResponse
    from django.db.models.functions import Extract
    from star.models import Star

    # Используем annotate для извлечения месяца и дня
    unique_dates = Star.objects.filter(is_published=True).annotate(
        month=Extract('birth_date', 'month'),
        day=Extract('birth_date', 'day')
    ).values_list('month', 'day').distinct()

    # Создаем словарь для отслеживания уникальности
    seen = set()
    valid_dates = []

    for month, day in unique_dates:
        if month is None or day is None:
            continue

        key = f"{month}-{day}"
        if key not in seen:
            seen.add(key)
            valid_dates.append((month, day))

    # Выводим информацию
    response = f"Всего дат из БД: {len(unique_dates)}<br>"
    response += f"Количество уникальных дат (месяц-день): {len(valid_dates)}<br><br>"

    # Сортируем даты для удобства просмотра
    valid_dates.sort()
    for month, day in valid_dates[:50]:  # Показываем первые 50 элементов
        response += f"{month}-{day}<br>"

    return HttpResponse(response)




urlpatterns = [
    # Перенаправляем старый URL на новый
    path('sitemap.xml', RedirectView.as_view(url='/sitemap-index.xml', permanent=True)),
    
    # Индекс карты сайта
    path('sitemap-index.xml', cache_page(86400)(sitemap_index), {'sitemaps': sitemaps},
     name='sitemap_index_alt'),
    
    # Отдельные секции карты сайта
    path('sitemap-<section>.xml', cache_page(86400)(sitemap),
         {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Затем стандартные маршруты
    path('admin/', admin.site.urls),
    path('', include('star.urls')),
]