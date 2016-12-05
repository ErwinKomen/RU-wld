"""Models for the wld records.

The wld is the "Dictionary of Limburg Dialects".
Each wld entry has a gloss, a definition and a number of variants in different dialects.
The dialects are identified by locations, and the locations are indicated by a 'Kloekecode'.

"""
from django.db import models
from django.contrib.auth.models import User
from django.db import transaction
from datetime import datetime
from wld.settings import APP_PREFIX, MEDIA_ROOT
import os
import sys
import io
import codecs
import html
import json
                


MAX_IDENTIFIER_LEN = 10
MAX_LEMMA_LEN = 100


# ============================= LOCAL CLASSES ======================================
class ErrHandle:
    """Error handling"""

    # ======================= CLASS INITIALIZER ========================================
    def __init__(self):
        # Initialize a local error stack
        self.loc_errStack = []

    # ----------------------------------------------------------------------------------
    # Name :    Status
    # Goal :    Just give a status message
    # History:
    # 6/apr/2016    ERK Created
    # ----------------------------------------------------------------------------------
    def Status(self, msg):
        # Just print the message
        print(msg, file=sys.stderr)

    # ----------------------------------------------------------------------------------
    # Name :    DoError
    # Goal :    Process an error
    # History:
    # 6/apr/2016    ERK Created
    # ----------------------------------------------------------------------------------
    def DoError(self, msg, bExit = False):
        # Append the error message to the stack we have
        self.loc_errStack.append(msg)
        # Print the error message for the user
        print("Error: "+msg+"\nSystem:", file=sys.stderr)
        for nErr in sys.exc_info():
            if (nErr != None):
                print(nErr, file=sys.stderr)
        # Is this a fatal error that requires exiting?
        if (bExit):
            sys.exit(2)

errHandle = ErrHandle()

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
  
def bulk_uploaded_csv(fPath, iDeel, iSectie, iAflevering):
    """Process a CSV with entry definitions in a two-pass method"""

    # Pass 1: read and prepare all the [lemma], [dialect], [trefwoord] and [aflevering] details
    lstLemma = []
    lstDialect = []
    lstTrefwoord = []
    lstAflevering = []

    # Open it with the appropriate codec
    f = codecs.open(fPath, "r", encoding='utf-8-sig')
    bEnd = False
    bFirst = True
    iCounter = 0
    with transaction.atomic():
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
                # Print a counter
                msg = "bulk pass1: " + str(iCounter)
                print(msg, file=sys.stderr)
                iCounter += 1
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
                    #if iPkLemma < 0:
                    #    print("Add lemma {}, {}, {}".format(arPart[1], arPart[6], arPart[7]), file=sys.stderr)
                    #    lstLemma.append(Lemma(gloss=arPart[1], bronnenlijst=arPart[6], boek=arPart[7]))

                    # Find out which dialect this is
                    iPkDialect = Dialect.get_item({'stad': arPart[10], 
                                                   'nieuw': arPart[15]})
                    #if iPkDialect < 0:
                    #    lstDialect.append(Dialect(stad=arPart[10], nieuw=arPart[15]))

                    # Find out which trefwoord this is
                    iPkTrefwoord = Trefwoord.get_item({'woord': arPart[3]})
                    #if iPkTrefwoord < 0:
                    #    lstTrefwoord.append(Trefwoord(woord=arPart[3]))

                    # Get an entry to aflevering
                    iPkAflevering = Aflevering.get_item({'deel': iDeel, 
                                                         'sectie': iSectie, 
                                                         'aflnum': iAflevering})
                    #if iPkAflevering < 0:
                    #    if iSectie == None:
                    #        lstAflevering.append(Aflevering(deel=iDeel, aflnum=iAflevering))
                    #    else:
                    #        lstAflevering.append(Aflevering(deel=iDeel, sectie=iSectie, aflnum=iAflevering))

    # CLose the input file
    f.close()

    # Perform bulk-processing of Lemma, Dialect, Trefwoord and Aflevering
    Lemma.objects.bulk_create(lstLemma)
    Dialect.objects.bulk_create(lstDialect)
    Trefwoord.objects.bulk_create(lstTrefwoord)
    if lstAflevering.count > 0:
        iStop = 1
        Aflevering.objects.bulk_create(lstAflevering)


    # Open it with the appropriate codec
    f = codecs.open(fPath, "r", encoding='utf-8-sig')
    bEnd = False
    bFirst = True
    iCounter = 0
    while (not bEnd):
        # Read one line
        strLine = f.readline()
        if (strLine == ""):
            break
        strLine = str(strLine)
        strLine = strLine.strip(" \n\r")
        # Only process substantial lines
        if (strLine != ""):
            # Print a counter
            msg = "bulk pass2: " + str(iCounter)
            print(msg, file=sys.stderr)
            iCounter += 1
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
                # Find out which lemma this is
                iPkLemma = Lemma.get_pk({'gloss': arPart[1], 
                                           'bronnenlijst': arPart[6], 
                                           'boek': arPart[7]})
                # Find out which dialect this is
                iPkDialect = Dialect.get_pk({'stad': arPart[10], 
                                               'nieuw': arPart[15]})
                # Find out which trefwoord this is
                iPkTrefwoord = Trefwoord.get_pk({'woord': arPart[3]})
                # Get an entry to aflevering
                iPkAflevering = Aflevering.get_pk({'deel': iDeel, 
                                                     'sectie': iSectie, 
                                                     'aflnum': iAflevering})


                # Process this entry
                sDialectWoord = arPart[5]
                sDialectWoord = html.unescape(sDialectWoord).strip('"')
                iPkEntry = Entry.get_pk({'woord': sDialectWoord, 
                                           'toelichting': arPart[14], 
                                           'lemma': iPkLemma, 
                                           'dialect': iPkDialect, 
                                           'trefwoord': iPkTrefwoord,
                                           'aflevering': iPkAflevering})
                if iPkEntry < 0:
                    lstEntry.append(Entry(woord=sDialectWoord, 
                                          toelichting= arPart[14], 
                                          lemma= iPkLemma, 
                                          dialect= iPkDialect, 
                                          trefwoord= iPkTrefwoord,
                                          aflevering= iPkAflevering))

    # CLose the input file
    f.close()

    # Save all the new entries
    Entry.objects.bulk_create(lstEntry)

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


class Description(models.Model):
    """Description for a lemma"""

    toelichting = models.TextField("Omschrijving van het lemma", blank=True)
    bronnenlijst = models.TextField("Bronnenlijst bij het lemma", db_index=True, blank=True)
    boek = models.TextField("Boekaanduiding", db_index=True, null=True,blank=True)

    def __str__(self):
        return self.bronnenlijst

    def get_descr_sort(self):
        return self.toelichting

    def get_pk(self):
        """Check if this Description exists and return a PK"""
        qs = Description.objects.filter(bronnenlijst__iexact=self['bronnenlijst'], 
                                        boek__iexact=self['boek'],
                                        toelichting__iexact=self['toelichting'])
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        # Get the parameters
        bronnenlijst = self['bronnenlijst']
        boek = self['boek']
        toelichting = ""
        if 'toelichting' in self:
            toelichting = self['toelichting']
        # Try find an existing item
        qItem = Description.objects.filter(bronnenlijst__iexact=bronnenlijst, 
                                           boek__iexact=boek,
                                           toelichting__iexact=toelichting).first()
        # see if we get one value back
        if qItem == None:
            # add a new Description object
            descr = Description(bronnenlijst=bronnenlijst, boek=boek, toelichting=toelichting)
            descr.save()
            iPk = descr.pk
        else:
            # Get the pk of the first hit
            iPk = qItem.pk

        # Return the result
        return iPk


class Lemma(models.Model):
    """Lemma"""

    gloss = models.CharField("Gloss voor dit lemma", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # toelichting = models.TextField("Omschrijving van het lemma", blank=True)
    # bronnenlijst = models.TextField("Bronnenlijst bij dit lemma", db_index=True, blank=True)
    # boek = models.TextField("Boekaanduiding", db_index=True, null=True,blank=True)
    lmdescr = models.ManyToManyField(Description, through='LemmaDescr')

    def __str__(self):
        return self.gloss

    def get_pk(self):
        """Check if this lemma exists and return a PK"""
        qs = Lemma.objects.filter(gloss__iexact=self['gloss'])
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        # Get the parameters
        gloss = self['gloss']
        # Try find an existing item
        qItem = Lemma.objects.filter(gloss__iexact=gloss).first()
        # see if we get one value back
        if qItem == None:
            # add a new Dialect object
            lemma = Lemma(gloss=gloss)
            lemma.save()
            iPk = lemma.pk
        else:
            # Get the pk of the first hit
            iPk = qItem.pk

        # Return the result
        return iPk


class LemmaDescr(models.Model):
    """Description belonging to a lemma"""

    lemma=models.ForeignKey(Lemma, on_delete=models.CASCADE)
    description=models.ForeignKey(Description, on_delete=models.CASCADE)


class Dialect(models.Model):
    """Dialect"""

    class Meta:
        verbose_name_plural = "Dialecten"

    stad = models.CharField("Dialectlocatie", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    code = models.CharField("Plaatscode (Kloeke)", blank=False, max_length=6, default="xxxxxx")
    nieuw = models.CharField("Plaatscode (Nieuwe Kloeke)", db_index=True, blank=False, max_length=6, default="xxxxxx")
    toelichting = models.TextField("Toelichting bij dialect", blank=True)

    def __str__(self):
        return self.nieuw

    def get_pk(self):
        """Check if this dialect exists and return a PK"""
        qs = Dialect.objects.filter(stad__iexact=self['stad'], 
                                  nieuw__iexact=self['nieuw']).first()
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        # Get the parameters
        stad = self['stad']
        nieuw = self['nieuw']
        # Try find an existing item
        qItem = Dialect.objects.filter(stad__iexact=stad, nieuw__iexact=nieuw).first()
        # see if we get one value back
        if qItem == None:
            # add a new Dialect object
            dialect = Dialect(stad=stad, nieuw=nieuw, code='-')
            dialect.save()
            iPk = dialect.pk
        else:
            # Get the pk of the first hit
            iPk = qItem.pk

        # Return the result
        return iPk


class Trefwoord(models.Model):
    """Trefwoord"""

    class Meta:
        verbose_name_plural = "Trefwoorden"

    woord = models.CharField("Trefwoord", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Toelichting bij trefwoord", blank=True)

    def __str__(self):
        return self.woord

    def get_pk(self):
        """Check if this dialect exists and return a PK"""
        qs = Trefwoord.objects.filter(woord__iexact=self['woord'])
        if 'toelichting' in self: 
            qs = qs.filter(toelichting__iexact=self['toelichting'])
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        toelichting = None
        # Get the parameters
        woord = self['woord']
        # Try find an existing item
        if 'toelichting' in self:
            toelichting = self['toelichting']
            # Try find an existing item
            qItem = Trefwoord.objects.filter(woord__iexact=woord, toelichting__iexact = toelichting).first()
        else:
            qItem = Trefwoord.objects.filter(woord__iexact=woord).first()
        # see if we get one value back
        if qItem == None:
            # add a new Dialect object
            trefwoord = Trefwoord(woord=woord)
            if toelichting != None:
                trefwoord.toelichting = toelichting
            trefwoord.save()
            iPk = trefwoord.pk
        else:
            # Get the pk of the first hit
            iPk = qItem.pk

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
    # Number of read and skipped lines
    read = models.IntegerField("Gelezen", blank=False, default=0)
    skipped = models.IntegerField("Overgeslagen", blank=False, default=0)
    # Het bestand dat ge-upload wordt
    csv_file = models.FileField(upload_to="csv_files/")

    def save(self, *args, **kwargs):
        # Standard treatment: first save it
        super(Info, self).save(*args, **kwargs)
        # Has it been processed already?
        if self.processed == None or self.processed == "":
            # Process the file
            # bResult = handle_uploaded_csv(self.csv_file.path, self.deel, self.sectie, self.aflnum)
            oResult = csv_to_fixture(self.csv_file.path, self.deel, self.sectie, self.aflnum)
            # Do we have success?
            if oResult['result']:
                # Show it is processed
                self.processed =  datetime.now().strftime("%d/%B/%Y - %H:%M:%S")
                # Show how much has been read
                self.read = oResult['read']
                self.skipped = oResult['skipped']
                # Save the revised information
                super(Info, self).save(*args, **kwargs)


class Aflevering(models.Model):
    """Aflevering van een woordenboek"""

    class Meta:
        verbose_name_plural = "Afleveringen"

    # The 'naam' is the full name of the PDF (without path) in which information is stored
    naam = models.CharField("PDF naam", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # The 'deel' is the main category of the books
    deel = models.ForeignKey(Deel, db_index=True, blank=False)
    # The 'sectie' is a sub-category used for instance in deel 3
    sectie = models.IntegerField("Sectie (optioneel)", db_index=True, blank=True, null=True)
    # The 'aflnum' is the actual number of the aflevering 
    aflnum = models.IntegerField("Aflevering", db_index=True, blank=False, default=0)
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

    def get_pk(self):
        """Check if this aflevering exists and return a PK"""
        qs = Aflevering.objects.filter(deel__nummer__iexact=self['deel'], 
                                  aflnum__iexact = self['aflnum'])
        if self['sectie'] != None:
            qs = qs.filter(sectie__iexact = self['sectie'])

        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        # Get the parameters
        deel = self['deel']
        sectie = self['sectie']
        aflnum = self['aflnum']
        # Try find an existing item
        if sectie == None:
            qItem = Aflevering.objects.filter(deel__nummer__iexact=deel, 
                                           aflnum__iexact=aflnum).first()
        else:
            qItem = Aflevering.objects.filter(deel__nummer__iexact=deel, 
                                           aflnum__iexact=aflnum,
                                           sectie__iexact = sectie).first()
        # see if we get one value back
        if qItem == None:
            # We cannot add a new item
            iPk = -1
        else:
            # Get the pk of the first hit
            iPk = qItem.pk

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

    def get_pk(self):
        """Check if this [mijn] exists and return a PK"""
        qs = Mijn.objects.filter(naam__iexact=self['naam'])
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk




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
    lemma = models.ForeignKey(Lemma, db_index=True, blank=False)
    # Dialect: obligatory
    dialect = models.ForeignKey(Dialect, db_index=True, blank=False)
    # Trefwoord: obligatory
    trefwoord = models.ForeignKey(Trefwoord, db_index=True, blank=False)
    # Mijn [0-1]
    mijn = models.ForeignKey(Mijn, blank = True, null=True)
    # Aflevering [1]
    aflevering = models.ForeignKey(Aflevering, db_index=True, blank=False)
    # Dialectal entry: obligatory
    woord = models.CharField("Dialectopgave", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Notes to this entry: optional
    toelichting = models.TextField("Toelichting", db_index=True, blank=True)

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

    def get_pk(self):
        """Check if this [entry] exists and return a PK"""
        qs = Entry.objects.filter(woord__iexact=self['woord'], 
                                  toelichting__iexact=self['toelichting'],
                                  lemma__pk=self['lemma'],
                                  dialect__pk = self['dialect'],
                                  trefwoord__pk = self['trefwoord'],
                                  aflevering__pk = self['aflevering'])
        if 'mijn' in self:
            qs = qs.filter(mijn__pk = self['naam'])

        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

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


# ============================= Fixture Database Classes ===========================
class FixSkip:
    """Fixture skips"""

    bFirst = True
    fl_out = None

    def __init__(self, output_file):
        # Clear the output file, replacing it with a list starter
        self.fl_out = io.open(output_file, "w", encoding='utf-8')
        self.fl_out.write("")
        self.fl_out.close()
        # Make sure we keep the output file name
        self.output_file = output_file
        # Open the file for appending
        self.fl_out = io.open(output_file, "a", encoding='utf-8')

    def append(self, sLine):
        # Add a newline
        sLine += "\n"
        # Add the object         
        self.fl_out.writelines(sLine)

    def close(self):
        # Close the output file
        self.fl_out.close()



class FixOut:
    """Fixture output"""

    bFirst = True      # Indicates that the first output string has been written
    fl_out = None      # Output file

    def __init__(self, output_file):
        # Clear the output file, replacing it with a list starter
        self.fl_out = io.open(output_file, "w", encoding='utf-8')
        self.fl_out.write("[")
        self.fl_out.close()
        # Make sure we keep the output file name
        self.output_file = output_file
        # Open the file for appending
        self.fl_out = io.open(output_file, "a", encoding='utf-8')

    def append(self, sModel, iPk, **oFields):
        # Possibly add comma
        self.do_comma()
        # Create entry object
        oEntry = {"model": sModel, 
                  "pk": iPk, "fields": oFields}
        # Add the object         
        self.fl_out.writelines(json.dumps(oEntry, indent=2))

    def do_comma(self):
        # Is this the first output?
        if self.bFirst:
            self.bFirst = False
        else:
            self.fl_out.writelines(",")

    def close(self):
        # Append the final [
        self.fl_out.writelines("]")
        # Close the output file
        self.fl_out.close()

    def findItem(self, arItem, **oFields):
        try:
            # Sanity check
            if len(arItem) == 0:
                return -1
            # Check all the items given
            for it in arItem:
                # Assume we are okay
                bFound = True
                # Look through all the (k,v) pairs of [oFields]
                for (k,v) in oFields.items():
                    try:
                        if k in oFields and getattr(it, k) != v:
                            bFound = False
                            break
                    except:
                        # No need to stop here
                        a = 1
                if bFound:
                    return getattr(it, 'pk')
    
            # getting here means we haven't found it
            return -1
        except:
            errHandle.DoError("FixOut/findItem", True)



    def get_pk(self, oCls, sModel, bSearch, **oFields):
        try:
            iPkItem = -1
            # Look for this item in the list that we have
            if bSearch:
                iPkItem = self.findItem(oCls.lstItem, **oFields)
            if iPkItem < 0:
                # it is not in the list: add it
                iPkItem = len(oCls.lstItem)+1
                newItem = fElement(iPkItem, **oFields)
                oCls.lstItem.append(newItem)
                # Add the item to the output
                self.append(sModel, iPkItem, **oFields)

            # Return the pK
            return iPkItem
        except:
            errHandle.DoError("FixOut/get_pk", True)
    

class fElement:

    def __init__(self, iPk, **kwargs):
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        self.pk = iPk


class fLemma:
    """Lemma information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known lemma's

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, gloss=item.gloss))
                self.pk = item.pk


class fDescr:
    """Description information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known lemma's

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, 
                                             bronnenlijst=item.bronnenlijst, 
                                             toelichting=item.toelichting, 
                                             boek=item.boek))
                self.pk = item.pk


class fLemmaDescr:
    """Connection between lemma and description information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known lemma's

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, lemma=item.lemma, description=item.description))
                self.pk = item.pk


class fDialect:
    """Dialect information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                added = fElement(item.pk, stad=item.stad, nieuw=item.nieuw)
                self.lstItem.append(added)
                self.pk = item.pk


class fTrefwoord:
    """Trefwoord information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, woord=item.woord))
                self.pk = item.pk


class fAflevering:
    """Aflevering information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def load(self, qs):
        try:
            if qs:
                for item in qs:
                    # Add this item to the list we have
                    if item.sectie != None:
                        try:
                            added = fElement(item.pk, deel=item.deel, sectie=item.sectie,aflnum=item.aflnum)
                        except:
                            a = 1
                    else:
                        try:
                            added = fElement(item.pk, deel=item.deel, aflnum=item.aflnum)
                        except:
                            a = 1
                    self.lstItem.append(added)
                    self.pk = item.pk
        except:
            errHandle.DoError("fAflevering", True)


class fEntry:
    """Entry information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, woord=item.woord, 
                                      toelichting=item.toelichting, 
                                      lemma=item.lemma, 
                                      dialect=item.dialect, 
                                      trefwoord=item.trefwoord, 
                                      aflevering=item.aflevering))
                self.pk = item.pk


# ----------------------------------------------------------------------------------
# Name :    csv_to_fixture
# Goal :    Convert CSV file into a fixtures file
# History:
#  1/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def csv_to_fixture(csv_file, iDeel, iSectie, iAflevering, bUseDbase=False, bUseOld=False):
    """Process a CSV with entry definitions"""

    oBack = {}      # What we return

    try:
        oBack['result'] = False
        # Validate: input file exists
        if (not os.path.isfile(csv_file)): return oBack

        # Start creating an array that will hold the fixture elements
        arFixture = []
        iPkLemma = 1        # The PK for each Lemma
        iPkDescr = 1        # The PK for each Description (lemma-toelichting many-to-many)
        iPkTrefwoord = 1    # The PK for each Trefwoord
        iPkDialect = 1      # The PK for each Dialect
        iPkEntry = 1        # The PK for each Entry
        iPkAflevering = 1   # The PK for each Aflevering
        iCounter = 0        # Loop counter for progress
        iRead = 0           # Number read correctly
        iSkipped = 0        # Number skipped

        # Create an output file writer
        # Basename: derive from filename
        # sBaseName = os.path.splitext(os.path.basename(csv_file))[0]
        # Basename: derive from deel/section/aflevering
        sBaseName = "fixture-d" + str(iDeel)
        if iSectie != None: sBaseName = sBaseName + "-s" + str(iSectie)
        sBaseName = sBaseName + "-a" + str(iAflevering)
        output_file = os.path.join(MEDIA_ROOT ,sBaseName + ".json")
        skip_file = os.path.join(MEDIA_ROOT, sBaseName + ".skip")
        oFix = FixOut(output_file)
        oSkip = FixSkip(skip_file)

        # Create instances of the Lemma, Dialect and other classes
        oLemma = fLemma()
        oDescr = fDescr()
        oLemmaDescr = fLemmaDescr()
        oDialect = fDialect()
        oTrefwoord = fTrefwoord()
        oAflevering = fAflevering()
        oEntry = fEntry()

        # Initialise the lists in these instances (where needed)
        oDialect.load(Dialect.objects.all())
        oAflevering.load(Aflevering.objects.all())
        if bUseOld:
            oLemma.load(Lemma.objects.all())
            oTrefwoord.load(Trefwoord.objects.all())
            oEntry.load(Entry.objects.all())
        else:
            # Remove the existing objects from Lemma, Trefwoord and Entry
            Lemma.objects.all().delete()
            Trefwoord.objects.all().delete()
            Entry.objects.all().delete()

        # Open source file to read line-by-line
        f = codecs.open(csv_file, "r", encoding='utf-8-sig')
        bEnd = False
        bFirst = True
        bFirstOut = False
        while (not bEnd):
            # Show where we are
            iCounter +=1
            if iCounter % 1000 == 0:
                errHandle.Status("Processing: " + str(iCounter))
            # Read one line
            strLine = f.readline()
            if (strLine == ""):
                bEnd = True
                break
            strLine = str(strLine)
            strLine = strLine.strip(" \n\r")
            # Only process substantial lines
            if (strLine != ""):
                # Split the line into parts
                arPart = strLine.split('\t')
                # Check if this line contains 'valid' data:
                #  1 = lemma
                #  3 = trefwoord
                #  5 = Dialectwoord (fonetische variant)
                # 10 = Dialect city name
                # 15 = Kloeke code
                iValid = isNullOrEmptyOrInt(arPart, [1, 3, 5, 10, 15])
                # IF this is the first line or an empty line, then skip
                if bFirst:
                    # Check if the line starts correctly
                    if arPart[0] != 'Lemmanummer':
                        # The first line does not start correctly -- return false
                        return oBack
                    # Indicate that the first item has been had
                    bFirst = False
                elif iValid == 0:
                    # Assuming this 'part' is entering an ENTRY

                    if bUseDbase:
                        # Find out which lemma this is
                        iPkLemma = Lemma.get_item({'gloss': arPart[1]})

                        # Find out which lemma-description this is
                        iPkDescr = Description.get_item({'bronnenlijst': arPart[6],
                                                         'toelichting': arPart[2], 
                                                         'boek': arPart[7]})

                        # TODO: add the [iPkDescr] to the Lemma--but only if it is not already there

                        # Find out which dialect this is
                        iPkDialect = Dialect.get_item({'stad': arPart[10], 
                                                        'nieuw': arPart[15]})

                        # Find out which trefwoord this is
                        iPkTrefwoord = Trefwoord.get_item({'woord': arPart[3]})

                        # Get an entry to aflevering
                        iPkAflevering = Aflevering.get_item({'deel': iDeel, 
                                                             'sectie': iSectie, 
                                                             'aflnum': iAflevering})
                    else:
                        # Adapt any part-elements that need this
                        for idx in [2,6,7,14]:
                            if arPart[idx] == "NULL":
                                arPart[idx] = ""

                        # Get a lemma number from this
                        # NOTE: assume 2 = toelichting 
                        iPkLemma = oFix.get_pk(oLemma, "dictionary.lemma", True,
                                               gloss=arPart[1])

                        # Get a description number
                        iPkDescr = oFix.get_pk(oDescr, "dictionary.description", True,
                                               bronnenlijst=arPart[6], 
                                               toelichting=arPart[2], 
                                               boek=arPart[7])

                        # Add the Lemma-Description connection
                        iPkLemmaDescr = oFix.get_pk(oLemmaDescr, "dictionary.lemmadescr", True,
                                                    lemma=iPkLemma,
                                                    description=iPkDescr)


                        # get a dialect number
                        iPkDialect = oFix.get_pk(oDialect, "dictionary.dialect", True,
                                                 stad=arPart[10], 
                                                 nieuw=arPart[15])

                        # get a trefwoord number
                        sTrefWoord = arPart[3]
                        sTrefWoord = html.unescape(sTrefWoord).strip('"')
                        iPkTrefwoord = oFix.get_pk(oTrefwoord, "dictionary.trefwoord", True,
                                                   woord=sTrefWoord)

                        # get a Aflevering number
                        iPkAflevering = oFix.get_pk(oAflevering, "dictionary.aflevering", True,
                                                    deel=iDeel,
                                                    sectie=iSectie,
                                                    aflnum = iAflevering)

                    # Process the ENTRY
                    sDialectWoord = arPart[5]
                    sDialectWoord = html.unescape(sDialectWoord).strip('"')
                    iPkEntry = oFix.get_pk(oEntry, "dictionary.entry", False,
                                           woord=sDialectWoord,
                                           toelichting=arPart[14],
                                           lemma=iPkLemma,
                                           dialect=iPkDialect,
                                           trefwoord=iPkTrefwoord,
                                           aflevering=iPkAflevering)
                    iRead += 1
                else:
                    # This line is being skipped
                    oSkip.append(strLine)
                    iSkipped += 1
                    sIdx = 'line-' + str(iValid)
                    if not sIdx in oBack:
                        oBack[sIdx] = 0
                    oBack[sIdx] +=1


        # CLose the input file
        f.close()

        # Close the skip file
        oSkip.close()

        # Finish the JSON array that contains the fixtures
        oFix.close()

        # return positively
        oBack['result'] = True
        oBack['skipped'] = iSkipped
        oBack['read'] = iRead
        return oBack
    except:
        errHandle.DoError("csv_to_fixture", True)
        return oBack

def isNullOrEmptyOrInt(arPart, lstColumn):
    for iIdx in lstColumn:
        sItem = arPart[iIdx]
        # Check if this item is empty, null or numeric
        if sItem == "" or sItem == "NULL" or sItem.isnumeric():
            # Indicate where the error was
            return iIdx

    # When everything has been checked and there is no indication, return false
    return 0
