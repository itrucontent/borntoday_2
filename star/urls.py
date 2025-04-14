from django.urls import path
from django.views.decorators.cache import cache_page
from . import views
from django.contrib.sitemaps.views import sitemap


# Время кэширования
DAY = 60 * 60 * 24  # 24 часа
WEEK = DAY * 7  # 7 дней

urlpatterns = [
    # Главная страница - кэшируем на день, но очищаем в полночь
    path('', views.index, name='star_index'),

    # Детальные страницы знаменитостей - кэшируем на неделю
    path('person/<slug:slug>/', views.star_detail, name='star_detail'),

    # Страницы с формами - не кэшируем
    path('about/', views.about, name='about'),
    path('add/', views.add_star, name='add_star'),
    path('search/', views.search, name='search'),

    # Каталожные страницы - кэшируем на день
    path('country/<slug:slug>/', views.stars_by_country, name='stars_by_country'),
    path('industry/<slug:slug>/', views.stars_by_category, name='stars_by_category'),
    path('tag/<slug:tag_slug>/', views.tag, name='tag'),

    # Календарные страницы - кэшируем на день
    path('birthday/<int:month>-<int:day>/', views.birthday, name='birthday'),
    path('dates/', views.dates, name='dates'),

    # Статические страницы - кэшируем долго
    path('celebrities/', views.celebrities, name='celebrities'),
    path('rules/', views.rules, name='rules'),
    path('names/', views.names, name='names'),
    path('names/<str:letter>/', views.names_letter, name='names_letter'),
]