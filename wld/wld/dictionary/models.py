"""Models for the wld records.

The wld is the "Dictionary of Limburg Dialects".
Each wld entry has a gloss, a definition and a number of variants in different dialects.
The dialects are identified by locations, and the locations are indicated by a 'Kloekecode'.

"""
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from wld.settings import APP_PREFIX
import codecs
import html
                


MAX_IDENTIFIER_LEN = 10
MAX_LEMMA_LEN = 100



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

def int_to_roman(input):
   """Convert an integer to Roman numerals."""
   ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
   nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
   result = ""
   for i in range(len(ints)):
      count = int(input / ints[i])
      result += nums[i] * count
      input -= ints[i] * count
   return result

def handle_uploaded_csv(fPath, iDeel, iSectie, iAflevering):
    """Process a CSV with entry definitions"""

    # Open it with the appropriate codec
    f = codecs.open(fPath, "r", encoding='utf-8-sig')
    bEnd = False
    bFirst = True
    while (not bEnd):
        # Read one line
        strLine = f.readline()
        if (strLine == ""):
            break
        strLine = str(strLine)
        strLine = strLine.strip(" \n\r")
        # Only process substantial lines
        if (strLine != ""):
            # Split the line into parts
            arPart = strLine.split('\t')
            # IF this is the first line or an empty line, then skip
            if bFirst:
                # Check if the line starts correctly
                if arPart[0] != 'Lemmanummer':
                    # The first line does not start correctly -- return false
                    return False
                # Indicate that the first item has been had
                bFirst = False
            else:
                # Assuming this is entering an ENTRY
                # Fields overview:
                #  0 Lemmanummer        -   
                #  1 Lemmatitel         - lemma.gloss
                #  2 Vraag(tekst)       -
                #  3 Trefwoord          - trefwoord.woord
                #  4 Lexicale variant   - 
                #  5 Fonetische variant - entry.woord
                #  6 Vragenlijst        - lemma.bronnenlijst
                #  7 Vraagnummer        - 
                #  8 Boek               - lemma.bronnenlijst
                #  9 Boekpagina         -
                # 10 Plaatsnaam         - dialect.stad
                # 11 Regio              -
                # 12 Subregio           -
                # 13 Informantencode    -
                # 14 Commentaar         - entry.toelichting
                # 15 Plaatscode (Kloeke)- dialect.nieuw

                # Find out which lemma this is
                iPkLemma = Lemma.get_item({'gloss': arPart[1], 
                                           'bronnenlijst': arPart[6], 
                                           'boek': arPart[7]})

                # Find out which dialect this is
                iPkDialect = Dialect.get_item({'stad': arPart[10], 
                                               'nieuw': arPart[15]})

                # Find out which trefwoord this is
                iPkTrefwoord = Trefwoord.get_item({'woord': arPart[3]})

                # Get an entry to aflevering
                iPkAflevering = Aflevering.get_item({'deel': iDeel, 
                                                     'sectie': iSectie, 
                                                     'aflnum': iAflevering})

                # Process this entry
                sDialectWoord = arPart[5]
                sDialectWoord = html.unescape(sDialectWoord).strip('"')
                iPkEntry = Entry.get_item({'woord': sDialectWoord, 
                                           'toelichting': arPart[14], 
                                           'lemma': iPkLemma, 
                                           'dialect': iPkDialect, 
                                           'trefwoord': iPkTrefwoord,
                                           'aflevering': iPkAflevering})

    # CLose the input file
    f.close()

    # return correctly
    return True
  

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
    boek = models.TextField("Boekaanduiding", blank=True)

    def __str__(self):
        return self.gloss

    def get_item(self):
        # Get the parameters
        gloss = self['gloss']
        bronnenlijst = self['bronnenlijst']
        boek = self['boek']
        # Try find an existing item
        qs = Lemma.objects.filter(gloss__iexact=gloss, bronnenlijst__iexact=bronnenlijst, boek__iexact=boek)
        # see if we get one unique value back
        iLen = len(qs)
        if iLen == 0:
            # add a new Dialect object
            lemma = Lemma(gloss=gloss, bronnenlijst=bronnenlijst, boek=boek)
            lemma.save()
            iPk = lemma.pk
        else:
            # Get the pk of the first hit
            iPk = qs[0].pk

        # Return the result
        return iPk



class Dialect(models.Model):
    """Dialect"""

    class Meta:
        verbose_name_plural = "Dialecten"

    stad = models.CharField("Dialectlocatie", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    code = models.CharField("Plaatscode (Kloeke)", blank=False, max_length=6, default="xxxxxx")
    nieuw = models.CharField("Plaatscode (Nieuwe Kloeke)", blank=False, max_length=6, default="xxxxxx")
    toelichting = models.TextField("Toelichting bij dialect", blank=True)

    def __str__(self):
        return self.nieuw

    def get_item(self):
        # Get the parameters
        stad = self['stad']
        nieuw = self['nieuw']
        # Try find an existing item
        qs = Dialect.objects.filter(stad__iexact=stad, nieuw__iexact=nieuw)
        # see if we get one unique value back
        iLen = len(qs)
        if iLen == 0:
            # add a new Dialect object
            dialect = Dialect(stad=stad, nieuw=nieuw, code='-')
            dialect.save()
            iPk = dialect.pk
        else:
            # Get the pk of the first hit
            iPk = qs[0].pk

        # Return the result
        return iPk


class Trefwoord(models.Model):
    """Trefwoord"""

    class Meta:
        verbose_name_plural = "Trefwoorden"

    woord = models.CharField("Trefwoord", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Toelichting bij trefwoord", blank=True)

    def __str__(self):
        return self.woord

    def get_item(self):
        toelichting = None
        # Get the parameters
        woord = self['woord']
        # Try find an existing item
        qs = Trefwoord.objects.filter(woord__iexact=woord)
        if 'toelichting' in self:
            toelichting = self['toelichting']
            # Try find an existing item
            qs = qs.filter(toelichting__iexact = toelichting)
        # see if we get one unique value back
        iLen = len(qs)
        if iLen == 0:
            # add a new Dialect object
            trefwoord = Trefwoord(woord=woord)
            if toelichting != None:
                trefwoord.toelichting = toelichting
            trefwoord.save()
            iPk = trefwoord.pk
        else:
            # Get the pk of the first hit
            iPk = qs[0].pk

        # Return the result
        return iPk


class Deel(models.Model):
    """Deel van de woordenboekencollectie"""

    class Meta:
        verbose_name_plural = "Delen"

    # Titel van dit deel
    titel = models.CharField("Volledige titel", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Nummer van dit deel
    nummer = models.IntegerField("Nummer", blank=False, default=0)
    # Allow for comments for this 'deel'
    toelichting = models.TextField("Toelichting bij dit deel", blank=True)

    def __str__(self):
        return self.titel

    def romeins(self):
        return int_to_roman(self.nummer)


class Info(models.Model):
    """Informatiebestand (csv)"""

    # Nummer van het deel (I, II, III)
    deel = models.IntegerField("Deel", blank=False, default=0)
    # Nummer van de sectie (indien van toepassing -- subcategorie voor deel 3)
    sectie = models.IntegerField("Sectie (optioneel)", blank=True, null=True)
    # Nummer van de aflevering
    aflnum = models.IntegerField("Aflevering", blank=False, default=0)
    # Whether/when processed
    processed = models.CharField("Verwerkt", blank=True, max_length=MAX_LEMMA_LEN)
    # Het bestand dat ge-upload wordt
    csv_file = models.FileField(upload_to="csv_files/")

    def save(self, *args, **kwargs):
        # Standard treatment: first save it
        super(Info, self).save(*args, **kwargs)
        # Has it been processed already?
        if self.processed == None or self.processed == "":
            # Process the file
            bResult = handle_uploaded_csv(self.csv_file.path, self.deel, self.sectie, self.aflnum)
            # Do we have success?
            if bResult:
                # Show it is processed
                self.processed =  datetime.now().strftime("%d/%B/%Y - %H:%M:%S")
                # Save the revised information
                super(Info, self).save(*args, **kwargs)


class Aflevering(models.Model):
    """Aflevering van een woordenboek"""

    class Meta:
        verbose_name_plural = "Afleveringen"

    # The 'naam' is the full name of the PDF (without path) in which information is stored
    naam = models.CharField("PDF naam", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # The 'deel' is the main category of the books
    deel = models.ForeignKey(Deel, blank=False)
    # The 'sectie' is a sub-category used for instance in deel 3
    sectie = models.IntegerField("Sectie (optioneel)", blank=True, null=True)
    # The 'aflnum' is the actual number of the aflevering 
    aflnum = models.IntegerField("Aflevering", blank=False, default=0)
    # A field that indicates this item also has an Inleiding
    inleiding = models.BooleanField("Heeft inleiding", blank=False, default=False)
    # The year of publication of the book
    jaar = models.IntegerField("Jaar van publicatie", blank=False, default=1900)
    # The authors for this book
    auteurs = models.CharField("Auteurs", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # The title of this aflevering
    afltitel = models.CharField("Boektitel", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # The title of this sectie
    sectietitel = models.CharField("Sectietitel", blank=True, max_length=MAX_LEMMA_LEN, default="")
    # The place(s) of publication
    plaats = models.CharField("Plaats van publicatie", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Any additional information
    toelichting = models.TextField("Toelichting bij aflevering", blank=True)

    def __str__(self):
        return self.naam

    def get_number(self):
        if self.sectie == None:
            iNumber = self.aflnum
        else:
            iNumber = self.sectie * 10 + self.aflnum
        return iNumber

    def get_pdf(self):
        # sPdf =  "{}/static/dictionary/content/pdf{}/{}".format(APP_PREFIX, self.deel.nummer,self.naam)
        sPdf =  "wld-{}/{}".format(self.deel.nummer,self.naam)
        return sPdf

    def get_item(self):
        # Get the parameters
        deel = self['deel']
        sectie = self['sectie']
        aflnum = self['aflnum']
        # Try find an existing item
        qs = Aflevering.objects.filter(deel__nummer__iexact=deel, aflnum__iexact=aflnum)
        if sectie != None:
            qs = qs.filter(sectie__iexact = sectie)
        # see if we get one unique value back
        iLen = len(qs)
        if iLen == 0:
            # We cannot add a new item
            iPk = -1
        else:
            # Get the pk of the first hit
            iPk = qs[0].pk

        # Return the result
        return iPk



class Mijn(models.Model):
    """De mijn waar de sprekers werken"""

    class Meta:
        verbose_name_plural = "Mijnen"

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
    mijn = models.ForeignKey(Mijn, blank = True, null=True)
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

    def get_row(self):
        arRow = []
        arRow.append(self.lemma.gloss)
        arRow.append(self.trefwoord.woord)
        arRow.append(self.woord)
        arRow.append(self.dialect.nieuw)
        arRow.append(self.aflevering.naam)
        return arRow

    def get_tsv(self):
        return self.lemma.gloss + '\t' + self.trefwoord.woord + '\t' + self.woord + '\t' + self.dialect.nieuw + '\t' + self.aflevering.naam

    def get_item(self):
        mijnPk = None

        # Get the parameters out of [self]
        woord = self['woord']
        toelichting = self['toelichting']
        lemmaPk = self['lemma']
        dialectPk = self['dialect']
        trefwoordPk = self['trefwoord']
        afleveringPk = self['aflevering']
        if 'mijn' in self:
            mijnPk = self['mijn']

        # Try find an existing item
        qs = Entry.objects.filter(woord__iexact=woord, 
                                  toelichting__iexact=toelichting,
                                  lemma__pk=lemmaPk,
                                  dialect__pk = dialectPk,
                                  trefwoord__pk = trefwoordPk,
                                  aflevering__pk = afleveringPk,
                                  mijn__pk = mijnPk)
        # see if we get one unique value back
        iLen = len(qs)
        if iLen == 0:
            # Get the objects from the pk's
            lemma      = Lemma.objects.get(pk=lemmaPk)
            dialect    = Dialect.objects.get(pk=dialectPk)
            trefwoord  = Trefwoord.objects.get(pk=trefwoordPk)
            aflevering = Aflevering.objects.get(pk=afleveringPk)
            if mijnPk != None:
                mijn = Mijn.objects.get(pk=mijnPk)
                # add a new Dialect object
                entry = Entry(woord=woord, toelichting = toelichting, lemma=lemma,
                              dialect = dialect, trefwoord = trefwoord,
                              aflevering = aflevering, mijn = mijn)
            else:
                # add a new Dialect object
                entry = Entry(woord=woord, toelichting = toelichting, lemma=lemma,
                              dialect = dialect, trefwoord = trefwoord,
                              aflevering = aflevering)
            entry.save()
            iPk = entry.pk
        else:
            # Get the pk of the first hit
            iPk = qs[0].pk

        # Return the result
        return iPk



