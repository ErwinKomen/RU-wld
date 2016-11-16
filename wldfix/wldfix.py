#! /usr/bin/env python3
# -*- coding: utf8 -*-
import sys
import getopt
import os.path
import io
import codecs
import json

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


# ----------------------------------------------------------------------------------
# Name :    main
# Goal :    Main body of the function
# History:
# 18/jun/2016    ERK Created
# ----------------------------------------------------------------------------------
def main(prgName, argv) :
    flInput = ''        # input file name
    flOutput = ''       # output file name
    sPart = ''          # The part we are supposed to process: 'entries' or 'afleveringen'
    oAflevering = {}    # Details of this aflevering

    try:
        # Adapt the program name to exclude the directory
        index = prgName.rfind("\\")
        if (index > 0) :
            prgName = prgName[index+1:]

        sSyntax = prgName + ' -p <part> -i <inputfile> -o <outputfile>'
        # get all the arguments
        try:
            # Get arguments and options
            opts, args = getopt.getopt(argv, "hp:i:o:d:s:a:", ["-part=","-inputfile=","-outputfile=","-deel=", "-sectie=", "-aflevering="])
        except getopt.GetoptError:
            print(sSyntax)
            sys.exit(2)

        # Initialise the aflevering details
        oAflevering['deel'] = ""
        oAflevering['sectie'] = ""
        oAflevering['aflevering'] = ""

        # Walk all the arguments
        for opt, arg in opts:
            if opt == '-h':
                print(sSyntax)
                sys.exit(0)
            elif opt in ("-i", "--inputfile"):
                flInput = arg
            elif opt in ("-o", "--outputfile"):
                flOutput = arg
            elif opt in ("-p", "--part"):
                sPart = arg
            elif opt in ("-d", "--deel"):
                oAflevering['deel'] = arg
            elif opt in ("-s", "--sectie"):
                oAflevering['sectie'] = arg
            elif opt in ("-a", "--aflevering"):
                oAflevering['aflevering'] = arg

        # Check if all arguments are there
        if (flInput == '' or flOutput == ''):
            errHandle.DoError(sSyntax)

        # Continue with the program
        errHandle.Status('Input is "' + flInput + '"')
        errHandle.Status('Output is "' + flOutput + '"')

        # Call the function that converts input into output
        if (wldfix(flInput, flOutput, sPart, oAflevering)) :
            errHandle.Status("Ready")
        else :
            errHandle.DoError("Could not complete")

        # return positively
        return True
    except:
        # act
        errHandle.DoError("main")
        return False


def findItem(arItem, sKeyField, sKeyValue):
    for it in arItem:
        if getattr(it, sKeyField) == sKeyValue:
            return getattr(it, 'pk')
    
    # getting here means we haven't found it
    return -1


class Lemma:
    """Lemma"""

    pk = 0     # Initialise PK

    def __init__(self, iPk, sName, sToelichting, sBronnen):
        self.name = sName
        self.toelichting = sToelichting
        self.bronnen = sBronnen
        self.pk = iPk


class Trefwoord:
    """Trefwoord"""

    def __init__(self, iPk, sWoord, sToelichting):
        self.woord = sWoord
        self.toelichting = sToelichting
        self.pk = iPk


class Dialect:
    """Dialect"""

    def __init__(self, iPk, sStad, sCode, sNieuw, sToelichting):
        self.stad = sStad
        self.code = sCode
        self.nieuw = sNieuw
        self.toelichting = sToelichting
        self.pk = iPk


class Deel:
    """Deel"""

    def __init__(self, iPk, sTitel, iNummer, sToelichting):
        self.titel = sTitel
        self.nummer = iNummer
        self.toelichting = sToelichting
        self.pk = iPk


class Aflevering:
    """Aflevering"""

    def __init__(self, iPk, sPdfNaam, iDeel, iSectie, iAflevering, iJaar, sToelichting):
        self.naam = sPdfNaam
        self.deel = iDeel
        if (iSectie != None):
            self.sectie = iSectie
        self.aflevering = iAflevering
        self.jaar = iJaar
        self.toelichting = sToelichting
        self.pk = iPk


class Mijn:
    """Mijn"""

    def __init__(self, iPk, sNaam, sLocatie, sToelichting):
        self.naam = sNaam
        self.locatie = sLocatie
        self.toelichting = sToelichting
        self.pk = iPk


class Entry:
    """Entry"""

    def __init__(self, iPk, iLemmaPk, iDialectPk, iTrefwoordPk, sWoord, sToelichting):
        self.lemma = iLemmaPk
        self.dialect = iDialectPk
        self.trefwoord = iTrefwoordPk
        self.woord = sWoord
        self.toelichting = sToelichting
        self.pk = iPk


# ----------------------------------------------------------------------------------
# Name :    wldfix
# Goal :    Create fixtures for the collection bank
# History:
# 18/jun/2016   ERK Created
# 16/nov/2016   ERK Added [sPart] and [oAflevering] arguments
# ----------------------------------------------------------------------------------
def wldfix(csv_file, output_file, sPart, oAflevering):
    try:
        # Validate: input file exists
        if (not os.path.isfile(csv_file)): return False

        # Start creating an array that will hold the fixture elements
        arFixture = []
        iPkLemma = 1        # The PK for each Lemma
        iPkTrefw = 1        # The PK for each Trefwoord
        iPkDialect = 1      # The PK for each Dialect
        iPkEntry = 1        # The PK for each Entry
        iPkAfl = 1          # The PK for each Aflevering
        iPkDeel = 1         # The PK for each Deel
        lstDeel = []        # List of deel afleveringen
        lstLemma = []       # List of lemma entries
        lstTrefw = []       # List of trefwoord entries
        lstDialect = []     # list of dialect entries
        lstMijn = []        # List of mijn entries
        lstAflevering = []  # List of aflevering entries
        lstEntry = []       # List of dictionary entries

        # Open source file to read line-by-line
        f = codecs.open(csv_file, "r", encoding='utf-8-sig')
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
                if (not bFirst):
                    # Determine what part we are processing
                    if sPart == "aflevering":
                        # Process this line of aflevering-details
                        #   0  - PDF name    (string)
                        #   1  - deel        (int)
                        #   2  - sectie      (int, optional)
                        #   3  - aflnum      (int)
                        #   4  - jaar        (int)
                        #   5  - auteurs     (string)
                        #   6  - afltitel    (string)
                        #   7  - sectietitel (string)
                        #   8  - plaats      (string)
                        #   9  - toelichting (string)
                        #  10  - deeltitel   (string)

                        # Determine the Sectie
                        iSectie = arPart[2]
                        if iSectie == "":
                            iSectie = None

                        # get a 'deel' identifier
                        iPkDeel = findItem(lstDeel, 'titel', arPart[10])
                        if (iPkDeel<0):
                            iPkDeel = len(lstDeel)+1
                            newItem = Deel(iPkDeel, arPart[10], arPart[1], "")
                            lstDeel.append(newItem)

                            # Add this dialect to the fixtures
                            oFields = {"titel":         newItem.titel,
                                       "nummer":        newItem.nummer,
                                       "toelichting":   newItem.toelichting}
                            oDeel = {"model": "dictionary.deel", 
                                      "pk": iPkDeel, "fields": oFields}
                            arFixture.append(oDeel)

                        # Add the whole aflevering to the fixtures
                        oFields = {"naam":        arPart[0],
                                   "deel":        arPart[1],
                                   "sectie":      iSectie,
                                   "aflnum":      arPart[3],
                                   "jaar":        arPart[4],
                                   "auteurs":     arPart[5],
                                   "afltitel":    arPart[6],
                                   "sectietitel": arPart[7],
                                   "plaats":      arPart[8],
                                   "toelichting": arPart[9],
                                   "deel":        iPkDeel}
                        # Process this aflevering
                        oAflevering = {"model": "dictionary.aflevering", 
                                  "pk": iPkAfl, "fields": oFields}
                        arFixture.append(oAflevering)

                        # Make sure PK is incremented
                        iPkAfl += 1
                    else:
                        # Assuming this 'part' is entering an ENTRY
                        # Get a lemma number from this
                        iPkLemma = findItem(lstLemma, 'name', arPart[0])
                        if (iPkLemma<0):

                            # Create a new lemma entry
                            iPkLemma = len(lstLemma)+1
                            newItem = Lemma(iPkLemma, arPart[0], arPart[1], arPart[2])
                            lstLemma.append(newItem)

                            # Add this lemma to the fixtures
                            oFields = {"gloss":         newItem.name,
                                       "toelichting":   newItem.toelichting,
                                       "bronnenlijst":  newItem.bronnen}
                            oEntry = {"model": "dictionary.lemma", 
                                      "pk": iPkLemma, "fields": oFields}
                            arFixture.append(oEntry)

                        # get a dialect number
                        iPkDialect = findItem(lstDialect, 'code', arPart[7])
                        if (iPkDialect<0):
                            iPkDialect = len(lstDialect)+1
                            newItem = Dialect(iPkDialect, arPart[9], arPart[7], arPart[8], arPart[10])
                            lstDialect.append(newItem)

                            # Add this dialect to the fixtures
                            oFields = {"stad":          newItem.stad,
                                       "nieuw":         newItem.nieuw,
                                       "toelichting":   newItem.toelichting,
                                       "code":          newItem.code}
                            oEntry = {"model": "dictionary.dialect", 
                                      "pk": iPkDialect, "fields": oFields}
                            arFixture.append(oEntry)

                        # Get a trefwoord number
                        iPkTrefw = findItem(lstTrefw, 'woord', arPart[3])
                        if (iPkTrefw<0):
                            iPkTrefw = len(lstTrefw)+1
                            newItem = Trefwoord(iPkTrefw, arPart[3], arPart[4])
                            lstTrefw.append(newItem)

                            # Add this trefwoord to the fixtures
                            oFields = {"woord":         newItem.woord,
                                       "toelichting":   newItem.toelichting}
                            oEntry = {"model": "dictionary.trefwoord", 
                                      "pk": iPkTrefw, "fields": oFields}
                            arFixture.append(oEntry)
                    

                        # Add the whole entry to the fixtures
                        oFields = {"lemma":         iPkLemma,
                                   "dialect":       iPkDialect,
                                   "trefwoord":     iPkTrefw,
                                   "woord":         arPart[5],
                                   "toelichting":   arPart[6]}
                        oEntry = {"model": "dictionary.entry", 
                                  "pk": iPkEntry, "fields": oFields}
                        arFixture.append(oEntry)

                        # Make sure PK is incremented
                        iPkEntry += 1
                else:
                    # Indicate that the first item has been had
                    bFirst = False


        # CLose the input file
        f.close()

        # COnvert the array into a json string
        sJson = json.dumps(arFixture, indent=2)

        # Save the string to the output file
        fl_out = io.open(output_file, "w", encoding='utf-8')
        fl_out.write(sJson)
        fl_out.close()

        # return positively
        return True
    except:
        errHandle.DoError("wldfix")
        return False


# ----------------------------------------------------------------------------------
# Goal :  If user calls this as main, then follow up on it
# History:
# 18/jun/2016    ERK Created
# ----------------------------------------------------------------------------------
if __name__ == "__main__":
  # Call the main function with two arguments: program name + remainder
  main(sys.argv[0], sys.argv[1:])