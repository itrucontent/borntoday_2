from django import forms
from django.core.exceptions import ValidationError
from .models import Star, Country, Category


class StarForm(forms.ModelForm):
    """Форма для добавления знаменитости"""

    class Meta:
        model = Star
        fields = ['name', 'country', 'categories', 'birth_date', 'death_date',
                  'content', 'photo', 'wikipedia', 'ruwiki']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '3'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'death_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'wikipedia': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Ссылка на статью в Википедии'}),
            'ruwiki': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Ссылка на статью в RuWiki'}),
        }


class ContactForm(forms.Form):
    """Форма обратной связи для страницы О сайте"""
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}), label='Ваше имя')
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}), label='Электронная почта')
    topic = forms.ChoiceField(choices=[
        ('', 'Выберите тему обращения'),
        ('error', 'Сообщить об ошибке'),
        ('suggestion', 'Предложить улучшение'),
        ('cooperation', 'Сотрудничество'),
        ('other', 'Другое'),
    ], widget=forms.Select(attrs={'class': 'form-select'}), label='Тема')
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}), label='Сообщение')
    agreement = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Я согласен с правилами сайта и обработкой персональных данных'
    )