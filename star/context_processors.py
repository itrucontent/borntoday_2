from datetime import date
from .models import Star


def site_stats(request):
    """Добавляет общую статистику сайта в контекст шаблонов."""
    today = date.today()

    # Получаем общее количество звезд
    star_count = Star.objects.filter(is_published=True).count()

    # Получаем количество именинников сегодня
    birthday_count = Star.objects.filter(
        is_published=True,
        birth_date__month=today.month,
        birth_date__day=today.day
    ).count()

    return {
        'star_count': star_count,
        'birthday_count': birthday_count,
    }