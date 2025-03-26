from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='star_index'),
    path('person/<slug:slug>/', views.star_detail, name='star_detail'),
    path('about/', views.about, name='about'),
    path('country/<slug:slug>/', views.stars_by_country, name='stars_by_country'),
    path('industry/<slug:slug>/', views.stars_by_category, name='stars_by_category'),
    path('add/', views.add_star, name='add_star'),

    # Новые URL
    path('search/', views.search, name='search'),
    path('birthday/<int:month>-<int:day>/', views.birthday, name='birthday'),
    path('dates/', views.dates, name='dates'),
    path('celebrities/', views.celebrities, name='celebrities'),
    path('tag/<slug:tag_slug>/', views.tag, name='tag'),
    path('rules/', views.rules, name='rules'),
    path('names/', views.names, name='names'),
    path('names/<str:letter>/', views.names_letter, name='names_letter'),
]