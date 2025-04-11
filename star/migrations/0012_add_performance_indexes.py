from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('star', '0011_country_name_2'),  # Убедитесь, что это имя вашей последней миграции
    ]

    operations = [
        migrations.AddIndex(
            model_name='star',
            index=models.Index(fields=['is_published'], name='published_idx'),
        ),
        migrations.AddIndex(
            model_name='star',
            index=models.Index(fields=['rating'], name='rating_idx'),
        ),
        migrations.AddIndex(
            model_name='star',
            index=models.Index(fields=['name'], name='name_idx'),
        ),
        migrations.AddIndex(
            model_name='star',
            index=models.Index(fields=['birth_date'], name='birth_date_idx'),
        ),
        migrations.AddIndex(
            model_name='star',
            index=models.Index(fields=['is_published', 'birth_date'], name='published_bday_idx'),
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['title'], name='category_title_idx'),
        ),
        migrations.AddIndex(
            model_name='country',
            index=models.Index(fields=['name'], name='country_name_idx'),
        ),
    ]