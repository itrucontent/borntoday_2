# Generated by Django 4.2.19 on 2025-03-04 11:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('star', '0003_alter_star_options_star_star_star_time_cr_80a8dd_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, verbose_name='URL'),
        ),
        migrations.AddField(
            model_name='country',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, verbose_name='URL'),
        ),
    ]
