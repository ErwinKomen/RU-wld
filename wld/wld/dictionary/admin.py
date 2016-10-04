from django.contrib import admin
from django import forms
from django.core import serializers
from django.contrib.contenttypes.models import ContentType
from wld.dictionary.models import *
import logging

MAX_IDENTIFIER_LEN = 10
logger = logging.getLogger(__name__)

def remove_from_fieldsets(fieldsets, fields):
    for fieldset in fieldsets:
        for field in fields:
            if field in fieldset[1]['fields']:
                logging.debug("'%s' field found in %s, hiding." % (field, fieldset[1]['fields']))
                newfields = []
                for myfield in fieldset[1]['fields']:
                    if not myfield in fields:
                        newfields.append(myfield)

                fieldset[1]['fields'] = tuple(newfields)
                logger.debug('Setting newfields to: %s' % newfields)

                break

class LemmaAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('gloss', 'toelichting', 'bronnenlijst',)}),
                )


class DialectAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('stad', 'code', 'nieuw', 'toelichting',)}),
                )


class TrefwoordAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('woord', 'toelichting',)}),
                )


class EntryAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('woord', 'lemma', 'dialect', 'trefwoord', 'toelichting',)}),
                )
    list_display = ['woord', 'lemma', 'dialect', 'trefwoord', 'toelichting']
    list_filter = ['lemma', 'dialect']


# -- Components of an entry
admin.site.register(Lemma, LemmaAdmin)
admin.site.register(Dialect, DialectAdmin)
admin.site.register(Trefwoord, TrefwoordAdmin)
admin.site.register(Mijn)
admin.site.register(Aflevering)

# -- dictionary as a whole
admin.site.register(Entry, EntryAdmin)