# Generated by Django 4.2.19 on 2025-03-04 11:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('star', '0004_category_slug_country_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True, verbose_name='URL'),
        ),
        migrations.AlterField(
            model_name='country',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True, verbose_name='URL'),
        ),
    ]
