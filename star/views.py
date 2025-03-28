import re

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseNotFound
from django.db.models import Count, Q, F, Case, When, Value, IntegerField
from django.core.paginator import Paginator
from datetime import date, timedelta
import calendar
from .models import Star, Country, Category, FeedbackMessage
from .forms import StarForm, ContactForm


def get_coming_birthday_order():
    """
    Создает выражение для сортировки по ближайшему дню рождения.
    """
    today = date.today()
    # Создаем выражение для подсчета дней до следующего дня рождения
    return Case(
        # Если день рождения еще впереди в этом году
        When(
            Q(birth_date__month__gt=today.month) |
            Q(birth_date__month=today.month, birth_date__day__gt=today.day),
            then=F('birth_date__month') * 31 + F('birth_date__day') - (today.month * 31 + today.day)
        ),
        # Если день рождения уже прошел в этом году, добавляем 365 дней
        default=F('birth_date__month') * 31 + F('birth_date__day') + (365 - (today.month * 31 + today.day)),
        output_field=IntegerField()
    )


def get_calendar_days(year, month):
    """
    Генерирует календарные дни для отображения в мини-календаре.
    """
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
    """
    try:
        category = Category.objects.get(slug=category_slug)
        country = Country.objects.get(slug=country_slug)

        count = Star.objects.filter(
            is_published=True,
            categories=category,
            countries=country
        ).count()

        return count >= 10
    except (Category.DoesNotExist, Country.DoesNotExist):
        return False


def get_viable_tags(category, limit=None):
    """
    Возвращает список жизнеспособных виртуальных категорий для данной категории.
    """
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

    return viable_tags


def get_viable_country_tags(country, limit=None):
    """
    Возвращает список жизнеспособных виртуальных категорий для данной страны.
    """
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

    return viable_tags


def index(request):
    """Главная страница сайта."""
    # Получаем текущую дату
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Находим звезд с днями рождения сегодня, сортируем по рейтингу
    today_stars = Star.objects.filter(
        is_published=True,
        birth_date__month=today.month,
        birth_date__day=today.day
    ).order_by('-rating')[:12]

    # Находим звезд с днями рождения завтра, сортируем по рейтингу
    tomorrow_stars = Star.objects.filter(
        is_published=True,
        birth_date__month=tomorrow.month,
        birth_date__day=tomorrow.day
    ).order_by('-rating')[:8]

    context = {
        'today_stars': today_stars,
        'tomorrow_stars': tomorrow_stars,
        'today_date': today,
        'tomorrow_date': tomorrow,
        'today_count': today_stars.count(),
        'tomorrow_count': tomorrow_stars.count(),
        'title': 'Дни рождения звезд',
    }
    return render(request, 'star/index.html', context)


def star_detail(request, slug):
    """Детальная страница звезды."""
    # Получаем объект звезды по slug или выбрасываем 404 ошибку
    star = get_object_or_404(Star, slug=slug, is_published=True)

    # Удаляем блок "Похожие персоны", так как он больше не нужен
    # similar_stars = Star.objects.filter(
    #     categories__in=star.categories.all(),
    #     is_published=True
    # ).exclude(id=star.id).distinct().order_by('-rating')[:3]

    # Находим популярные виртуальные категории для этой звезды
    popular_tag_blocks = []

    # Сет для хранения ID звезд, которые уже были добавлены в блоки
    used_star_ids = {star.id}  # Добавляем текущую звезду, чтобы исключить ее

    # Проверяем все комбинации категорий и стран звезды
    for category in star.categories.all():
        for country in star.countries.all():
            # Считаем количество знаменитостей в этой виртуальной категории
            count = Star.objects.filter(
                is_published=True,
                categories=category,
                countries=country
            ).count()

            # Если знаменитостей достаточно, добавляем блок
            if count >= 10:
                # Получаем примеры звезд для предпросмотра (берем больше, чтобы была возможность замены)
                preview_stars = Star.objects.filter(
                    is_published=True,
                    categories=category,
                    countries=country
                ).exclude(id__in=used_star_ids).order_by('-rating')[:10]  # Берем больше для фильтрации

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
                        'title': f"{category.title} из {country.name}",
                        'count': count,
                        'stars': unique_preview_stars
                    })

    # Сортируем блоки по количеству знаменитостей и берем топ-3
    popular_tag_blocks.sort(key=lambda x: x['count'], reverse=True)
    popular_tag_blocks = popular_tag_blocks[:3]

    # Получаем все страны и категории для формы фильтра
    countries = Country.objects.all()
    categories = Category.objects.all()

    context = {
        'star': star,
        # Удаляем 'similar_stars': similar_stars,
        'popular_tag_blocks': popular_tag_blocks,
        'countries': countries,
        'categories': categories,
        'title': f"{star.name} - биография и день рождения",
    }

    return render(request, 'star/star-detail.html', context)


def about(request):
    """Страница О сайте с формой обратной связи."""
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

    context = {
        'form': form,
        'title': 'О сайте',
        'description': 'Сайт создан в учебных целях. Данные сгенерированы нейросетью.',
        'star_count': Star.objects.filter(is_published=True).count(),  # Добавим счетчик опубликованных звезд
    }
    return render(request, 'star/about.html', context)


def stars_by_country(request, slug):
    """Страница знаменитостей по стране."""
    country = get_object_or_404(Country, slug=slug)

    # Получаем параметры сортировки и фильтрации
    sort_by = request.GET.get('sort', 'birthday')  # по умолчанию сортировка по ближайшему дню рождения
    name_filter = request.GET.get('name', '')
    country_filter = request.GET.get('country', '')
    category_filter = request.GET.get('category', '')

    # Базовый набор знаменитостей этой страны
    stars = Star.objects.filter(countries=country, is_published=True)

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

    # Получаем ТОП-10 виртуальных категорий для этой страны
    viable_tags = get_viable_country_tags(country, limit=10)
    top_categories = viable_tags

    # Получаем другие популярные страны
    top_countries = Country.objects.exclude(id=country.id).annotate(
        star_count=Count('stars')
    ).order_by('-star_count')[:20]

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров
    all_countries = Country.objects.all()
    all_categories = Category.objects.all()

    context = {
        'stars': page_obj,
        'country': country,
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
    return render(request, 'star/country.html', context)


def stars_by_category(request, slug):
    """Страница знаменитостей по категории."""
    category = get_object_or_404(Category, slug=slug)

    # Получаем параметры сортировки и фильтрации
    sort_by = request.GET.get('sort', 'birthday')  # по умолчанию сортировка по ближайшему дню рождения
    name_filter = request.GET.get('name', '')
    country_filter = request.GET.get('country', '')
    category_filter = request.GET.get('category', '')

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

    # Получаем жизнеспособные теги для этой категории
    viable_tags = get_viable_tags(category, limit=10)
    top_countries = viable_tags

    # Получаем другие популярные категории
    top_categories = Category.objects.exclude(id=category.id).annotate(
        star_count=Count('stars')
    ).order_by('-star_count')[:10]

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров
    all_countries = Country.objects.all()
    all_categories = Category.objects.all()

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
    return render(request, 'star/industry.html', context)


def add_star(request):
    """Представление для добавления новой знаменитости."""
    if request.method == 'POST':
        form = StarForm(request.POST, request.FILES)
        if form.is_valid():
            star = form.save(commit=False)
            star.is_published = False  # Требует модерации
            star.save()
            form.save_m2m()  # Сохраняем связи many-to-many
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
    """Представление для поиска знаменитостей."""
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

    # Получаем ТОП-20 стран и категорий для сайдбара
    top_countries = Country.objects.annotate(
        star_count=Count('stars')
    ).order_by('-star_count')[:20]

    top_categories = Category.objects.annotate(
        star_count=Count('stars')
    ).order_by('-star_count')[:20]

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

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
        'all_countries': Country.objects.all(),
        'all_categories': Category.objects.all(),
    }
    return render(request, 'star/search.html', context)


def birthday(request, month=None, day=None):
    """Страница с именинниками за определенную дату."""
    today = date.today()
    year_filter = request.GET.get('year')

    # Если дата не указана, используем сегодняшнюю
    if month is None:
        month = today.month
    if day is None:
        day = today.day

    # Пытаемся создать дату для проверки валидности
    try:
        selected_date = date(today.year, int(month), int(day))
    except ValueError:
        # Если дата невалидна (например, 31 февраля), возвращаем 404
        return HttpResponseNotFound("Неверная дата")

    # Получаем знаменитостей, родившихся в эту дату
    stars = Star.objects.filter(
        is_published=True,
        birth_date__month=month,
        birth_date__day=day
    )

    # Фильтруем по году, если он указан
    if year_filter:
        try:
            year = int(year_filter)
            stars = stars.filter(birth_date__year=year)
        except ValueError:
            pass

    stars = stars.order_by('-rating')

    # Получаем соседние даты для навигации, но основываясь на сегодняшней дате
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)
    tomorrow = today + timedelta(days=1)
    day_after_tomorrow = today + timedelta(days=2)

    # Генерируем календарь для текущего месяца
    calendar_weeks = get_calendar_days(today.year, int(month))

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

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
        'total_count': stars.count(),
        'calendar_weeks': calendar_weeks,
        'page_range': page_range,
    }
    return render(request, 'star/birthday.html', context)


def dates(request):
    """Страница календаря с датами."""
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
    return render(request, 'star/dates.html', context)


def celebrities(request):
    """Страница со всеми знаменитостями."""
    # Получаем параметры сортировки и фильтрации
    sort_by = request.GET.get('sort', 'rating')  # по умолчанию сортировка по рейтингу
    name_filter = request.GET.get('name', '')
    country_filter = request.GET.get('country', '')
    category_filter = request.GET.get('category', '')

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

    # Получаем ТОП-20 стран и категорий
    top_countries = Country.objects.annotate(
        star_count=Count('stars')
    ).order_by('-star_count')[:20]

    top_categories = Category.objects.annotate(
        star_count=Count('stars')
    ).order_by('-star_count')[:20]

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров
    all_countries = Country.objects.all()
    all_categories = Category.objects.all()

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
    return render(request, 'star/celebrities.html', context)


def tag(request, tag_slug):
    """Страница виртуальной категории (тега)."""
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
    country = get_object_or_404(Country, slug=country_slug)
    category = get_object_or_404(Category, slug=category_slug)

    # Получаем знаменитостей, соответствующих тегу
    stars = Star.objects.filter(
        is_published=True,
        countries=country,
        categories=category
    )

    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'birthday')

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

    # Получаем ТОП-20 стран и категорий для сайдбара
    top_countries = Country.objects.annotate(
        star_count=Count('stars')
    ).order_by('-star_count')[:20]

    top_categories = Category.objects.annotate(
        star_count=Count('stars')
    ).order_by('-star_count')[:20]

    # Пагинация
    paginator = Paginator(stars, 20)  # По 20 знаменитостей на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    # Получаем все страны и категории для фильтров
    all_countries = Country.objects.all()
    all_categories = Category.objects.all()

    context = {
        'stars': page_obj,
        'country': country,
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
    return render(request, 'star/tag.html', context)


def rules(request):
    """Страница с правилами сайта."""
    context = {
        'title': 'Правила сайта',
        'today': date.today(),
    }
    return render(request, 'star/rules.html', context)


def names(request):
    """Страница карты сайта с алфавитным списком."""
    # Получаем все буквы, с которых начинаются имена знаменитостей
    letters = {}

    # Для каждой буквы получаем первые 20 знаменитостей
    for letter in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ':
        stars = Star.objects.filter(
            is_published=True,
            name__istartswith=letter
        ).order_by('name')[:20]

        # Добавляем букву в словарь только если есть знаменитости
        if stars.exists():
            letters[letter] = stars

    context = {
        'letters': letters,
        'title': 'Карта сайта',
    }
    return render(request, 'star/names.html', context)


def names_letter(request, letter):
    """Страница со знаменитостями на определенную букву."""
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
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = get_page_range(paginator, page_obj)

    context = {
        'stars': page_obj,
        'letter': letter.upper(),
        'title': f'Знаменитости на букву {letter.upper()}',
        'total_count': stars.count(),
        'page_range': page_range,
    }
    return render(request, 'star/names-letter.html', context)