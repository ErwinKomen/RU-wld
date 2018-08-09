"""Models for the wld records.

The wld is the "Dictionary of Limburg Dialects".
Each wld entry has a gloss, a definition and a number of variants in different dialects.
The dialects are identified by locations, and the locations are indicated by a 'Kloekecode'.

"""
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db import models
from django.db.models import Q
from datetime import datetime
import time
from wld.settings import APP_PREFIX, MEDIA_ROOT
from wld.utils import *
import os, os.path
import sys
import io
import codecs
import html
import json
                


MAX_IDENTIFIER_LEN = 10
MAX_LEMMA_LEN = 100
# oCsvImport = {'read': 0, 'skipped': 0, 'status': 'idle', 'method': 'none'}


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

def get_now_time():
    return time.clock()

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
  
def isNullOrEmptyOrInt(arPart, lstColumn):
    for iIdx in lstColumn:
        sItem = arPart[iIdx]
        # Check if this item is empty, null or numeric
        if sItem == "" or sItem == "NULL" or sItem.startswith('#') or sItem == "?" or sItem == "-" or sItem.isnumeric():
            # Indicate where the error was
            return iIdx

    # When everything has been checked and there is no indication, return false
    return 0

def isLineOkay(oLine):
    try:
        # Define which items need to be checked
        lCheck = ['lemma_name', 'trefwoord_name', 'dialectopgave_name', 'dialect_stad', 'dialect_nieuw']
        iIdx = 0
        # Walk all key-value pairs
        for (k,v) in oLine.items():
            iIdx += 1
            # Is this key part of the range that needs checking?
            if k in lCheck:
                # Perform the check here
                if v=="" or v=="NULL" or v.startswith('#') or v=="?" or v=="-" or v.isnumeric():
                    # Indicate where the error was
                    return iIdx

        # When everything has been checked and there is no indication, return false
        return 0
    except:
        errHandle.DoError("isLineOkay", True)
        return 0


# ----------------------------------------------------------------------------------
# Name :    partToLine
# Goal :    Convert an array of values into a structure
# History:
#  12/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def partToLine(sVersie, arPart, bDoMijnen):
    """Convert an array of values [arPart] into a structure"""

    try:
        oBack = {}
        # Preposing of all the parts
        if sVersie == "Lemmanummer":
            oBack['lemma_name'] = arPart[1]
            oBack['lemma_bronnenlijst'] = arPart[6]
            oBack['lemma_toelichting'] = arPart[2]
            oBack['lemma_boek'] = arPart[7]
            oBack['dialect_stad'] = arPart[10]
            oBack['dialect_nieuw'] = arPart[15]
            # oBack['dialect_toelichting'] = None
            oBack['dialect_kloeke'] = None
            oBack['trefwoord_name'] = arPart[3]
            oBack['trefwoord_toelichting'] = ""
            oBack['dialectopgave_name'] = arPart[5]
            oBack['dialectopgave_toelichting'] = arPart[14]
            oBack['dialectopgave_kloeketoelichting'] = ""         # See WLD issue #22
        elif sVersie == "lemma.name":
            oBack['lemma_name'] = arPart[0]
            oBack['lemma_bronnenlijst'] = arPart[2]
            oBack['lemma_toelichting'] = arPart[1]
            oBack['lemma_boek'] = ""
            oBack['dialect_stad'] = arPart[9]
            oBack['dialect_nieuw'] = arPart[8]
            # oBack['dialect_toelichting'] = arPart[10]
            oBack['dialect_kloeke'] = arPart[7]         # OLD KloekeCode
            oBack['trefwoord_name'] = arPart[3]
            oBack['trefwoord_toelichting'] = arPart[4]
            oBack['dialectopgave_name'] = arPart[5]
            oBack['dialectopgave_toelichting'] = arPart[6]
            oBack['dialectopgave_kloeketoelichting'] = arPart[10]   # See WLD issue #22

        if sVersie != "":
            # Unescape two items
            oBack['dialectopgave_name'] = html.unescape(oBack['dialectopgave_name'])
            oBack['trefwoord_name'] = html.unescape(oBack['trefwoord_name'])
            # Remove quotation marks everywhere and adapt NULL where needed
            for (k,v) in oBack.items():
                if oBack[k] != None:
                    oBack[k] = v.strip('"')
                    oBack[k] = oBack[k].strip()
                    if oBack[k].startswith("'") and oBack[k].endswith("'"):
                      oBack[k] = oBack[k].strip("'")
                    if oBack[k] == "NULL":
                        oBack[k] = ""
            # Need to treat the Mines??
            if bDoMijnen:
                # Check for unknown dialect location
                if oBack['dialect_stad'].lower() == "onbekend":
                    oBack['dialect_stad'] = "Zie mijnen"
                # Get the list of mines
                sMijnen = oBack['dialectopgave_kloeketoelichting'].replace('(', '').replace(')', '').strip()
                # Sanity check
                if sMijnen == "":
                    lMijnen = []
                else:
                    # Adaptations for Oranje nassau mijnen
                    sMijnen = sMijnen.replace('Oranje-Nassau I-IV', 'Oranje-Nassau I / Oranje-Nassau II / Oranje-Nassau III / Oranje-Nassau IV')
                    lMijnen = sMijnen.split('/')
                    # Remove spaces from the mines
                    for i, s in enumerate(lMijnen):
                        s = s.strip()
                        if s == "I": 
                            s = "Oranje-Nassau I"
                        elif s == "II":
                            s = "Oranje-Nassau II"
                        elif s == "III":
                            s = "Oranje-Nassau III"
                        elif s == "IV":
                            s = "Oranje-Nassau IV"
                        lMijnen[i] = s
                    
                # Add the list of Mijnen
                oBack['mijn_list'] = lMijnen

        # Return what we found
        return oBack
    except:
        # Provide more information
        errHandle.Status("partToLine error info [{}]".format(sVersie))
        for idx, val in enumerate(arPart):
            errHandle.Status("arPart[{}] = [{}]".format(idx, val))
        errHandle.DoError("partToLine", True)
        return None

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

    class Meta:
        index_together = ['toelichting', 'bronnenlijst', 'boek']

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
        """Return the identifier of the object described in self"""

        oErr = ErrHandle()
        try:
            # Get the parameters
            bronnenlijst = self['bronnenlijst']
            boek = self['boek']
            toelichting = ""
            if 'toelichting' in self:
                toelichting = self['toelichting']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(bronnenlijst__iexact=bronnenlijst))
            lstQ.append(Q(boek__iexact=boek))
            lstQ.append(Q(toelichting__iexact=toelichting))
            qItem = Description.objects.filter(*lstQ).first()
            # see if we get one value back
            if qItem == None:
                # add a new Description object
                descr = Description(bronnenlijst=bronnenlijst, boek=boek, toelichting=toelichting)
                descr.save()
                iPk = descr.pk
                qItem = descr
            else:
                # Get the pk of the first hit
                iPk = qItem.pk

            # Return the result
            return iPk, qItem
        except:
            oErr.DoError("Description/get_item error:")
            return -1, None

    def get_instance(options, instance, oTime = None):
        """Return the instance described by the options"""

        oErr = ErrHandle()
        bSpeedUp = True
        try:
            # Get the parameters
            bronnenlijst = options['bronnenlijst']
            boek = options['boek']
            toelichting = ""
            if 'toelichting' in options:
                toelichting = options['toelichting']
            # Check if we have an existing instance and if it equals that one
            if instance != None:
                if instance.bronnenlijst == bronnenlijst and instance.boek == boek and instance.toelichting == toelichting:
                    # Return this instance
                    return instance

            # SPEEDING UP:
            #  - If there was no previous instance, then just create a new one without searching any further.
            if bSpeedUp:
                qItem = None
            else:
                # Try find an existing item
                lstQ = []
                lstQ.append(Q(bronnenlijst__iexact=bronnenlijst))
                lstQ.append(Q(boek__iexact=boek))
                lstQ.append(Q(toelichting__iexact=toelichting))

                if oTime != None: iStart = get_now_time()
                qItem = Description.objects.filter(*lstQ).first()
                if oTime != None: oTime['search_Ds'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Description object
                if oTime != None: iStart = get_now_time()
                qItem = Description(bronnenlijst=bronnenlijst, boek=boek, toelichting=toelichting)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart

            # Return the result
            return qItem
        except:
            oErr.DoError("Description/get_instance error:")
            return None
        

class Lemma(models.Model):
    """Lemma"""

    gloss = models.CharField("Gloss voor dit lemma", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # toelichting = models.TextField("Omschrijving van het lemma", blank=True)
    # bronnenlijst = models.TextField("Bronnenlijst bij dit lemma", db_index=True, blank=True)
    # boek = models.TextField("Boekaanduiding", db_index=True, null=True,blank=True)
    lmdescr = models.ManyToManyField(Description, through='LemmaDescr')
    # A field that indicates this item may be showed
    toonbaar = models.BooleanField("Mag getoond worden", blank=False, default=True)

    class Meta:
        # Note: no index is possible, since lmdescr is many-to-many
        # index_together = ['gloss', 'lmdescr']
        verbose_name_plural = "Lemma's"

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
        oErr = ErrHandle()
        try:
            # Get the parameters
            gloss = self['gloss']
            try:
                # OLD: lemma = Lemma.objects.get(gloss__iexact=gloss)
                lemma = Lemma.objects.get(gloss=gloss)
            except ObjectDoesNotExist:
                lemma = Lemma(gloss=gloss)
                lemma.save()
            # Get the pk of the lemma
            iPk = lemma.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Lemma/get_item error:")
            return -1

    def get_instance(options, oTime = None):
        """Return the instance described by the options"""

        oErr = ErrHandle()
        try:
            # Get the parameters
            gloss = options['gloss']
            # Make sure it is lower case
            gloss = gloss.lower()
            # Try find an existing item
            lstQ = []
            # lstQ.append(Q(gloss__iexact=gloss))
            lstQ.append(Q(gloss=gloss))

            if oTime != None: iStart = get_now_time()
            qItem = Lemma.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_L'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                if oTime != None: iStart = get_now_time()
                qItem = Lemma(gloss=gloss)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart

            # Return the result
            return qItem
        except:
            oErr.DoError("Lemma/get_instance error:")
            return None

    def change_toonbaar():
        # Set all lemma's to 'toonbaar
        with transaction.atomic():
            for lemma in Lemma.objects.all():
                if lemma.toonbaar != True:
                    lemma.toonbaar = True
                    lemma.save()
        # Get a list of all lemma's that are NOT toonbaar
        lemma_show = Lemma.objects.filter(entry__aflevering__toonbaar=1).distinct()
        lemma_hide = Lemma.objects.exclude(Q(id__in=lemma_show))
        with transaction.atomic():
            for lemma in lemma_hide:
                lemma.toonbaar = False
                lemma.save()
        # Return positively
        return True


class LemmaDescr(models.Model):
    """Description belonging to a lemma"""

    lemma=models.ForeignKey(Lemma, on_delete=models.CASCADE)
    description=models.ForeignKey(Description, on_delete=models.CASCADE)

    class Meta:
        index_together = ['lemma', 'description']

    def get_item(self, oTime = None):
        oErr = ErrHandle()
        try:
            # Get the parameters
            lemma = self['lemma']
            description = self['description']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(lemma=lemma))
            lstQ.append(Q(description=description))

            if oTime != None: iStart = get_now_time()
            qItem = LemmaDescr.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_LD'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Description object
                # lemdescr = LemmaDescr(lemma=Lemma.objects.get(id=lemma), description=Description.objects.get(id=description))
                if oTime != None: iStart = get_now_time()
                qItem = LemmaDescr(lemma=lemma, description=description)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart
            # Get the pk of the first hit
            iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("LemmaDescr/get_item error:")
            return -1

    def get_instance(options):
        """Return the instance described by the options"""

        oErr = ErrHandle()
        try:
            # Get the parameters, which are *instances* (not id's)
            lemma = options['lemma']
            description = options['description']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(lemma=lemma))
            lstQ.append(Q(description=description))

            if oTime != None: iStart = get_now_time()
            qItem = LemmaDescr.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_LD'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Description object
                if oTime != None: iStart = get_now_time()
                qItem = LemmaDescr(lemma=lemma, description=description)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart

            # Return the result
            return qItem
        except:
            oErr.DoError("LemmaDescr/get_instance error:")
            return None
    

class Dialect(models.Model):
    """Dialect"""

    stad = models.CharField("Dialectlocatie", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    code = models.CharField("Plaatscode (Kloeke)", blank=False, max_length=6, default="xxxxxx")
    nieuw = models.CharField("Plaatscode (Nieuwe Kloeke)", db_index=True, blank=False, max_length=6, default="xxxxxx")
    # A field that indicates this item may be showed
    toonbaar = models.BooleanField("Mag getoond worden", blank=False, default=True)
    toelichting = models.TextField("Toelichting bij dialect", blank=True)

    class Meta:
        verbose_name_plural = "Dialecten"
        index_together = ['stad', 'code', 'nieuw']

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

    def get_item(self, oTime = None):
        oErr = ErrHandle()
        try:
            # Get the parameters
            stad = self['stad']
            nieuw = self['nieuw']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(stad__iexact=stad))
            lstQ.append(Q(nieuw__iexact=nieuw))

            if oTime != None: iStart = get_now_time()
            qItem = Dialect.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_Dt'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Dialect object
                if oTime != None: iStart = get_now_time()
                qItem = Dialect(stad=stad, nieuw=nieuw, code='-')
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart
            # Get the pk of the first hit
            iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Dialect/get_item error:")
            return -1

    def change_toonbaar():
        # Set all inst's to 'toonbaar
        with transaction.atomic():
            for inst in Dialect.objects.all():
                if inst.toonbaar != True:
                    inst.toonbaar = True
                    inst.save()
        # Get a list of all inst's that are NOT toonbaar
        dialect_show = Dialect.objects.filter(entry__aflevering__toonbaar=1).distinct()
        dialect_hide = Dialect.objects.exclude(Q(id__in=dialect_show))
        with transaction.atomic():
            for inst in dialect_hide:
                inst.toonbaar = False
                inst.save()
        # Return positively
        return True


class Trefwoord(models.Model):
    """Trefwoord"""

    woord = models.CharField("Trefwoord", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Toelichting bij trefwoord", blank=True)
    # A field that indicates this item may be showed
    toonbaar = models.BooleanField("Mag getoond worden", blank=False, default=True)

    class Meta:
        verbose_name_plural = "Trefwoorden"
        index_together = ['woord', 'toelichting']

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

    def get_item(self, oTime = None):
        oErr = ErrHandle()
        try:
            toelichting = None
            # Get the parameters
            woord = self['woord']
            # Make sure it is lower case
            woord = woord.lower()
            # Try find an existing item
            lstQ = []
            # lstQ.append(Q(woord__iexact=woord))
            lstQ.append(Q(woord=woord))
            if 'toelichting' in self:
                toelichting = self['toelichting']
                lstQ.append(Q(toelichting__iexact = toelichting))

            if oTime != None: iStart = get_now_time()
            qItem = Trefwoord.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_T'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Dialect object
                if oTime != None: iStart = get_now_time()
                qItem = Trefwoord(woord=woord)
                if toelichting != None:
                    qItem.toelichting = toelichting
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart
            # Get the pk of the first hit
            iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Trefwoord/get_item error:")
            return -1

    def change_toonbaar():
        # Set all inst's to 'toonbaar
        with transaction.atomic():
            for inst in Trefwoord.objects.all():
                if inst.toonbaar != True:
                    inst.toonbaar = True
                    inst.save()
        # Get a list of all inst's that are NOT toonbaar
        trefwoord_show = Trefwoord.objects.filter(entry__aflevering__toonbaar=1).distinct()
        trefwoord_hide = Trefwoord.objects.exclude(Q(id__in=trefwoord_show))
        with transaction.atomic():
            for inst in trefwoord_hide:
                inst.toonbaar = False
                inst.save()
        # Return positively
        return True


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


class Status(models.Model):
    """Status of importing a CSV file """

    # Number of read and skipped lines
    read = models.IntegerField("Gelezen", blank=False, default=0)
    skipped = models.IntegerField("Overgeslagen", blank=False, default=0)
    status = models.TextField("Status", blank=False, default="idle")
    method = models.CharField("Reading method", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Link to the Info
    info = models.ForeignKey(Info, blank=False)

    def set_status(self, sStatus, sMsg = None):
        self.status = sStatus
        self.save()


class Repair(models.Model):
    """Definition and status of a repair action"""

    # Definition of this repair type
    repairtype = models.CharField("Soort reparatie", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Status of this repair action
    status = models.TextField("Status", blank=False, default="idle")


class Aflevering(models.Model):
    """Aflevering van een woordenboek"""

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
    # A field that indicates this item may be showed
    toonbaar = models.BooleanField("Mag getoond worden", blank=False, default=True)
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

    class Meta:
        verbose_name_plural = "Afleveringen"
        index_together = ['deel', 'sectie', 'aflnum']

    def __str__(self):
        return self.naam

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        # Get the original
        orig = Aflevering.objects.get(pk=self.pk)
        bToonbaarChanged = (self.toonbaar != orig.toonbaar)
        result = super(Aflevering, self).save(force_insert, force_update, using, update_fields)
        # Action if Toonbaar has changed
        if bToonbaarChanged:
            # Adapt Lemma, Trefwoord and Dialect instances
            Lemma.change_toonbaar()
            Trefwoord.change_toonbaar()
            Dialect.change_toonbaar()
        return result

    def get_number(self):
        if self.sectie == None:
            iNumber = self.aflnum
        else:
            iNumber = self.sectie * 10 + self.aflnum
        return iNumber

    def get_summary(self):
        sSum = int_to_roman(self.deel.nummer) + "-"
        if self.sectie != None:
            sSum += str(self.sectie) + "-"
        sSum += str(self.aflnum)
        return sSum

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
        oErr = ErrHandle()
        try:
            # Get the parameters
            deel = self['deel']
            sectie = self['sectie']
            aflnum = self['aflnum']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(deel__nummer__iexact=deel))
            lstQ.append(Q(aflnum__iexact=aflnum))
            if sectie != None:
                lstQ.append(Q(sectie__iexact = sectie))
            qItem = Aflevering.objects.filter(*lstQ).first()
            # see if we get one value back
            if qItem == None:
                # We cannot add a new item
                iPk = -1
            else:
                # Get the pk of the first hit
                iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Aflevering/get_item error:")
            return -1


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

    def get_item(self, oTime = None):
        oErr = ErrHandle()
        try:
            # Get the parameters
            naam = self['naam']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(naam__iexact=naam))

            if oTime != None: iStart = get_now_time()
            qItem = Mijn.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_M'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Dialect object
                if oTime != None: iStart = get_now_time()
                qItem = Mijn(naam=naam)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart
            # Get the pk of the first hit
            iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Mijn/get_item error:")
            return -1


class Entry(models.Model):
    """Dictionary entry"""

    class Meta:
        verbose_name_plural = "Entries"
        ordering = ['lemma', 'woord']
        permissions = ( ('search_gloss', 'Can search/view/edit full entry details'),
                       )
        index_together = [
            ["dialect", "lemma", "trefwoord", "woord"],
            ["lemma", "aflevering"],
          ]

    def __str__(self):
        return self.woord + '_' + self.dialect.code

    # Lemma: obligatory
    lemma = models.ForeignKey(Lemma, db_index=True, blank=False)
    # Description: this description should be one and the same for a whole lemma, but this is not true in practice
    descr = models.ForeignKey(Description, db_index=True, blank=False)
    # Dialect: obligatory
    dialect = models.ForeignKey(Dialect, db_index=True, blank=False)
    # Trefwoord: obligatory
    trefwoord = models.ForeignKey(Trefwoord, db_index=True, blank=False)
    # Mijn [0-1]
    # mijn = models.ForeignKey(Mijn, blank = True, null=True)
    # Mijn [0-n]
    mijnlijst = models.ManyToManyField(Mijn, db_index=True, through='EntryMijn')
    # Aflevering [1]
    aflevering = models.ForeignKey(Aflevering, db_index=True, blank=False)
    # Dialectal entry: obligatory
    woord = models.CharField("Dialectopgave", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Notes to this entry: optional
    toelichting = models.TextField("Toelichting", db_index=True, blank=True)
    # See WLD issue #22
    kloeketoelichting = models.TextField("Toelichting bij dialectopgave voor een bepaalde kloekelocatie", blank=True)

    def get_trefwoord_woord(self):
        return self.trefwoord.woord + '_' + self.woord

    def get_trefwoord_lemma_woord(self):
        return self.trefwoord.woord + '_' +self.lemma.gloss + "_" + self.woord

    def dialectopgave(self):
        sWoord = "*"
        # Are we allowed to show it?
        if self.aflevering.toonbaar:
            sWoord = self.woord
        return sWoord

    def get_toelichting(self):
        return self.toelichting

    def get_aflevering(self):
        afl = self.aflevering
        sAfl = "d" + str(afl.deel.nummer) + "-"
        if afl.sectie != None:
            sAfl += "s" + str(afl.sectie) + "-"
        sAfl += "a" + str(afl.aflnum)
        return sAfl

    def get_lemma_gloss(self):
        return self.lemma.gloss + '_' + self.woord

    def get_row(self):
        arRow = []
        arRow.append(self.lemma.gloss)
        arRow.append(self.trefwoord.woord)
        arRow.append(self.woord)
        arRow.append(self.dialect.nieuw)
        arRow.append(self.aflevering.naam)
        arRow.append(self.descr.bronnenlijst)
        return arRow

    def get_tsv(self):
        return self.lemma.gloss + '\t' + self.trefwoord.woord + '\t' + self.woord + '\t' + self.dialect.nieuw + '\t' + self.aflevering.naam

    def get_pk(self):
        """Check if this [entry] exists and return a PK"""
        qs = Entry.objects.filter(woord__iexact=self['woord'], 
                                  toelichting__iexact=self['toelichting'],
                                  kloeketoelichting__iexact=self['kloeketoelichting'],
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
        kloeketoelichting=""

        # Get the parameters out of [self]
        woord = self['woord']
        toelichting = self['toelichting']
        lemmaPk = self['lemma']
        dialectPk = self['dialect']
        trefwoordPk = self['trefwoord']
        afleveringPk = self['aflevering']
        if 'kloeketoelichting' in self:
            kloeketoelichting = self['kloeketoelichting']
        if 'mijn' in self:
            mijnPk = self['mijn']

        # Try find an existing item
        lstQ = []
        lstQ.append(Q(woord__iexact=woord))
        lstQ.append(Q(toelichting__iexact=toelichting))
        lstQ.append(Q(lemma__pk=lemmaPk))
        lstQ.append(Q(dialect__pk = dialectPk))
        lstQ.append(Q(trefwoord__pk = trefwoordPk))
        lstQ.append(Q(aflevering__pk = afleveringPk))
        lstQ.append(Q(mijn__pk = mijnPk))
        lstQ.append(Q(kloeketoelichting = kloeketoelichting))

        qs = Entry.objects.filter(*lstQ)
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
                              kloeketoelichting = kloeketoelichting,
                              aflevering = aflevering, mijn = mijn)
            else:
                # add a new Dialect object
                entry = Entry(woord=woord, toelichting = toelichting, lemma=lemma,
                              dialect = dialect, trefwoord = trefwoord,
                              kloeketoelichting = kloeketoelichting,
                              aflevering = aflevering)
            entry.save()
            iPk = entry.pk
        else:
            # Get the pk of the first hit
            iPk = qs[0].pk

        # Return the result
        return iPk


class EntryMijn(models.Model):
    """Connection between Entry and Mijn"""

    entry=models.ForeignKey(Entry, db_index=True, on_delete=models.CASCADE)
    mijn=models.ForeignKey(Mijn, db_index=True, on_delete=models.CASCADE)

    def get_item(self, bSet):
        # Get the parameters
        entry = self['entry']
        mijn = self['mijn']
        # Try find an existing item
        qItem = EntryMijn.objects.filter(entry=entry, 
                                         mijn=mijn).first()
        # see if we get one value back
        if qItem == None:
            # add a new Description object
            if bSet:
                # Just add this link; do not start looking for Entry or Mijn
                entrymijn = EntryMijn(entry_id=entry, mijn_id=mijn)
            else:
                entrymijn = EntryMijn(entry=Entry.objects.get(id=entry), mijn=Mijn.objects.get(id=mijn))
            entrymijn.save()
            iPk = entrymijn.pk
        else:
            # Get the pk of the first hit
            iPk = qItem.pk

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
            # Make sure numeric values are 
            # Check all the items given: do it reversed, because then we have the best chance of getting something
            for it in reversed(arItem):
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
                if 'pk' in oFields:
                    # Get the pk value and *remove* the key from the field
                    iPkItem = oFields.pop('pk')                    
                else:
                    iPkItem = len(oCls.lstItem)

                iPkItem += 1
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


class fEntryMijn:
    """Connection between entry and mijn information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known items

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, entry=item.entry, mijn=item.mijn))
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
    lstItem = []   # Array of known items

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, woord=item.woord))
                self.pk = item.pk


class fMijn:
    """Mijn information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known items

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, naam=item.naam))
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
# Name :    csv_to_fixture_old
# Goal :    Convert CSV file into a fixtures file
# History:
#  1/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def csv_to_fixture_old(csv_file, iDeel, iSectie, iAflevering, iStatus, bUseDbase=False, bUseOld=False):
    """Process a CSV with entry definitions"""

    oBack = {}      # What we return
    sVersie = ""    # The version we are using--this depends on the column names
    sDict = "wbd"   # The dictionary we are working for: wld, wbd, 
    # bUsdDbaseMijnen = False
    bUsdDbaseMijnen = True
    oErr = ErrHandle()

    try:
        # Retrieve the correct instance of the status object
        oStatus = Status.objects.filter(id=iStatus).first()
        oStatus.status = "preparing"
        if bUseDbase:
            oStatus.method = "db"
        else:
            oStatus.method = "lst"
        # Save the status to the database
        oStatus.save()

        oBack['result'] = False

        if str(iDeel).isnumeric(): iDeel = int(iDeel)
        if str(iSectie).isnumeric(): iSectie = int(iSectie)
        if str(iAflevering).isnumeric(): iAflevering = int(iAflevering)

        bDoEverything = (iDeel == 0 and iSectie == 0 and iAflevering == 0)
        lstInfo = []

        if bDoEverything:
            # Special method: treat all the files under 'csv_files'
            for oInfo in Info.objects.all():
                lstInfo.append(oInfo)
        else:
            # Validate: input file exists
            if not "/" in csv_file and not "\\" in csv_file:
                csv_file = os.path.abspath( os.path.join(MEDIA_ROOT, "csv_files", csv_file))
            elif csv_file.startswith("csv_files"):
                csv_file = os.path.abspath( os.path.join(MEDIA_ROOT, csv_file))
            if (not os.path.isfile(csv_file)): 
                oStatus.set_status("error", "Cannot find file " + csv_file)
                return oBack

            # Get the [Info] object
            if iSectie == None:
                oInfo = Info.objects.filter(deel=iDeel, aflevering=iAflevering).first()
            else:
                oInfo = Info.objects.filter(deel=iDeel, sectie=iSectie, aflevering=iAflevering).first()
            lstInfo.append(oInfo)

        # Start creating an array that will hold the fixture elements
        arFixture = []
        iPkLemma = 1        # The PK for each Lemma
        iPkDescr = 1        # The PK for each Description (lemma-toelichting many-to-many)
        iPkTrefwoord = 1    # The PK for each Trefwoord
        iPkDialect = 1      # The PK for each Dialect
        iPkEntry = 0        # The PK for each Entry
        iPkAflevering = 1   # The PK for each Aflevering
        iPkMijn = 1         # The PK for each Mijn
        iPkEntryMijn = 1    # The PK for each Entry/Mijn
        iCounter = 0        # Loop counter for progress
        iRead = 0           # Number read correctly
        iSkipped = 0        # Number skipped

        # Create instances of the Lemma, Dialect and other classes
        oLemma = fLemma()
        oDescr = fDescr()
        oLemmaDescr = fLemmaDescr()
        oDialect = fDialect()
        oTrefwoord = fTrefwoord()
        oAflevering = fAflevering()
        oEntry = fEntry()
        oMijn = fMijn()
        oEntryMijn = fEntryMijn()

        # Initialise the lists in these instances (where needed)
        oDialect.load(Dialect.objects.all())
        oAflevering.load(Aflevering.objects.all())
        oMijn.load(Mijn.objects.all())
        if bUseOld:
            oLemma.load(Lemma.objects.all())
            oTrefwoord.load(Trefwoord.objects.all())
            oLemmaDescr.load(LemmaDescr.objects.all())
            oDescr.load(Description.objects.all())
            # It should *not* be necessary to load all existing ENTRY objects
            #    since we assume that any object to be added is UNIQUE
            # oEntry.load(Entry.objects.all())
            oEntryMijn.load(EntryMijn.objects.all())

            # Determine what the maximum [pk] for [Entry] currently in use is
            if Entry.objects.all().count() == 0:
                iPkEntry = 0
            else:
                iPkEntry = Entry.objects.latest('id').id


        # Process all the objects in [lstInfo]
        for oInfo in lstInfo:
            # Get the details of this object
            csv_file = oInfo.csv_file.path
            iDeel = oInfo.deel
            iSectie = oInfo.sectie
            iAflevering = oInfo.aflnum
            sProcessed = ""
            if oInfo.processed != None:
                sProcessed = oInfo.processed

            # Determine whether we will process this item or not
            bDoThisItem = (sProcessed == "")

            if bDoThisItem:
                # Make sure 'NONE' sectie is turned into an empty string
                if iSectie == None: iSectie = ""

                iRead = 0           # Number read correctly
                iSkipped = 0        # Number skipped

                sWorking = "working {}/{}/{}".format(iDeel, iSectie, iAflevering)

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

                # get a Aflevering number
                if str(iDeel).isnumeric(): iDeel = int(iDeel)
                if str(iSectie).isnumeric(): iSectie = int(iSectie)
                if str(iAflevering).isnumeric(): iAflevering = int(iAflevering)
                if iSectie == None or iSectie == "":
                    oAfl = Aflevering.objects.filter(deel__nummer=iDeel, aflnum=iAflevering).first()
                else:
                    oAfl = Aflevering.objects.filter(deel__nummer=iDeel, sectie=iSectie, aflnum=iAflevering).first()
                iPkAflevering = oAfl.pk

                # Open source file to read line-by-line
                f = codecs.open(csv_file, "r", encoding='utf-8-sig')
                bEnd = False
                bFirst = True
                bFirstOut = False
                bDoMijnen = (iDeel == 2 and iAflevering == 5)   # Treat 'Mijn' for WLD-II-5
                lMijnen = []
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
                        # Convert the array of values to a structure
                        oLine = partToLine(sVersie, arPart, bDoMijnen)
                        # Check if this line contains 'valid' data:
                        iValid = isLineOkay(oLine)
                        # IF this is the first line or an empty line, then skip
                        if bFirst:
                            # Get the version from cell 0, line 0
                            sVersie = arPart[0]
                            # Check if the line starts correctly
                            if sVersie != 'Lemmanummer' and sVersie != "lemma.name":
                                # The first line does not start correctly -- return false
                                return oBack
                            # Indicate that the first item has been had
                            bFirst = False
                        elif iValid == 0:
                            # Assuming this 'part' is entering an ENTRY

                            # Make sure we got TREFWOORD correctly
                            sTrefWoord = oLine['trefwoord_name']

                            if bDoMijnen and 'mijn_list' in oLine:
                                lMijnen = oLine['mijn_list']


                            if bUseDbase:
                                # Find out which lemma this is
                                iPkLemma = Lemma.get_item({'gloss': oLine['lemma_name']})

                                # Find out which lemma-description this is
                                iPkDescr = Description.get_item({'bronnenlijst': oLine['lemma_bronnenlijst'],
                                                                 'toelichting': oLine['lemma_toelichting'], 
                                                                 'boek': oLine['lemma_boek']})

                                # Add the [iPkDescr] to the LemmaDescr--but only if it is not already there
                                iPkLemmaDescr = LemmaDescr.get_item({'lemma': iPkLemma,
                                                                     'description': iPkDescr})

                                # Find out which dialect this is
                                if oLine['dialect_toelichting'] != None and oLine['dialect_kloeke'] != None:
                                    iPkDialect = Dialect.get_item({'stad': oLine['dialect_stad'], 
                                                                    'nieuw': oLine['dialect_nieuw'],
                                                                    'code': oLine['dialect_kloeke'],
                                                                    'toelichting': oLine['dialect_toelichting']})
                                else:
                                    iPkDialect = Dialect.get_item({'stad': oLine['dialect_stad'], 
                                                                    'nieuw': oLine['dialect_nieuw']})

                                # Find out which trefwoord this is
                                sTwToel = oLine['trefwoord_toelichting']
                                if sTwToel == None or sTwToel == "":
                                    iPkTrefwoord = Trefwoord.get_item({'woord': sTrefWoord})
                                else:
                                    iPkTrefwoord = Trefwoord.get_item({'woord': sTrefWoord,
                                                                       'toelichting': sTwToel})

                            else:
                                # Get a lemma number from this
                                # NOTE: assume 2 = toelichting 
                                iPkLemma = oFix.get_pk(oLemma, "dictionary.lemma", True,
                                                       gloss=oLine['lemma_name'])

                                # Get a description number
                                iPkDescr = oFix.get_pk(oDescr, "dictionary.description", True,
                                                       bronnenlijst=oLine['lemma_bronnenlijst'], 
                                                       toelichting=oLine['lemma_toelichting'], 
                                                       boek=oLine['lemma_boek'])

                                # Add the Lemma-Description connection
                                iPkLemmaDescr = oFix.get_pk(oLemmaDescr, "dictionary.lemmadescr", True,
                                                            lemma=iPkLemma,
                                                            description=iPkDescr)


                                # get a dialect number
                                if oLine['dialect_toelichting'] != None and oLine['dialect_kloeke'] != None:
                                    iPkDialect = oFix.get_pk(oDialect, "dictionary.dialect", True,
                                                             stad=oLine['dialect_stad'], 
                                                             nieuw=oLine['dialect_nieuw'],
                                                             code=oLine['dialect_kloeke'],
                                                             toelichting=oLine['dialect_toelichting'])
                                else:
                                    iPkDialect = oFix.get_pk(oDialect, "dictionary.dialect", True,
                                                             stad=oLine['dialect_stad'], 
                                                             nieuw=oLine['dialect_nieuw'])

                                # get a trefwoord number
                                sTwToel = oLine['trefwoord_toelichting']
                                if sTwToel == None or sTwToel == "":
                                    iPkTrefwoord = oFix.get_pk(oTrefwoord, "dictionary.trefwoord", True,
                                                               woord=sTrefWoord)
                                else:
                                    iPkTrefwoord = oFix.get_pk(oTrefwoord, "dictionary.trefwoord", True,
                                                               woord=sTrefWoord,
                                                               toelichting=sTwToel)

                            # Process the ENTRY
                            sDialectWoord = oLine['dialectopgave_name']
                            # Make sure that I use my OWN continuous [pk] for Entry
                            iPkEntry += 1
                            # Do *NOT* use the Entry PK that is returned 
                            iDummy = oFix.get_pk(oEntry, "dictionary.entry", False,
                                                   pk=iPkEntry,
                                                   woord=sDialectWoord,
                                                   toelichting=oLine['dialectopgave_toelichting'],
                                                   lemma=iPkLemma,
                                                   dialect=iPkDialect,
                                                   trefwoord=iPkTrefwoord,
                                                   aflevering=iPkAflevering)

                            if bDoMijnen:
                                if bUseDbase and bUsdDbaseMijnen:
                                    # Walk all the mijnen for this entry
                                    for sMijn in lMijnen:
                                        # Get the PK for this mijn
                                        iPkMijn = Mijn.get_item({'naam': sMijn})
                                        # Process the PK for EntryMijn
                                        iPkEntryMijn = EntryMijn.get_item({'entry': iPkEntry,
                                                                           'mijn': iPkMijn})

                                else:
                                    # Walk all the mijnen for this entry
                                    for sMijn in lMijnen:
                                        # Get the PK for this mijn
                                        iPkMijn = oFix.get_pk(oMijn, "dictionary.mijn", True,
                                                              naam=sMijn)
                                        # Process the PK for EntryMijn
                                        iPkEntryMijn = oFix.get_pk(oEntryMijn, "dictionary.entrymijn", False,
                                                                   pk=iPkEntryMijn,
                                                                   entry=iPkEntry,
                                                                   mijn=iPkMijn)
                            iRead += 1
                        else:
                            # This line is being skipped
                            oSkip.append(strLine)
                            iSkipped += 1
                            sIdx = 'line-' + str(iValid)
                            if not sIdx in oBack:
                                oBack[sIdx] = 0
                            oBack[sIdx] +=1
                    # Keep track of progress
                    oStatus.skipped = iSkipped
                    oStatus.read = iRead
                    oStatus.status = sWorking
                    oStatus.save()


                # CLose the input file
                f.close()

                # Close the skip file
                oSkip.close()

                # Finish the JSON array that contains the fixtures
                oFix.close()

                # Note the results for this info object
                oInfo.read = iRead
                oInfo.skipped = iSkipped
                oInfo.processed = "Processed at {:%d/%b/%Y %H:%M:%S}".format(datetime.now())
                oInfo.save()

        # return positively
        oBack['result'] = True
        oBack['skipped'] = iSkipped
        oBack['read'] = iRead
        # oCsvImport['status'] = 'done'
        oStatus.status = "done"
        oStatus.save()
        return oBack
    except:
        # oCsvImport['status'] = 'error'
        oStatus.status = "error"
        oStatus.save()
        errHandle.DoError("csv_to_fixture", True)
        return oBack

# -----------------------------------------------------------------------------------------------------
# Name :    csv_to_fixture
# Goal :    Convert CSV file into a fixtures file
# History:
#  1/dec/2016   ERK Created
#  8/aug/2018   ERK Copied adaptation from the e-WBD version
# -----------------------------------------------------------------------------------------------------
def csv_to_fixture(csv_file, iDeel, iSectie, iAflevering, iStatus, bUseDbase=False, bUseOld=False):
    """Process a CSV with entry definitions"""

    oBack = {}      # What we return
    sVersie = ""    # The version we are using--this depends on the column names
    sDict = "wld"   # The dictionary we are working for: wld, wbd, 
    # bUsdDbaseMijnen = False
    bUsdDbaseMijnen = True
    oErr = ErrHandle()

    try:
        # Retrieve the correct instance of the status object
        oStatus = Status.objects.filter(id=iStatus).first()
        oStatus.status = "preparing"
        if bUseDbase:
            oStatus.method = "db"
        else:
            oStatus.method = "lst"
        # Save the status to the database
        oStatus.save()

        oBack['result'] = False

        if str(iDeel).isnumeric(): iDeel = int(iDeel)
        if str(iSectie).isnumeric(): iSectie = int(iSectie)
        if str(iAflevering).isnumeric(): iAflevering = int(iAflevering)

        bDoEverything = (iDeel == 0 and iSectie == 0 and iAflevering == 0)
        lstInfo = []

        if bDoEverything:
            # Special method: treat all the files under 'csv_files'
            for oInfo in Info.objects.all():
                lstInfo.append(oInfo)
        else:
            # Validate: input file exists
            if not "/" in csv_file and not "\\" in csv_file:
                csv_file = os.path.abspath( os.path.join(MEDIA_ROOT, "csv_files", csv_file))
            elif csv_file.startswith("csv_files"):
                csv_file = os.path.abspath( os.path.join(MEDIA_ROOT, csv_file))
            if (not os.path.isfile(csv_file)): 
                oStatus.set_status("error", "Cannot find file " + csv_file)
                return oBack

            # Get the [Info] object
            if iSectie == None or iSectie == "":
                oInfo = Info.objects.filter(deel=iDeel, aflnum=iAflevering).first()
            else:
                oInfo = Info.objects.filter(deel=iDeel, sectie=iSectie, aflnum=iAflevering).first()
            lstInfo.append(oInfo)

        # Start creating an array that will hold the fixture elements
        arFixture = []
        iPkLemma = 1        # The PK for each Lemma
        iPkDescr = 1        # The PK for each Description (lemma-toelichting many-to-many)
        iPkTrefwoord = 1    # The PK for each Trefwoord
        iPkDialect = 1      # The PK for each Dialect
        iPkEntry = 0        # The PK for each Entry
        iPkAflevering = 1   # The PK for each Aflevering
        iPkMijn = 1         # The PK for each Mijn
        iPkEntryMijn = 1    # The PK for each Entry/Mijn
        iCounter = 0        # Loop counter for progress
        iRead = 0           # Number read correctly
        iSkipped = 0        # Number skipped

        # Prepare the entry object
        oEntry = fEntry()

        # Create instances of the Lemma, Dialect and other classes
        if not bUseDbase:
            oLemma = fLemma()
            oDescr = fDescr()
            oLemmaDescr = fLemmaDescr()
            oDialect = fDialect()
            oTrefwoord = fTrefwoord()
            oAflevering = fAflevering()
            oMijn = fMijn()
            oEntryMijn = fEntryMijn()

            # Initialise the lists in these instances (where needed)
            oDialect.load(Dialect.objects.all())
            oAflevering.load(Aflevering.objects.all())
            oMijn.load(Mijn.objects.all())
            if bUseOld:
                # Indicate we are loading existing stuff

                # Start loading...
                oStatus.set_status("loading lemma's")
                oLemma.load(Lemma.objects.all())

                oStatus.set_status("loading keywords")
                oTrefwoord.load(Trefwoord.objects.all())

                iSize = LemmaDescr.objects.all().count()
                oStatus.set_status("loading {} lemma-descriptions ".format(iSize))
                oLemmaDescr.load(LemmaDescr.objects.all())

                oStatus.set_status("loading descriptions")
                oDescr.load(Description.objects.all())
                # It should *not* be necessary to load all existing ENTRY objects
                #    since we assume that any object to be added is UNIQUE
                # oEntry.load(Entry.objects.all())
                oStatus.set_status("loading mines")
                oEntryMijn.load(EntryMijn.objects.all())

        if bUseOld:
            # Determine what the maximum [pk] for [Entry] currently in use is
            if Entry.objects.all().count() == 0:
                iPkEntry = 0
            else:
                iPkEntry = Entry.objects.latest('id').id

        # First check the presence of all the 'promised' files
        lMsg = []
        for oInfo in lstInfo:
            # Get the details of this object
            csv_file = oInfo.csv_file.path
            iDeel = oInfo.deel
            iSectie = oInfo.sectie
            iAflevering = oInfo.aflnum
            if not os.path.isfile(csv_file):
                lMsg.append("{}/{}/{} file is not existing: {}".format(
                    iDeel, iSectie, iAflevering, csv_file))

        # Any messages?
        if len(lMsg) > 0:
            sMsg = "\n".join(lMsg)
            oStatus.set_status("error", sMsg)
            oBack['result'] = False
            oBack['msg'] = sMsg
            oErr.Status(sMsg)
            return oBack

        # Initialization of 'last' items
        descr_this = None
        
        # Process all the objects in [lstInfo]
        for oInfo in lstInfo:
            # Get the details of this object
            csv_file = oInfo.csv_file.path
            iDeel = oInfo.deel
            iSectie = oInfo.sectie
            iAflevering = oInfo.aflnum
            sProcessed = ""
            if oInfo.processed != None:
                sProcessed = oInfo.processed

            # Determine whether we will process this item or not
            bDoThisItem = (sProcessed == "" and (iDeel>0 or iSectie>0 or iAflevering>0))

            if bDoThisItem:
                # Make sure 'NONE' sectie is turned into an empty string
                if iSectie == None: iSectie = ""

                iRead = 0           # Number read correctly
                iSkipped = 0        # Number skipped

                sWorking = "working {}/{}/{}".format(iDeel, iSectie, iAflevering)
                oStatus.set_status(sWorking)
                oErr.Status(sWorking)

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

                # get a Aflevering number
                if str(iDeel).isnumeric(): iDeel = int(iDeel)
                if str(iSectie).isnumeric(): iSectie = int(iSectie)
                if str(iAflevering).isnumeric(): iAflevering = int(iAflevering)
                lstQ = []
                lstQ.append(Q(deel__nummer=iDeel))
                lstQ.append(Q(aflnum=iAflevering))
                if iSectie != None and iSectie != "":
                    lstQ.append(Q(sectie=iSectie))
                oAfl = Aflevering.objects.filter(*lstQ).first()
                iPkAflevering = oAfl.pk

                # Open source file to read line-by-line
                f = codecs.open(csv_file, "r", encoding='utf-8-sig')
                bEnd = False
                bFirst = True
                bFirstOut = False

                sVersie = ""
                sLastLemma = ""     # For speeding up processing
                sLastLemmaDescr = ""
                sLastTw = ""
                sLastTwToel = ""

                # The use of 'mijnen' depends on the dictionary we are working for (wld, wbd, wgd)
                lMijnen = []
                if sDict == "wld" or sDict == "wgd":
                    # The WLD uses mijnen in 2/5
                    bDoMijnen = (iDeel == 2 and iAflevering == 5)   # Treat 'Mijn' for wbd-II-5
                else:
                    # The WBD doesn't have any mijnen
                    bDoMijnen = False

                # Time measurements: keep track of time used in different parts
                oTime = {}
                oTime['read'] = 0   # time to read the source file
                oTime['db'] = 0     # Time spent in reading and saving database items
                oTime['entry'] = 0  # Processing entries
                oTime['save'] = 0   # Time spent in saving
                oTime['search_L'] = 0   # Time spent in searching (lemma)
                oTime['search_T'] = 0   # Time spent in searching (trefwoord)
                oTime['search_Ds'] = 0  # Time spent in searching (description)
                oTime['search_Dt'] = 0  # Time spent in searching (dialect)
                oTime['search_LD'] = 0  # Time spent in searching (lemmadescription)
                oTime['search_M'] = 0   # Time spent in searching (mijn)

                # Iterate through the lines of the CSV file
                while (not bEnd):
                    # Show where we are
                    iCounter +=1
                    if iCounter % 1000 == 0:
                        errHandle.Status("Processing: " + str(iCounter))
                    # Read one line
                    iStarttime = get_now_time()
                    strLine = f.readline()
                    if (strLine == ""):
                        bEnd = True
                        break
                    strLine = str(strLine)
                    strLine = strLine.strip(" \n\r")
                    oTime['read'] += get_now_time() - iStarttime
                    # Only process substantial lines
                    if (strLine != ""):
                        # Split the line into parts
                        arPart = strLine.split('\t')
                        # Convert the array of values to a structure
                        oLine = partToLine(sVersie, arPart, bDoMijnen)
                        # Check if this line contains 'valid' data:
                        iValid = isLineOkay(oLine)
                        # IF this is the first line or an empty line, then skip
                        if bFirst:
                            # Get the version from cell 0, line 0
                            sVersie = arPart[0]
                            # Check if the line starts correctly
                            if sVersie != 'Lemmanummer' and sVersie != "lemma.name":
                                # The first line does not start correctly -- return false
                                oErr.DoError("csv_to_fixture: cannot process version [{}]".format(sVersie))
                                return oBack
                            # Indicate that the first item has been had
                            bFirst = False
                        elif iValid == 0:
                            # Assuming this 'part' is entering an ENTRY

                            # Make sure we got TREFWOORD correctly
                            sTrefWoord = oLine['trefwoord_name']

                            if bDoMijnen and 'mijn_list' in oLine:
                                lMijnen = oLine['mijn_list']


                            if bUseDbase:
                                # Try to do all of this within one actual transation
                                iStarttime = get_now_time()
                                with transaction.atomic():
                                    # Find out which lemma this is
                                    sLemma = oLine['lemma_name']
                                    if sLemma != sLastLemma:
                                        lemma_this = Lemma.get_instance({'gloss': sLemma}, oTime)
                                        sLastLemma = sLemma

                                    # Find out which lemma-description this is
                                    descr_this = Description.get_instance({'bronnenlijst': oLine['lemma_bronnenlijst'],
                                                                     'toelichting': oLine['lemma_toelichting'], 
                                                                     'boek': oLine['lemma_boek']}, descr_this, oTime)

                                    # We do need the PKs of the lemma and the description
                                    iPkLemma = lemma_this.pk
                                    iPkDescr = descr_this.pk

                                    # Add the [iPkDescr] to the LemmaDescr--but only if it is not already there
                                    iPkLemmaDescr = LemmaDescr.get_item({'lemma': lemma_this,
                                                                         'description': descr_this}, oTime)

                                    # Find out which dialect this is
                                    if oLine['dialect_kloeke'] != None and oLine['dialect_kloeke'] != "":
                                        iPkDialect = Dialect.get_item({'stad': oLine['dialect_stad'], 
                                                                        'nieuw': oLine['dialect_nieuw'],
                                                                        'code': oLine['dialect_kloeke']}, oTime)
                                        # Note: removed 'dialect_toelichting' in accordance with issue #22 of WLD
                                    else:
                                        iPkDialect = Dialect.get_item({'stad': oLine['dialect_stad'], 
                                                                        'nieuw': oLine['dialect_nieuw']}, oTime)

                                    # Find out which trefwoord this is
                                    sTwToel = oLine['trefwoord_toelichting']
                                    if sTwToel == None or sTwToel == "":
                                        if sLastTwToel != "" or sLastTw != sTrefWoord:
                                            iPkTrefwoord = Trefwoord.get_item({'woord': sTrefWoord}, oTime)
                                            sLastTw = sTrefWoord
                                            sLastTwToel = ""
                                    else:
                                        if sLastTw != sTrefWoord or sLastTwToel != sTwToel:
                                            iPkTrefwoord = Trefwoord.get_item({'woord': sTrefWoord,
                                                                           'toelichting': sTwToel}, oTime)
                                            sLastTw = sTrefWoord
                                            sLastTwToel = sTwToel
                                oTime['db'] += get_now_time() - iStarttime

                            else:
                                # Get a lemma number from this
                                iStarttime = get_now_time()
                                # NOTE: assume 2 = toelichting 
                                iPkLemma = oFix.get_pk(oLemma, "dictionary.lemma", True,
                                                       gloss=oLine['lemma_name'])

                                # Get a description number
                                iPkDescr = oFix.get_pk(oDescr, "dictionary.description", True,
                                                       bronnenlijst=oLine['lemma_bronnenlijst'], 
                                                       toelichting=oLine['lemma_toelichting'], 
                                                       boek=oLine['lemma_boek'])

                                # Add the Lemma-Description connection
                                iPkLemmaDescr = oFix.get_pk(oLemmaDescr, "dictionary.lemmadescr", True,
                                                            lemma=iPkLemma,
                                                            description=iPkDescr)


                                # get a dialect number
                                if oLine['dialect_kloeke'] != None:
                                    iPkDialect = oFix.get_pk(oDialect, "dictionary.dialect", True,
                                                             stad=oLine['dialect_stad'], 
                                                             nieuw=oLine['dialect_nieuw'],
                                                             code=oLine['dialect_kloeke'])
                                    # Note: removed 'dialect_toelichting' in accordance with issue #22 of WLD
                                else:
                                    iPkDialect = oFix.get_pk(oDialect, "dictionary.dialect", True,
                                                             stad=oLine['dialect_stad'], 
                                                             nieuw=oLine['dialect_nieuw'])

                                # get a trefwoord number
                                sTwToel = oLine['trefwoord_toelichting']
                                if sTwToel == None or sTwToel == "":
                                    iPkTrefwoord = oFix.get_pk(oTrefwoord, "dictionary.trefwoord", True,
                                                               woord=sTrefWoord)
                                else:
                                    iPkTrefwoord = oFix.get_pk(oTrefwoord, "dictionary.trefwoord", True,
                                                               woord=sTrefWoord,
                                                               toelichting=sTwToel)
                                # Keep track of the time
                                oTime['db'] += get_now_time() - iStarttime
                            # Check validity
                            if iPkDescr < 0 or iPkLemma < 0 or iPkLemmaDescr < 0 or iPkDialect < 0 or iPkTrefwoord < 0:
                                # Something has gone wrong: we cannot continue
                                oStatus.set_status("error")
                                errHandle.DoError("csv_to_fixture has a negative index", True)
                                return oBack

                            # Process the ENTRY
                            sDialectWoord = oLine['dialectopgave_name']
                            # Make sure that I use my OWN continuous [pk] for Entry
                            iPkEntry += 1
                            # Do *NOT* use the Entry PK that is returned 
                            iStarttime = get_now_time()
                            iDummy = oFix.get_pk(oEntry, "dictionary.entry", False,
                                                   pk=iPkEntry,
                                                   woord=sDialectWoord,
                                                   toelichting=oLine['dialectopgave_toelichting'],
                                                   kloeketoelichting=oLine['dialectopgave_kloeketoelichting'],
                                                   lemma=iPkLemma,
                                                   descr=iPkDescr,     # This is the Description that in principle is valid for the whole lemma, but not in practice
                                                   dialect=iPkDialect,
                                                   trefwoord=iPkTrefwoord,
                                                   aflevering=iPkAflevering)
                            oTime['entry'] += get_now_time() - iStarttime

                            if bDoMijnen:
                                if bUseDbase and bUsdDbaseMijnen:
                                    # Walk all the mijnen for this entry
                                    for sMijn in lMijnen:
                                        # Get the PK for this mijn
                                        iPkMijn = Mijn.get_item({'naam': sMijn}, oTime)
                                        # Process the PK for EntryMijn
                                        iPkEntryMijn = EntryMijn.get_item({'entry': iPkEntry,
                                                                           'mijn': iPkMijn}, True)

                                else:
                                    # Walk all the mijnen for this entry
                                    for sMijn in lMijnen:
                                        # Get the PK for this mijn
                                        iPkMijn = oFix.get_pk(oMijn, "dictionary.mijn", True,
                                                              naam=sMijn)
                                        # Process the PK for EntryMijn
                                        iPkEntryMijn = oFix.get_pk(oEntryMijn, "dictionary.entrymijn", False,
                                                                   pk=iPkEntryMijn,
                                                                   entry=iPkEntry,
                                                                   mijn=iPkMijn)
                            iRead += 1
                        else:
                            # This line is being skipped
                            oSkip.append(strLine)
                            iSkipped += 1
                            sIdx = 'line-' + str(iValid)
                            if not sIdx in oBack:
                                oBack[sIdx] = 0
                            oBack[sIdx] +=1
                    # Keep track of progress
                    oStatus.skipped = iSkipped
                    oStatus.read = iRead
                    oStatus.status = "{} (read={:.1f}, db={:.1f}, entry={:.1f}, search (L={:.1f}, T={:.1f}, Ds={:.1f}, LD={:.1f}, Dt={:.1f}, M={:.1f}), save={:.1f})".format(
                        sWorking, oTime['read'], oTime['db'], oTime['entry'],
                        oTime['search_L'], oTime['search_T'], oTime['search_Ds'], oTime['search_LD'], oTime['search_Dt'], oTime['search_M'], oTime['save'])
                    oStatus.save()


                # CLose the input file
                f.close()

                # Close the skip file
                oSkip.close()

                # Finish the JSON array that contains the fixtures
                oFix.close()

                # Note the results for this info object
                oInfo.read = iRead
                oInfo.skipped = iSkipped
                oInfo.processed = "Processed at {:%d/%b/%Y %H:%M:%S}".format(datetime.now())
                oInfo.save()

        # return positively
        oBack['result'] = True
        oBack['skipped'] = iSkipped
        oBack['read'] = iRead
        # oCsvImport['status'] = 'done'
        oStatus.set_status("done")
        return oBack
    except:
        # oCsvImport['status'] = 'error'
        oStatus.status = "error"
        oStatus.save()
        errHandle.DoError("csv_to_fixture", True)
        return oBack


# ----------------------------------------------------------------------------------
# Name :    do_repair_lemma
# Goal :    Repair the lemma's
# History:
#  13/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def do_repair_lemma(oRepair):
    """Repair lemma stuff"""

    # Get all the lemma's
    qs = Lemma.objects.all()

    # Walk all the lemma's
    iStart = 0
    iLen = qs.count()
    iRepair = 0
    for oLem in qs:
        # Note progress
        iStart += 1
        bChange = False
        # Show where we are
        oRepair.status = "Working on {} (of {})".format(iStart,iLen)
        oRepair.save()
        # Remove spaces from lemma
        sGloss = oLem.gloss.strip()
        if sGloss != oLem.gloss:
            iRepair +=1
            oLem.gloss = sGloss
            bChange = True
        # Check for trailing and following quotation marks
        sGloss = oLem.gloss
        if sGloss.startswith('"') and sGloss.endswith('"'):
            oLem.gloss = sGloss.strip('"')
            iRepair += 1
            bChange = True
        sGloss = oLem.gloss
        if sGloss.startswith("'") and sGloss.endswith("'"):
            oLem.gloss = sGloss.strip("'")
            iRepair += 1
            bChange = True
        # Have any changes been made?
        if bChange:
            # save the changes
            oLem.save()
            oRepair.status = "Saved changes in {} (of {})".format(iStart,iLen)
            oRepair.save()

    # Return positively
    return True
