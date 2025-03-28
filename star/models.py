from django.db import models
from datetime import date
from django.utils.text import slugify
from transliterate import translit

class Country(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=255, blank=True, db_index=True, verbose_name="URL", unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            translit_name = translit(self.name, 'ru', reversed=True)
            base_slug = slugify(translit_name)

            slug = base_slug
            n = 1
            while Country.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1

            self.slug = slug

        super().save(*args, **kwargs)

class Category(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=255, blank=True, db_index=True, verbose_name="URL", unique=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            translit_name = translit(self.title, 'ru', reversed=True)
            base_slug = slugify(translit_name)

            slug = base_slug
            n = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1

            self.slug = slug

        super().save(*args, **kwargs)

class Star(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя знаменитости")
    slug = models.SlugField(max_length=255, db_index=True, verbose_name="URL", unique=True)
    countries = models.ManyToManyField(Country, related_name='stars', verbose_name="Связанные страны")
    categories = models.ManyToManyField(Category, related_name='stars', verbose_name="Виды деятельности")
    birth_date = models.DateField(verbose_name="День рождения")
    death_date = models.DateField(verbose_name="Дата смерти", blank=True, null=True)
    content = models.TextField(verbose_name="Биография")
    photo = models.ImageField(upload_to='photos/%Y/%m/%d/', blank=True, null=True, verbose_name="Фотография")
    rating = models.IntegerField(verbose_name="Рейтинг", default=0)
    wikipedia = models.URLField(verbose_name="Ссылка на Wikipedia", blank=True, null=True)
    ruwiki = models.URLField(verbose_name="Ссылка на RuWiki", blank=True, null=True)

    is_published = models.BooleanField(default=True)
    time_create = models.DateTimeField(auto_now_add=True)
    time_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_age(self):
        """Вычисляет возраст звезды на основе даты рождения."""
        if self.death_date:
            # Если человек умер, вычисляем возраст на момент смерти
            age = self.death_date.year - self.birth_date.year
            if (self.death_date.month, self.death_date.day) < (self.birth_date.month, self.birth_date.day):
                age -= 1
            return age
        else:
            # Если жив, вычисляем текущий возраст
            today = date.today()
            age = today.year - self.birth_date.year
            if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
                age -= 1
            return age

    def get_years_range(self):
        """Возвращает годы жизни в формате '1947-2023' или только год рождения."""
        birth_year = self.birth_date.year
        if self.death_date:
            death_year = self.death_date.year
            return f"{birth_year}-{death_year}"
        return str(birth_year)

    def save(self, *args, **kwargs):
        if not self.slug:
            translit_name = translit(self.name, 'ru', reversed=True)
            base_slug = slugify(translit_name)

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
        ordering = ['-time_create']
        indexes = [
            models.Index(fields=['-time_create']),
        ]


class FeedbackMessage(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя")
    email = models.EmailField(verbose_name="Email")
    topic = models.CharField(max_length=20, verbose_name="Тема")
    message = models.TextField(verbose_name="Сообщение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"{self.name} - {self.topic} ({self.created_at.strftime('%d.%m.%Y')})"

    class Meta:
        verbose_name = "Сообщение обратной связи"
        verbose_name_plural = "Сообщения обратной связи"
        ordering = ['-created_at']