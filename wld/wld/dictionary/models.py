"""Models for the wld records.

The wld is the "Dictionary of Limburg Dialects".
Each wld entry has a gloss, a definition and a number of variants in different dialects.
The dialects are identified by locations, and the locations are indicated by a Kloeke code.

"""
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

MAX_IDENTIFIER_LEN = 10
MAX_LEMMA_LEN = 50



class FieldChoice(models.Model):

    field = models.CharField(max_length=50)
    english_name = models.CharField(max_length=50)
    dutch_name = models.CharField(max_length=50)
    machine_value = models.IntegerField(help_text="The actual numeric value stored in the database. Created automatically.")

    def __str__(self):
        return "{}: {}, {} ({})".format(
            self.field, self.english_name, self.dutch_name, str(self.machine_value))

    class Meta:
        ordering = ['field','machine_value']


def build_choice_list(field):
    """Create a list of choice-tuples"""

    choice_list = [];

    try:
        # check if there are any options at all
        if FieldChoice.objects == None:
            # Take a default list
            choice_list = [('0','-'),('1','N/A')]
        else:
            for choice in FieldChoice.objects.filter(field__iexact=field):
                choice_list.append((str(choice.machine_value),choice.english_name));

            choice_list = sorted(choice_list,key=lambda x: x[1]);
    except:
        choice_list = [('0','-'),('1','N/A')];

    # Signbank returns: [('0','-'),('1','N/A')] + choice_list
    # We do not use defaults
    return choice_list;

def choice_english(field, num):
    """Get the english name of the field with the indicated machine_number"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(machine_value=num)
        if (result_list == None):
            return "(No results for "+field+" with number="+num
        return result_list[0].english_name
    except:
        return "(empty)"

def m2m_combi(items):
    if items == None:
        sBack = ''
    else:
        qs = items.all()
        sBack = '-'.join([str(thing) for thing in qs])
    return sBack

def m2m_identifier(items):
    if items == None:
        sBack = ''
    else:
        qs = items.all()
        sBack = "-".join([thing.identifier for thing in qs])
    return sBack

def get_ident(qs):
    if qs == None:
        idt = ""
    else:
        lst = qs.all()
        if len(lst) == 0:
            idt = "(empty)"
        else:
            qs = lst[0].entry_set
            idt = m2m_identifier(qs)
    return idt

  

class HelpChoice(models.Model):
    """Define the URL to link to for the help-text"""
    
    field = models.CharField(max_length=200)        # The 'path' to and including the actual field
    searchable = models.BooleanField(default=False) # Whether this field is searchable or not
    display_name = models.CharField(max_length=50)  # Name between the <a></a> tags
    help_url = models.URLField(default='')          # THe actual help url (if any)

    def __str__(self):
        return "[{}]: {}".format(
            self.field, self.display_name)

    def Text(self):
        help_text = ''
        # is anything available??
        if (self.help_url != ''):
            if self.help_url[:4] == 'http':
                help_text = "See: <a href='{}'>{}</a>".format(
                    self.help_url, self.display_name)
            else:
                help_text = "{} ({})".format(
                    self.display_name, self.help_url)
        return help_text


def get_help(field):
    """Create the 'help_text' for this element"""

    # find the correct instance in the database
    help_text = ""
    try:
        entry_list = HelpChoice.objects.filter(field__iexact=field)
        entry = entry_list[0]
        # Note: only take the first actual instance!!
        help_text = entry.Text()
    except:
        help_text = "Sorry, no help available for " + field

    return help_text

class Lemma(models.Model):
    """Lemma"""

    gloss = models.CharField("Gloss voor dit lemma", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Omschrijving van het lemma", blank=True)
    bronnenlijst = models.TextField("Bronnenlijst bij dit lemma", blank=True)

    def __str__(self):
        return self.gloss


class Dialect(models.Model):
    """Dialect"""

    stad = models.CharField("Stad van dialect", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    code = models.CharField("Plaatscode (Kloeke)", blank=False, max_length=6, default="xxxxxx")
    nieuw = models.CharField("Plaatscode (New Kloeke)", blank=False, max_length=6, default="xxxxxx")
    toelichting = models.TextField("Toelichting bij dialect", blank=True)

    def __str__(self):
        return self.stad


class Trefwoord(models.Model):
    """Trefwoord"""

    woord = models.CharField("Trefwoord", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Toelichting bij trefwoord", blank=True)

    def __str__(self):
        return self.woord


class Aflevering(models.Model):
    """Aflevering van een woordenboek"""

    naam = models.CharField("Aflevering", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Toelichting bij aflevering", blank=True)

    def __str__(self):
        return self.naam


class Mijn(models.Model):
    """De mijn waar de sprekers werken"""

    naam = models.CharField("Mijn", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    locatie = models.CharField("Locatie", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Toelichting bij mijn", blank=True)

    def __str__(self):
        return self.naam


class Entry(models.Model):
    """Dictionary entry"""

    class Meta:
        verbose_name_plural = "Entries"
        ordering = ['lemma', 'woord']
        permissions = ( ('search_gloss', 'Can search/view/edit full entry details'),
                       )

    def __str__(self):
        return self.woord + '_' + self.dialect.code

    # Lemma: obligatory
    lemma = models.ForeignKey(Lemma, blank=False)
    # Dialect: obligatory
    dialect = models.ForeignKey(Dialect, blank=False)
    # Trefwoord: obligatory
    trefwoord = models.ForeignKey(Trefwoord, blank=False)
    # Mijn [0-1]
    mijn = models.ForeignKey(Mijn, blank = True)
    # Aflevering [1]
    aflevering = models.ForeignKey(Aflevering, blank=False)
    # Dialectal entry: obligatory
    woord = models.CharField("Dialectopgave", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Notes to this entry: optional
    toelichting = models.TextField("Toelichting", blank=True)

    def get_trefwoord_woord(self):
        return self.trefwoord.woord + '_' + self.woord

    def get_lemma_gloss(self):
        return self.lemma.gloss + '_' + self.woord
