from modeltranslation.translator import TranslationOptions, register
from base.models import Category

@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('label',)   # add any other field you want translated