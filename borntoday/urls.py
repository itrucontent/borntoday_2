from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap, index as sitemap_index
from django.views.decorators.cache import cache_page
from django.views.generic.base import RedirectView
from django.http import HttpResponse
from star.sitemaps import StarSitemap, CountrySitemap, CategorySitemap, BirthdaySitemap, StaticSitemap, NamesSitemap
from .views import robots_txt

# Определяем словарь с картами сайта
sitemaps = {
    'stars': StarSitemap,
    'countries': CountrySitemap,
    'categories': CategorySitemap,
    'birthdays': BirthdaySitemap,
    'static': StaticSitemap,
    'names': NamesSitemap,
}






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
    path('robots.txt', robots_txt, name='robots_txt'),
]

# Добавляем обслуживание медиа-файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)