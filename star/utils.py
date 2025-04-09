class GenitiveCountry:
    """Обертка для объекта Country, которая возвращает name_2 вместо name.
    Делегирует все остальные атрибуты и методы оригинальному объекту."""

    def __init__(self, country):
        self._country = country

        # Копируем все атрибуты из оригинального объекта
        self.id = country.id
        self.slug = country.slug

        # Используем name_2, если оно есть, иначе используем name
        if country.name_2:
            self.name = country.name_2
        else:
            self.name = country.name

    def __str__(self):
        return self.name