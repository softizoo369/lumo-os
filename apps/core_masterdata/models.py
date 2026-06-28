from django.db import models
from apps.saas_core.models.base import LumoBaseModel

class Country(LumoBaseModel):
    name = models.CharField(max_length=100, unique=True)
    iso2_code = models.CharField(max_length=2, unique=True, help_text="e.g., BD, US")
    dial_code = models.CharField(max_length=10, help_text="e.g., +880, +1")

    class Meta:
        db_table = 'master_country'
        ordering = ['name']

    def __str__(self):
        return self.name

class Currency(LumoBaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=3, unique=True, help_text="e.g., BDT, USD")
    symbol = models.CharField(max_length=10, help_text="e.g., ৳, $")

    class Meta:
        db_table = 'master_currency'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} ({self.symbol})"

class Language(LumoBaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True, help_text="e.g., en, bn")

    class Meta:
        db_table = 'master_language'
        ordering = ['name']

    def __str__(self):
        return self.name

class Timezone(LumoBaseModel):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., Asia/Dhaka")

    class Meta:
        db_table = 'master_timezone'
        ordering = ['name']

    def __str__(self):
        return self.name

class Industry(LumoBaseModel):
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'master_industry'
        ordering = ['name']

    def __str__(self):
        return self.name