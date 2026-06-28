from django.contrib import admin
from .models import Country, Currency, Language, Timezone, Industry

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'iso2_code', 'dial_code')

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'symbol')

@admin.register(Timezone)
class TimezoneAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ('name',)