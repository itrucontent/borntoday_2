# Generated by Django 4.2.19 on 2025-03-04 09:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('star', '0002_alter_star_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='star',
            options={'ordering': ['-time_create'], 'verbose_name': 'Знаменитость', 'verbose_name_plural': 'Знаменитости'},
        ),
        migrations.AddIndex(
            model_name='star',
            index=models.Index(fields=['-time_create'], name='star_star_time_cr_80a8dd_idx'),
        ),
    ]
