"""Converting CSV files into fixtures.

Code that reads one or more CSV files (tab-separated) and converts them into
a fixture file. This file can then be manually read into the database on the server.

"""
import sys
# import getopt
import os.path
import io
import codecs
import json
from wld.dictionary.models import *
from wld import settings

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


# ============================= LOCAL VARIABLES ====================================
errHandle =  ErrHandle()

# ============================= Fixture Database Classes ===========================
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

    def append(self, sModel, iPk, oFields):
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

    def get_pk(self, oCls, sModel, **oFields):
        # Look for this item in the list that we have
        iPkItem = findItem(oCls.lstItem, **oFields)
        if iPkItem < 0:
            # it is not in the list: add it
            iPkItem = len(oCls.lstItem)+1
            newItem = oCls(iPkItem, **oFields)
            oCls.lstItem.append(newItem)
            # Add the item to the output
            self.append(sModel, iPkItem, **oFields)

        # Return the pK
        return iPkItem
    

def get_pk(self, oFix, oClass, sModel, **oFields):
    # Look for this item in the list that we have
    iPkItem = findItem(oFix.lstItem, **oFields)
    if iPkItem < 0:
        # it is not in the list: add it
        iPkItem = len(oFix.lstItem)+1
        newItem = oClass(iPkItem, **oFields)
        oFix.lstItem.append(newItem)
        # Add the item to the output
        oFix.append(sModel, iPkItem, **oFields)

    # Return the pK
    return iPkItem


class fLemma:
    """Lemma information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known lemma's

    def __init__(self, iPk, **kwargs):
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        self.pk = iPk

    def __init__(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                a=1



class fDialect:
    """Dialect information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def __init__(self, iPk, **kwargs):
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        self.pk = iPk

    def __init__(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                a=1


class fTrefwoord:
    """Trefwoord information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def __init__(self, iPk, **kwargs):
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        self.pk = iPk


class fAflevering:
    """Aflevering information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def __init__(self, iPk, **kwargs):
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        self.pk = iPk


class fEntry:
    """Entry information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def __init__(self, iPk, **kwargs):
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        self.pk = iPk


# ----------------------------------------------------------------------------------
# Name :    csv_to_fixture
# Goal :    Convert CSV file into a fixtures file
# History:
#  1/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def csv_to_fixture(csv_file, iDeel, iSectie, iAflevering):
    """Process a CSV with entry definitions"""

    try:
        # Validate: input file exists
        if (not os.path.isfile(csv_file)): return False

        # Start creating an array that will hold the fixture elements
        arFixture = []
        iPkLemma = 1        # The PK for each Lemma
        iPkTrefwoord = 1    # The PK for each Trefwoord
        iPkDialect = 1      # The PK for each Dialect
        iPkEntry = 1        # The PK for each Entry
        iPkAflevering = 1   # The PK for each Aflevering

        # Create an output file writer
        output_file = os.path.join(settings.MEDIA_ROOT ,os.path.splitext(os.path.basename(csv_file))[0] + ".json")
        oFix = FixOut(output_file)

        # Create instances of the Lemma, Dialect and other classes
        qs = Lemma.objects.none()
        oLemma = fLemma(Lemma.objects.none())
        oDialect = fDialect(Dialect.objects.all())
        oTrefwoord = fTrefwoord(Trefwoord.objects.none())
        oAflevering = fAflevering(Aflevering.objects.all())
        oEntry = fEntry(Entry.objects.none())

        # Open source file to read line-by-line
        f = codecs.open(csv_file, "r", encoding='utf-8-sig')
        bEnd = False
        bFirst = True
        bFirstOut = False
        while (not bEnd):
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
                # IF this is the first line or an empty line, then skip
                if bFirst:
                    # Check if the line starts correctly
                    if arPart[0] != 'Lemmanummer':
                        # The first line does not start correctly -- return false
                        return False
                    # Indicate that the first item has been had
                    bFirst = False
                else:
                    # Assuming this 'part' is entering an ENTRY
                    # Get a lemma number from this
                    iPkLemma = oFix.get_pk(oLemma, "dictionary.lemma",
                                           gloss=arPart[1], 
                                           bronnenlijst=arPart[6], 
                                           boek=arPart[7])

                    # get a dialect number
                    iPkDialect = oFix.get_pk(oDialect, "dictionary.dialect",
                                             stad=arPart[10], 
                                             nieuw=arPart[15])

                    # get a trefwoord number
                    iPkTrefwoord = oFix.get_pk(oTrefwoord, "dictionary.trefwoord",
                                               woord=arPart[3])

                    # get a Aflevering number
                    iPkAflevering = oFix.get_pk(oAflevering, "dictionary.aflevering",
                                                deel=iDeel,
                                                sectie=iSectie,
                                                aflnum = iAflevering)

                    # Process the ENTRY
                    sDialectWoord = arPart[5]
                    sDialectWoord = html.unescape(sDialectWoord).strip('"')
                    iPkEntry = oFix.get_pk(oEntry, "dictionary.entry",
                                           woord=sDialectWoord,
                                           toelichting=arPart[14],
                                           lemma=iPkLemma,
                                           dialect=iPkDialect,
                                           trefwoord=iPkTrefwoord,
                                           aflevering=iPkAflevering)


        # CLose the input file
        f.close()

        # Finish the JSON array that contains the fixtures
        oFix.close()

        # return positively
        return True
    except:
        errHandle.DoError("csv_to_fixture")
        return False

