from django.contrib import admin
from .models import Star, Country, Category, FeedbackMessage


class StarAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_date', 'get_countries', 'get_categories', 'is_published')
    list_filter = ('is_published', 'categories', 'countries')
    search_fields = ('name',)
    list_editable = ('is_published',)

    def get_countries(self, obj):
        return ", ".join([country.name for country in obj.countries.all()])

    get_countries.short_description = 'Страны'

    def get_categories(self, obj):
        return ", ".join([category.title for category in obj.categories.all()])

    get_categories.short_description = 'Категории'


admin.site.register(Star, StarAdmin)
admin.site.register(Country)
admin.site.register(Category)

class FeedbackMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'topic', 'created_at')
    list_filter = ('topic', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('name', 'email', 'topic', 'message', 'created_at')

admin.site.register(FeedbackMessage, FeedbackMessageAdmin)