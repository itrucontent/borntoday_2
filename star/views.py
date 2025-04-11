import re
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseNotFound
from django.db.models import Count, Q, F, Case, When, Value, IntegerField
from django.core.paginator import Paginator
from datetime import date, timedelta
import calendar
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.cache import cache_page
from django.utils.functional import cached_property

from .models import Star, Country, Category, FeedbackMessage
from .forms import StarForm, ContactForm
from .utils import GenitiveCountry

# Определяем константы для TTL кэша
CACHE_DAY = 60 * 60 * 24  # 24 часа
CACHE_WEEK = 60 * 60 * 24 * 7  # 7 дней
CACHE_HOUR = 60 * 60  # 1 час


def get_coming_birthday_order():
    """
    Создает выражение для сортировки по ближайшему дню рождения.
    Оптимизировано для PostgreSQL.
    """
    today = date.today()
    from django.db.models.functions import Extract

    # Используем Extract для эффективной работы с частями даты в PostgreSQL
    month = Extract('birth_date', 'month')
    day = Extract('birth_date', 'day')

    # Создаем выражение для подсчета дней до следующего дня рождения
    return Case(
        # Если день рождения еще впереди в этом году
        When(
            Q(birth_date__month__gt=today.month) |
            Q(birth_date__month=today.month, birth_date__day__gt=today.day),
            then=month * 100 + day - (today.month * 100 + today.day)
        ),
        # Если день рождения уже прошел в этом году, добавляем 12 месяцев
        default=month * 100 + day + 1200 - (today.month * 100 + today.day),
        output_field=IntegerField()
    )


def get_calendar_days(year, month):
    """
    Генерирует календарные дни для отображения в мини-календаре.
    Результат кэшируется.
    """
    cache_key = f'calendar_days_{year}_{month}'
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    # Получаем календарь на месяц
    cal = calendar.monthcalendar(year, month)

    # Форматируем для шаблона
    weeks = []
    for week in cal:
        days = []
        for day in week:
            if day == 0:
                days.append({'number': '', 'in_month': False})
            else:
                days.append({'number': day, 'in_month': True})
        weeks.append(days)

    # Кэшируем результат на неделю
    cache.set(cache_key, weeks, CACHE_WEEK)

    return weeks


def get_page_range(paginator, page, on_each_side=2, on_ends=1):
    """
    Возвращает ограниченный диапазон страниц для пагинации.
    """
    page_range = []

    # Добавляем страницы в начале диапазона
    for i in range(1, min(on_ends + 1, paginator.num_pages + 1)):
        page_range.append(i)

    # Страницы вокруг текущей
    start = max(page.number - on_each_side, on_ends + 1)
    end = min(page.number + on_each_side, paginator.num_pages - on_ends)

    # Добавляем разделитель, если нужно
    if start > on_ends + 1:
        page_range.append(None)  # None будет представлять "..."

    # Добавляем страницы вокруг текущей
    for i in range(start, end + 1):
        if i not in page_range:
            page_range.append(i)

    # Добавляем разделитель, если нужно
    if end < paginator.num_pages - on_ends:
        page_range.append(None)  # None будет представлять "..."

    # Добавляем страницы в конце диапазона
    for i in range(max(paginator.num_pages - on_ends + 1, end + 1), paginator.num_pages + 1):
        if i not in page_range:
            page_range.append(i)

    return page_range


def check_tag_viability(category_slug, country_slug):
    """
    Проверяет, содержит ли виртуальная категория достаточное количество знаменитостей.
    Результат кэшируется.
    """
    cache_key = f'tag_viability_{category_slug}_{country_slug}'
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    try:
        category = Category.objects.get(slug=category_slug)
        country = Country.objects.get(slug=country_slug)

        count = Star.objects.filter(
            is_published=True,
            categories=category,
            countries=country
        ).count()

        result = count >= 10
        # Кэшируем результат на неделю
        cache.set(cache_key, result, CACHE_WEEK)
        return result
    except (Category.DoesNotExist, Country.DoesNotExist):
        return False


def get_viable_tags(category, limit=None):
    """
    Возвращает список жизнеспособных виртуальных категорий для данной категории.
    Результат кэшируется.
    """
    cache_key = f'viable_tags_category_{category.id}_{limit}'
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    viable_tags = []
    countries = Country.objects.all()

    for country in countries:
        count = Star.objects.filter(
            is_published=True,
            categories=category,
            countries=country
        ).count()

        if count >= 10:
            viable_tags.append({
                'slug': f"{category.slug}-{country.slug}",
                'name': country.name,
                'count': count
            })

    # Сортируем по количеству знаменитостей
    viable_tags.sort(key=lambda x: x['count'], reverse=True)

    # Ограничиваем, если нужно
    if limit and len(viable_tags) > limit:
        viable_tags = viable_tags[:limit]

    # Кэшируем результат на день
    cache.set(cache_key, viable_tags, CACHE_DAY)

    return viable_tags


def get_viable_country_tags(country, limit=None):
    """
    Возвращает список жизнеспособных виртуальных категорий для данной страны.
    Результат кэшируется.
    """
    cache_key = f'viable_tags_country_{country.id}_{limit}'
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    viable_tags = []
    categories = Category.objects.all()

    for category in categories:
        count = Star.objects.filter(
            is_published=True,
            categories=category,
            countries=country
        ).count()

        if count >= 10:
            viable_tags.append({
                'slug': f"{category.slug}-{country.slug}",
                'title': category.title,
                'name': category.title,  # Добавляем для совместимости с шаблоном
                'count': count
            })

    # Сортируем по количеству знаменитостей
    viable_tags.sort(key=lambda x: x['count'], reverse=True)

    # Ограничиваем, если нужно
    if limit and len(viable_tags) > limit:
        viable_tags = viable_tags[:limit]

    # Кэшируем результат на день
    cache.set(cache_key, viable_tags, CACHE_DAY)

    return viable_tags


def get_top_countries(count=20, exclude_id=None):
    """
    Возвращает топ стран по количеству знаменитостей.
    Результат кэшируется.
    """
    cache_key = f'top_countries_{count}_{exclude_id}'
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    query = Country.objects.annotate(star_count=Count('stars')).order_by('-star_count')

    if exclude_id:
        query = query.exclude(id=exclude_id)

    top_countries = list(query[:count])

    # Кэшируем на день
    cache.set(cache_key, top_countries, CACHE_DAY)

    return top_countries


def get_top_categories(count=10, exclude_id=None):
    """
    Возвращает топ категорий по количеству знаменитостей.
    Результат кэшируется.
    """
    cache_key = f'top_categories_{count}_{exclude_id}'
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    query = Category.objects.annotate(star_count=Count('stars')).order_by('-star_count')

    if exclude_id:
        query = query.exclude(id=exclude_id)

    top_categories = list(query[:count])

    # Кэшируем на день
    cache.set(cache_key, top_categories, CACHE_DAY)

    return top_categories


def get_birthday_stars(month, day, year=None, limit=None):
    """
    Возвращает звезд с днем рождения в указанную дату.
    Результат кэшируется.
    """
    cache_key = f'birthday_stars_{month}_{day}_{year}_{limit}'
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    stars = Star.objects.filter(
        is_published=True,
        birth_date__month=month,
        birth_date__day=day
    )

    if year:
        stars = stars.filter(birth_date__year=year)

    stars = stars.order_by('-rating')

    if limit:
        stars = stars[:limit]

    result = list(stars.prefetch_related('countries', 'categories'))

    # Кэшируем на день
    cache.set(cache_key, result, CACHE_DAY)

    return result


def index(request):
    """Главная страница сайта с кэшированием."""
    # Кэш ключ для всей страницы
    today = date.today()
    cache_key = f'index_page_{today.month}_{today.day}'
    cached_context = cache.get(cache_key)

    if cached_context is not None:
        return render(request, 'star/index.html', cached_context)

    # Получаем текущую дату
    tomorrow = today + timedelta(days=1)

    # Находим звезд с днями рождения сегодня и завтра через кэширующую функцию
    today_stars = get_birthday_stars(today.month, today.day, limit=12)
    tomorrow_stars = get_birthday_stars(tomorrow.month, tomorrow.day, limit=8)

    # Создаем контекст
    context = {
        'today_stars': today_stars,
        'tomorrow_stars': tomorrow_stars,
        'today_date': today,
        'tomorrow_date': tomorrow,
        'today_count': len(today_stars),
        'tomorrow_count': len(tomorrow_stars),
        'title': 'Дни рождения знаменитостей сегодня | Born Today',
    }

    # Кэшируем контекст на один день
    cache.set(cache_key, context, CACHE_DAY)

    return render(request, 'star/index.html', context)


def star_detail(request, slug):
    """Детальная страница звезды с кэшированием."""
    # Кэш ключ для страницы звезды
    cache_key = f'star_detail_{slug}'
    cached_context = cache.get(cache_key)

    if cached_context is not None:
        return render(request, 'star/star-detail.html', cached_context)

    # Получаем объект звезды по slug или выбрасываем 404 ошибку
    star = get_object_or_404(
        Star.objects.prefetch_related('countries', 'categories'),
        slug=slug,
        is_published=True
    )

    # Сет для хранения ID звезд, которые уже были добавлены в блоки
    used_star_ids = {star.id}  # Добавляем текущую звезду, чтобы исключить ее

    # Находим популярные виртуальные категории для этой звезды
    popular_tag_blocks = []

    # Проверяем все комбинации категорий и стран звезды
    for category in star.categories.all():
        for country in star.countries.all():
            # Создаем обертку для отображения в название блока
            genitive_country = GenitiveCountry(country)

            # Ключ кэша для количества знаменитостей
            count_cache_key = f'star_count_category_{category.id}_country_{country.id}'
            count = cache.get(count_cache_key)

            if count is None:
                count = Star.objects.filter(
                    is_published=True,
                    categories=category,
                    countries=country
                ).count()
                cache.set(count_cache_key, count, CACHE_DAY)

            # Если знаменитостей достаточно, добавляем блок
            if count >= 10:
                # Ключ кэша для предпросмотра звезд
                preview_cache_key = f'preview_stars_category_{category.id}_country_{country.id}_exclude_{star.id}'
                preview_stars = cache.get(preview_cache_key)

                if preview_stars is None:
                    # Получаем примеры звезд для предпросмотра
                    preview_stars = list(Star.objects.filter(
                        is_published=True,
                        categories=category,
                        countries=country
                    ).exclude(id__in=used_star_ids).order_by('-rating')[:10])
                    cache.set(preview_cache_key, preview_stars, CACHE_DAY)

                # Фильтруем, оставляя только не использованные ранее звезды
                unique_preview_stars = []
                for preview_star in preview_stars:
                    if preview_star.id not in used_star_ids and len(unique_preview_stars) < 5:
                        unique_preview_stars.append(preview_star)
                        used_star_ids.add(preview_star.id)

                # Если осталось хотя бы 3 уникальных звезды, создаем блок
                if len(unique_preview_stars) >= 3:
                    popular_tag_blocks.append({
                        'slug': f"{category.slug}-{country.slug}",
                        'title': f"{category.title} из {genitive_country.name}",
                        'count': count,
                        'stars': unique_preview_stars
                    })

    # Сортируем блоки по количеству знаменитостей и берем топ-3
    popular_tag_blocks.sort(key=lambda x: x['count'], reverse=True)
    popular_tag_blocks = popular_tag_blocks[:3]

    # Получаем все страны и категории для формы фильтра через кэширующие функции
    countries = cache.get('all_countries')
    if countries is None:
        countries = list(Country.objects.all())
        cache.set('all_countries', countries, CACHE_DAY)

    categories = cache.get('all_categories')
    if categories is None:
        categories = list(Category.objects.all())
        cache.set('all_categories', categories, CACHE_DAY)

    # Создаем контекст
    context = {
        'star': star,
        'popular_tag_blocks': popular_tag_blocks,
        'countries': countries,
        'categories': categories,
        'title': f"{star.name} - биография и день рождения",
    }

    # Кэшируем на неделю, так как детали знаменитости редко меняются
    cache.set(cache_key, context, CACHE_WEEK)

    return render(request, 'star/star-detail.html', context)


def about(request):
    """Страница О сайте с формой обратной связи - не кэшируем."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Создаем новое сообщение обратной связи
            FeedbackMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                topic=form.cleaned_data['topic'],
                message=form.cleaned_data['message']
            )
            messages.success(request, 'Ваше сообщение отправлено! Спасибо за обратную связь.')
            return redirect('about')
    else:
        form = ContactForm()

    # Используем кэшированное значение количества звезд
    star_count = cache.get('star_count')
    if star_count is None:
        star_count = Star.objects.filter(is_published=True).count()
        cache.set('star_count', star_count, CACHE_DAY)

    context = {
        'form': form,
        'title': 'О сайте',
        'description': 'Сайт создан в учебных целях. Данные сгенерированы нейросетью.',
        'star_count': star_count,
    }
    return render(request, 'star/about.html', context)


def stars_by_country(request, slug):
    """Страница знаменитостей по стране с кэшированием."""
    # Базовый кэш-ключ для страницы
    base_cache_key = f'country_{slug}'

    # Получаем параметры сортировки и фильтрации
    sort_by = request.GET.get('sort', 'birthday')
    name_filter = request.GET.get('name', '')
    country_filter = request.GET.get('country', '')
    category_filter = request.GET.get('category', '')
    page_number = request.GET.get('page', 1)

    # Если есть фильтры, не используем базовый кэш
    if not (name_filter or country_filter or category_filter):
        # Полный кэш-ключ включает параметры сортировки и страницы
        cache_key = f'{base_cache_key}_{sort_by}_page{page_number}'
        cached_context = cache.get(cache_key)

        if cached_context is not None:
            return render(request, 'star/country.html', cached_context)

    # Получаем объект страны
    country_obj = get_object_or_404(Country, slug=slug)

    # Базовый набор знаменитостей этой страны
    stars = Star.objects.filter(countries=country_obj, is_published=True)

    # Применяем дополнительные фильтры, если они указаны
    if name_filter:
        stars = stars.filter(name__icontains=name_filter)
    if category_filter:
        category = get_object_or_404(Category, slug=category_filter)
        stars = stars.filter(categories=category)

    # Применяем сортировку
    if sort_by == 'rating':
        stars = stars.order_by('-rating')
    elif sort_by == 'name_asc':
        stars = stars.order_by('name')
    elif sort_by == 'name_desc':
        stars = stars.order_by('-name')
    elif sort_by == 'birthday':
        # Сортировка по ближайшему дню рождения
        coming_birthday_days = get_coming_birthday_order()
        stars = stars.annotate(days_until_birthday=coming_birthday_days).order_by('days_until_birthday')

    # Получаем ТОП-10 виртуальных категорий для этой страны через кэш
    viable_tags = get_viable_country_tags(country_obj, limit=10)
    top_categories = viable_tags

    # Получаем другие популярные страны через кэш
    top_countries = get_top_countries(count=20, exclude_id=country_obj.id)

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров через кэш
    all_countries = cache.get('all_countries')
    if all_countries is None:
        all_countries = list(Country.objects.all())
        cache.set('all_countries', all_countries, CACHE_DAY)

    all_categories = cache.get('all_categories')
    if all_categories is None:
        all_categories = list(Category.objects.all())
        cache.set('all_categories', all_categories, CACHE_DAY)

    # Создаем обертку для отображения в шаблоне
    country = GenitiveCountry(country_obj)

    # Составляем контекст
    context = {
        'stars': page_obj,
        'country': country,
        'country_obj': country_obj,
        'title': f"Знаменитости из {country.name}",
        'all_countries': all_countries,
        'all_categories': all_categories,
        'viable_tags': viable_tags,
        'top_categories': top_categories,
        'top_countries': top_countries,
        'sort_by': sort_by,
        'name_filter': name_filter,
        'country_filter': country_filter,
        'category_filter': category_filter,
        'total_count': stars.count(),
        'page_range': page_range,
    }

    # Сохраняем в кэш только если нет фильтров
    if not (name_filter or country_filter or category_filter):
        cache.set(cache_key, context, CACHE_DAY)

    return render(request, 'star/country.html', context)


def stars_by_category(request, slug):
    """Страница знаменитостей по категории с кэшированием."""
    # Базовый кэш-ключ для страницы
    base_cache_key = f'category_{slug}'

    # Получаем параметры сортировки и фильтрации
    sort_by = request.GET.get('sort', 'birthday')
    name_filter = request.GET.get('name', '')
    country_filter = request.GET.get('country', '')
    category_filter = request.GET.get('category', '')
    page_number = request.GET.get('page', 1)

    # Если есть фильтры, не используем базовый кэш
    if not (name_filter or country_filter or category_filter):
        # Полный кэш-ключ включает параметры сортировки и страницы
        cache_key = f'{base_cache_key}_{sort_by}_page{page_number}'
        cached_context = cache.get(cache_key)

        if cached_context is not None:
            return render(request, 'star/industry.html', cached_context)

    # Получаем объект категории
    category = get_object_or_404(Category, slug=slug)

    # Базовый набор знаменитостей этой категории
    stars = Star.objects.filter(categories=category, is_published=True)

    # Применяем дополнительные фильтры, если они указаны
    if name_filter:
        stars = stars.filter(name__icontains=name_filter)
    if country_filter:
        country = get_object_or_404(Country, slug=country_filter)
        stars = stars.filter(countries=country)

    # Применяем сортировку
    if sort_by == 'rating':
        stars = stars.order_by('-rating')
    elif sort_by == 'name_asc':
        stars = stars.order_by('name')
    elif sort_by == 'name_desc':
        stars = stars.order_by('-name')
    elif sort_by == 'birthday':
        # Сортировка по ближайшему дню рождения
        coming_birthday_days = get_coming_birthday_order()
        stars = stars.annotate(days_until_birthday=coming_birthday_days).order_by('days_until_birthday')

    # Получаем жизнеспособные теги для этой категории через кэш
    viable_tags = get_viable_tags(category, limit=10)
    top_countries = viable_tags

    # Получаем другие популярные категории через кэш
    top_categories = get_top_categories(count=10, exclude_id=category.id)

    # Пагинация
    paginator = Paginator(stars, 20)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров через кэш
    all_countries = cache.get('all_countries')
    if all_countries is None:
        all_countries = list(Country.objects.all())
        cache.set('all_countries', all_countries, CACHE_DAY)

    all_categories = cache.get('all_categories')
    if all_categories is None:
        all_categories = list(Category.objects.all())
        cache.set('all_categories', all_categories, CACHE_DAY)

    # Составляем контекст
    context = {
        'stars': page_obj,
        'category': category,
        'title': f"Знаменитости: {category.title}",
        'all_countries': all_countries,
        'all_categories': all_categories,
        'viable_tags': viable_tags,
        'top_categories': top_categories,
        'top_countries': top_countries,
        'sort_by': sort_by,
        'name_filter': name_filter,
        'country_filter': country_filter,
        'category_filter': category_filter,
        'total_count': stars.count(),
        'page_range': page_range,
    }

    # Сохраняем в кэш только если нет фильтров
    if not (name_filter or country_filter or category_filter):
        cache.set(cache_key, context, CACHE_DAY)

    return render(request, 'star/industry.html', context)


def add_star(request):
    """Представление для добавления новой знаменитости - не кэшируем."""
    if request.method == 'POST':
        form = StarForm(request.POST, request.FILES)
        if form.is_valid():
            star = form.save(commit=False)
            star.is_published = False  # Требует модерации
            star.save()
            form.save_m2m()  # Сохраняем связи many-to-many

            # Очищаем кэш статистики
            cache.delete('star_count')
            cache.delete('site_stats')

            # Если бы знаменитость была опубликована, нужно инвалидировать соответствующие кэши
            if star.is_published:
                today = date.today()
                if star.birth_date.month == today.month and star.birth_date.day == today.day:
                    # Очищаем кэш именинников сегодня
                    cache.delete(f'index_page_{today.month}_{today.day}')
                    cache.delete(f'birthday_stars_{today.month}_{today.day}_None_None')

                # ЗАМЕНЯЕМ НА:
                # Очищаем кэш категорий и стран
                today = date.today()
                # Очищаем общие ключи
                cache.delete('site_stats')
                cache.delete('star_count')
                cache.delete(f'index_page_{today.month}_{today.day}')
                cache.delete(f'birthday_stars_{today.month}_{today.day}_None_None')
                cache.delete('all_countries')
                cache.delete('all_categories')
                cache.delete('celebrities_rating_page1')
                cache.delete('celebrities_birthday_page1')

                # Очищаем кэш для категорий
                for category in star.categories.all():
                    cache.delete(f'category_{category.slug}')
                    cache.delete(f'category_{category.slug}_birthday_page1')
                    cache.delete(f'category_{category.slug}_rating_page1')
                    cache.delete(f'viable_tags_category_{category.id}_10')

                # Очищаем кэш для стран
                for country in star.countries.all():
                    cache.delete(f'country_{country.slug}')
                    cache.delete(f'country_{country.slug}_birthday_page1')
                    cache.delete(f'country_{country.slug}_rating_page1')
                    cache.delete(f'viable_tags_country_{country.id}_10')

            messages.success(request,
                             f'Знаменитость "{star.name}" успешно добавлена и будет опубликована после модерации!')
            return redirect('star_index')
    else:
        form = StarForm()

    context = {
        'form': form,
        'title': 'Добавление знаменитости',
    }
    return render(request, 'star/add-star.html', context)


def search(request):
    """Представление для поиска знаменитостей - кэшируем только популярные страны и категории."""
    query = request.GET.get('q', '')
    country_filter = request.GET.get('country', '')
    category_filter = request.GET.get('category', '')

    # Базовый набор знаменитостей
    stars = Star.objects.filter(is_published=True)

    # Применяем текстовый поиск если указан
    if query:
        # Разбиваем запрос на отдельные слова
        query_words = query.split()
        q_objects = Q()

        # Создаем OR запрос для каждого слова в имени
        for word in query_words:
            # Используем регулярное выражение для поиска без учета регистра
            word_regex = r'(?i)' + re.escape(word)
            q_objects |= Q(name__regex=word_regex)

        stars = stars.filter(q_objects)

    # Применяем фильтр по стране если указан
    if country_filter:
        country = get_object_or_404(Country, slug=country_filter)
        stars = stars.filter(countries=country)

    # Применяем фильтр по категории если указан
    if category_filter:
        category = get_object_or_404(Category, slug=category_filter)
        stars = stars.filter(categories=category)

    # Сортировка результатов
    stars = stars.distinct().order_by('-rating')

    # Кэшированное получение ТОП-20 стран и категорий для сайдбара
    top_countries = get_top_countries(count=20)
    top_categories = get_top_categories(count=20)

    # Пагинация
    paginator = Paginator(stars, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров через кэш
    all_countries = cache.get('all_countries')
    if all_countries is None:
        all_countries = list(Country.objects.all())
        cache.set('all_countries', all_countries, CACHE_DAY)

    all_categories = cache.get('all_categories')
    if all_categories is None:
        all_categories = list(Category.objects.all())
        cache.set('all_categories', all_categories, CACHE_DAY)

    context = {
        'stars': page_obj,
        'query': query,
        'country_filter': country_filter,
        'category_filter': category_filter,
        'top_countries': top_countries,
        'top_categories': top_categories,
        'total_count': stars.count(),
        'title': f'Поиск: {query}' if query else 'Поиск',
        'page_range': page_range,
        'all_countries': all_countries,
        'all_categories': all_categories,
    }
    return render(request, 'star/search.html', context)


def birthday(request, month=None, day=None):
    """Страница с именинниками за определенную дату с кэшированием."""
    today = date.today()
    year_filter = request.GET.get('year')
    page_number = request.GET.get('page', 1)

    # Если дата не указана, используем сегодняшнюю
    if month is None:
        month = today.month
    if day is None:
        day = today.day

    # Формируем кэш-ключ
    cache_key = f'birthday_{month}_{day}_{year_filter}_page{page_number}'
    cached_context = cache.get(cache_key)

    if cached_context is not None:
        return render(request, 'star/birthday.html', cached_context)

    # Пытаемся создать дату для проверки валидности
    try:
        selected_date = date(today.year, int(month), int(day))
    except ValueError:
        # Если дата невалидна (например, 31 февраля), возвращаем 404
        return HttpResponseNotFound("Неверная дата")

    # Получаем знаменитостей, родившихся в эту дату, через кэширующую функцию
    stars = get_birthday_stars(month, day, year=year_filter)

    # Получаем соседние даты для навигации, основываясь на сегодняшней дате
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)
    tomorrow = today + timedelta(days=1)
    day_after_tomorrow = today + timedelta(days=2)

    # Генерируем календарь для текущего месяца через кэширующую функцию
    calendar_weeks = get_calendar_days(today.year, int(month))

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Формируем контекст
    context = {
        'stars': page_obj,
        'selected_date': selected_date,
        'year_filter': year_filter,
        'today': today,
        'yesterday': yesterday,
        'day_before_yesterday': day_before_yesterday,
        'tomorrow': tomorrow,
        'day_after_tomorrow': day_after_tomorrow,
        'title': f'Дни рождения {day} {selected_date.strftime("%B")}' + (f' {year_filter} года' if year_filter else ''),
        'total_count': len(stars),
        'calendar_weeks': calendar_weeks,
        'page_range': page_range,
    }

    # Кэшируем на день
    cache.set(cache_key, context, CACHE_DAY)

    return render(request, 'star/birthday.html', context)


def dates(request):
    """Страница календаря с датами с кэшированием."""
    cache_key = 'dates_page'
    cached_context = cache.get(cache_key)

    if cached_context is not None:
        return render(request, 'star/dates.html', cached_context)

    today = date.today()

    # Получаем вчерашнюю, позавчерашнюю, завтрашнюю и послезавтрашнюю даты
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)
    tomorrow = today + timedelta(days=1)
    day_after_tomorrow = today + timedelta(days=2)

    # Список месяцев для шаблона
    months = [
        (1, 'Январь'),
        (2, 'Февраль'),
        (3, 'Март'),
        (4, 'Апрель'),
        (5, 'Май'),
        (6, 'Июнь'),
        (7, 'Июль'),
        (8, 'Август'),
        (9, 'Сентябрь'),
        (10, 'Октябрь'),
        (11, 'Ноябрь'),
        (12, 'Декабрь')
    ]

    # Генерируем календари для всех месяцев
    calendars = {}
    for month in range(1, 13):
        calendars[month] = get_calendar_days(today.year, month)

    # Формируем контекст
    context = {
        'today': today,
        'yesterday': yesterday,
        'day_before_yesterday': day_before_yesterday,
        'tomorrow': tomorrow,
        'day_after_tomorrow': day_after_tomorrow,
        'calendars': calendars,
        'months': months,
        'title': 'Календарь дней рождения',
    }

    # Кэшируем на неделю (календарь редко меняется)
    cache.set(cache_key, context, CACHE_WEEK)

    return render(request, 'star/dates.html', context)


def celebrities(request):
    """Страница со всеми знаменитостями с кэшированием."""
    # Базовый кэш-ключ для страницы
    base_cache_key = 'celebrities'

    # Получаем параметры сортировки и фильтрации
    sort_by = request.GET.get('sort', 'rating')
    name_filter = request.GET.get('name', '')
    country_filter = request.GET.get('country', '')
    category_filter = request.GET.get('category', '')
    page_number = request.GET.get('page', 1)

    # Если есть фильтры, не используем базовый кэш
    if not (name_filter or country_filter or category_filter):
        # Полный кэш-ключ включает параметры сортировки и страницы
        cache_key = f'{base_cache_key}_{sort_by}_page{page_number}'
        cached_context = cache.get(cache_key)

        if cached_context is not None:
            return render(request, 'star/celebrities.html', cached_context)

    # Базовый набор знаменитостей
    stars = Star.objects.filter(is_published=True)

    # Применяем фильтры
    if name_filter:
        stars = stars.filter(name__icontains=name_filter)
    if country_filter:
        country = get_object_or_404(Country, slug=country_filter)
        stars = stars.filter(countries=country)
    if category_filter:
        category = get_object_or_404(Category, slug=category_filter)
        stars = stars.filter(categories=category)

    # Применяем сортировку
    if sort_by == 'rating':
        stars = stars.order_by('-rating')
    elif sort_by == 'name_asc':
        stars = stars.order_by('name')
    elif sort_by == 'name_desc':
        stars = stars.order_by('-name')
    elif sort_by == 'birthday':
        # Сортировка по ближайшему дню рождения
        coming_birthday_days = get_coming_birthday_order()
        stars = stars.annotate(days_until_birthday=coming_birthday_days).order_by('days_until_birthday')

    # Кэшированное получение ТОП-20 стран и категорий для сайдбара
    top_countries = get_top_countries(count=20)
    top_categories = get_top_categories(count=20)

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров через кэш
    all_countries = cache.get('all_countries')
    if all_countries is None:
        all_countries = list(Country.objects.all())
        cache.set('all_countries', all_countries, CACHE_DAY)

    all_categories = cache.get('all_categories')
    if all_categories is None:
        all_categories = list(Category.objects.all())
        cache.set('all_categories', all_categories, CACHE_DAY)

    # Формируем контекст
    context = {
        'stars': page_obj,
        'title': 'Знаменитости',
        'all_countries': all_countries,
        'all_categories': all_categories,
        'top_countries': top_countries,
        'top_categories': top_categories,
        'sort_by': sort_by,
        'name_filter': name_filter,
        'country_filter': country_filter,
        'category_filter': category_filter,
        'total_count': stars.count(),
        'page_range': page_range,
    }

    # Сохраняем в кэш только если нет фильтров
    if not (name_filter or country_filter or category_filter):
        cache.set(cache_key, context, CACHE_DAY)

    return render(request, 'star/celebrities.html', context)


def tag(request, tag_slug):
    """Страница виртуальной категории (тега) с кэшированием."""
    # Базовый кэш-ключ для страницы
    base_cache_key = f'tag_{tag_slug}'

    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'birthday')
    page_number = request.GET.get('page', 1)

    # Полный кэш-ключ
    cache_key = f'{base_cache_key}_{sort_by}_page{page_number}'
    cached_context = cache.get(cache_key)

    if cached_context is not None:
        return render(request, 'star/tag.html', cached_context)

    # Разбираем slug тега на категорию и страну
    parts = tag_slug.split('-')
    if len(parts) < 2:
        return HttpResponseNotFound("Неверный формат тега")

    # Последняя часть - страна, остальное - категория
    country_slug = parts[-1]
    category_slug = '-'.join(parts[:-1])

    # Проверяем жизнеспособность тега перед отображением
    if not check_tag_viability(category_slug, country_slug):
        return HttpResponseNotFound("Страница не найдена")

    # Получаем объекты категории и страны
    country_obj = get_object_or_404(Country, slug=country_slug)
    category = get_object_or_404(Category, slug=category_slug)

    # Получаем знаменитостей, соответствующих тегу
    stars = Star.objects.filter(
        is_published=True,
        countries=country_obj,
        categories=category
    )

    # Применяем сортировку
    if sort_by == 'rating':
        stars = stars.order_by('-rating')
    elif sort_by == 'name_asc':
        stars = stars.order_by('name')
    elif sort_by == 'name_desc':
        stars = stars.order_by('-name')
    elif sort_by == 'birthday':
        coming_birthday_days = get_coming_birthday_order()
        stars = stars.annotate(days_until_birthday=coming_birthday_days).order_by('days_until_birthday')

    # Кэшированное получение ТОП-20 стран и категорий для сайдбара
    top_countries = get_top_countries(count=20)
    top_categories = get_top_categories(count=20)

    # Пагинация
    paginator = Paginator(stars, 20)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров через кэш
    all_countries = cache.get('all_countries')
    if all_countries is None:
        all_countries = list(Country.objects.all())
        cache.set('all_countries', all_countries, CACHE_DAY)

    all_categories = cache.get('all_categories')
    if all_categories is None:
        all_categories = list(Category.objects.all())
        cache.set('all_categories', all_categories, CACHE_DAY)

    # Создаем обертку для отображения в шаблоне
    country = GenitiveCountry(country_obj)

    # Формируем контекст
    context = {
        'stars': page_obj,
        'country': country,
        'country_obj': country_obj,
        'category': category,
        'title': f"{category.title} из {country.name}",
        'all_countries': all_countries,
        'all_categories': all_categories,
        'top_countries': top_countries,
        'top_categories': top_categories,
        'sort_by': sort_by,
        'total_count': stars.count(),
        'page_range': page_range,
    }

    # Кэшируем на день
    cache.set(cache_key, context, CACHE_DAY)

    return render(request, 'star/tag.html', context)


def rules(request):
    """Страница с правилами сайта с кэшированием."""
    cache_key = 'rules_page'
    cached_context = cache.get(cache_key)

    if cached_context is not None:
        return render(request, 'star/rules.html', cached_context)

    context = {
        'title': 'Правила сайта',
        'today': date.today(),
    }

    # Кэшируем на неделю (правила редко меняются)
    cache.set(cache_key, context, CACHE_WEEK)

    return render(request, 'star/rules.html', context)


def names(request):
    """Страница карты сайта с алфавитным списком с кэшированием."""
    cache_key = 'names_page'
    cached_context = cache.get(cache_key)

    if cached_context is not None:
        return render(request, 'star/names.html', cached_context)

    # Получаем все буквы, с которых начинаются имена знаменитостей
    letters = {}

    # Для каждой буквы получаем первые 20 знаменитостей
    for letter in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ':
        # Кэшируем звезды для каждой буквы
        letter_cache_key = f'names_letter_{letter}_top20'
        stars = cache.get(letter_cache_key)

        if stars is None:
            stars = list(Star.objects.filter(
                is_published=True,
                name__istartswith=letter
            ).order_by('name')[:20])

            # Кэшируем на день
            cache.set(letter_cache_key, stars, CACHE_DAY)

        # Добавляем букву в словарь только если есть знаменитости
        if stars:
            letters[letter] = stars

    # Формируем контекст
    context = {
        'letters': letters,
        'title': 'Карта сайта',
    }

    # Кэшируем на день
    cache.set(cache_key, context, CACHE_DAY)

    return render(request, 'star/names.html', context)


def names_letter(request, letter):
    """Страница со знаменитостями на определенную букву с кэшированием."""
    # Кэш-ключ с учетом страницы пагинации
    page_number = request.GET.get('page', 1)
    cache_key = f'names_letter_{letter.upper()}_page{page_number}'
    cached_context = cache.get(cache_key)

    if cached_context is not None:
        return render(request, 'star/names-letter.html', cached_context)

    # Получаем знаменитостей, имена которых начинаются с указанной буквы
    stars = Star.objects.filter(
        is_published=True,
        name__istartswith=letter.upper()
    ).order_by('name')

    # Если нет знаменитостей на эту букву, возвращаем 404
    if not stars.exists():
        return HttpResponseNotFound(f"Нет знаменитостей на букву {letter.upper()}")

    # Пагинация
    paginator = Paginator(stars, 200)  # По 200 знаменитостей на страницу
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Формируем контекст
    context = {
        'stars': page_obj,
        'letter': letter.upper(),
        'title': f'Знаменитости на букву {letter.upper()}',
        'total_count': stars.count(),
        'page_range': page_range,
    }

    # Кэшируем на день
    cache.set(cache_key, context, CACHE_DAY)

    return render(request, 'star/names-letter.html', context)


# Этот метод нужно добавить в context_processors.py
def site_stats(request):
    """Добавляет общую статистику сайта в контекст шаблонов с кэшированием."""
    cache_key = 'site_stats'
    cached_stats = cache.get(cache_key)

    if cached_stats is None:
        today = date.today()

        # Получаем общее количество звезд
        star_count = Star.objects.filter(is_published=True).count()

        # Получаем количество именинников сегодня
        birthday_count = Star.objects.filter(
            is_published=True,
            birth_date__month=today.month,
            birth_date__day=today.day
        ).count()

        cached_stats = {
            'star_count': star_count,
            'birthday_count': birthday_count,
        }

        # Кэшируем на 24 часа
        cache.set(cache_key, cached_stats, CACHE_DAY)

    return cached_stats