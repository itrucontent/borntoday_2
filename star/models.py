from django.db import models
from datetime import date  # для работы с датами в методе get_age
from django.utils.text import slugify  # для преобразования строки в slug-формат (URL-безопасный)
from transliterate import translit  # для транслитерации русского текста в латиницу

class Country(models.Model):
    name = models.CharField(max_length=100)  # Название страны
    slug = models.SlugField(max_length=255, unique=True, blank=True, db_index=True, verbose_name="URL")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            # Транслитерация имени с русского на английский
            translit_name = translit(self.name, 'ru', reversed=True)
            # Приведение к нижнему регистру и замена пробелов на дефисы
            base_slug = slugify(translit_name)

            # Проверка уникальности slug
            slug = base_slug
            n = 1
            while Star.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1

            self.slug = slug

        super().save(*args, **kwargs)

class Category(models.Model):
    title = models.CharField(max_length=100)  # Название категории
    slug = models.SlugField(max_length=255, unique=True, blank=True, db_index=True, verbose_name="URL")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            # Транслитерация имени с русского на английский
            translit_name = translit(self.title, 'ru', reversed=True)
            # Приведение к нижнему регистру и замена пробелов на дефисы
            base_slug = slugify(translit_name)

            # Проверка уникальности slug
            slug = base_slug
            n = 1
            while Star.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1

            self.slug = slug

        super().save(*args, **kwargs)

class Star(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя знаменитости")  # Имя звезды
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name="URL")
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='stars', verbose_name="Связанные страны")
    categories = models.ManyToManyField(Category, related_name='stars', verbose_name="Виды деятельности")
    birth_date = models.DateField(verbose_name = "День рождения")  # Дата рождения
    content = models.TextField(verbose_name = "Биография")  # Описание звезды
    photo = models.ImageField(upload_to='photos/%Y/%m/%d/', blank=True, null=True, verbose_name="Фотография")

    is_published = models.BooleanField(default=True)  # Флаг публикации
    time_create = models.DateTimeField(auto_now_add=True)  # Дата создания (автоматически)
    time_update = models.DateTimeField(auto_now=True)  # Дата обновления (автоматически)

    def __str__(self):
        return self.name

    def get_age(self):
        """Вычисляет возраст звезды на основе даты рождения."""
        today = date.today()
        age = today.year - self.birth_date.year
        # Если день рождения еще не наступил в этом году, вычитаем один год
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            age -= 1
        return age

    def save(self, *args, **kwargs):
        if not self.slug:
            # Транслитерация имени с русского на английский
            translit_name = translit(self.name, 'ru', reversed=True)
            # Приведение к нижнему регистру и замена пробелов на дефисы
            base_slug = slugify(translit_name)

            # Проверка уникальности slug
            slug = base_slug
            n = 1
            while Star.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1

            self.slug = slug

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Знаменитость'
        verbose_name_plural = 'Знаменитости'
        ordering = ['-time_create']  # Сортировка по убыванию времени создания
        indexes = [
            models.Index(fields=['-time_create']),  # Индекс для повышения производительности
        ]

