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

    try:
        # Adapt the program name to exclude the directory
        index = prgName.rfind("\\")
        if (index > 0) :
            prgName = prgName[index+1:]

        sSyntax = prgName + ' -i <inputfile>'
        # get all the arguments
        try:
            # Get arguments and options
            opts, args = getopt.getopt(argv, "hi:", ["-inputfile="])
        except getopt.GetoptError:
            print(sSyntax)
            sys.exit(2)

        # Walk all the arguments
        for opt, arg in opts:
            if opt == '-h':
                print(sSyntax)
                sys.exit(0)
            elif opt in ("-i", "--inputfile"):
                flInput = arg

        # Check if all arguments are there
        if (flInput == ''):
            errHandle.DoError(sSyntax)

        # Continue with the program
        errHandle.Status('Input is "' + flInput + '"')

        # Call the function that converts input into output
        if (not wldfixscan(flInput)) :
            errHandle.DoError("Could not complete")

        # return positively
        return True
    except:
        # act
        errHandle.DoError("main")
        return False


def needed(oStatus):
    # Do we actually need to do anything?
    iNeeded = 0
    for (k,v) in oStatus.items():
        if v == 0:
            # Count the number of needs
            iNeeded += 1
    return iNeeded


def parse_object(oStatus, arData):
    # Do we actually need to do anything?
    iNeeded = needed(oStatus)
    # Is anything still needed?
    if iNeeded > 0:
        # Convert the data into a JSON object
        oData = json.loads(''.join(arData))
        # Get the model name
        sModel = oData['model']
        # Check if this is the one we need
        for (k,v) in oStatus.items():
            if v == 0 and sModel == k:
                # Get the PK value
                oStatus[k] = oData['pk']

    # Return the adapted status
    return oStatus

def repair_entry(arData):
    # Convert the data into a JSON object
    oData = json.loads(''.join(arData))
    # Repair the entry count
    oFields = oData['fields']
    if 'entry' in oFields:
        oFields['entry'] = oFields['entry'] + 1
        oData['fields'] = oFields

    # Return the adapted array
    return json.dumps(oData,indent=2)
    

# ----------------------------------------------------------------------------------
# Name :    wldfixscan
# Goal :    Scan JSON fixture file
# History:
# 15/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def wldfixscan(csv_file):
    flOutput = csv_file + ".out"       # output file name

    try:
        # Open source file to read line-by-line
        f = codecs.open(csv_file, "r", encoding='utf-8-sig')
        oStatus = {"dictionary.lemma": 0, 
                   "dictionary.description": 0,
                   "dictionary.lemmadescr": 0,
                   "dictionary.entry": 0,
                   "dictionary.dialect": 0,
                   "dictionary.trefwoord": 0}
        # Save the string to the output file
        fl_out = io.open(flOutput, "w", encoding='utf-8')
        fl_out.write('')
        fl_out.close()
        # Open the output file for appending
        fl_out = io.open(flOutput, "a", encoding='utf-8')

        bEnd = False
        bFirst = True
        arJson = []
        while (not bEnd):
            # Read one line
            strLine = f.readline()
            if (strLine == ""):
                # Get out of the loop
                break
            strLine = str(strLine.strip())
            # Action depends on which line we are getting
            if strLine == "[{":
                #This is the start of the whole file
                arJson.clear()
                arJson.append("{")
                # Copy input to output
                fl_out.write("[\n")
            elif strLine == "},{":
                # Finish one object, start another
                arJson.append("}")
                # Process what is inside [arJson]
                oStatus = parse_object(oStatus, arJson)
                # output what is needed
                fl_out.write(repair_entry(arJson) + ",")
                # Check if we need to continue
                if needed(oStatus) == 0: bEnd = True
                # Continue
                arJson.clear()
                arJson.append("{")

                # PATCH: continue until the file ends
                bEnd = False
            elif strLine == "}]":
                # Finish one object, start another
                arJson.append("}")
                # Process what is inside [arJson]
                oStatus = parse_object(oStatus, arJson)
                # output what is needed
                fl_out.write(repair_entry(arJson) + "]\n")
                # Check if we need to continue
                if needed(oStatus) == 0: bEnd = True

                # PATCH: continue until the file ends
                bEnd = False
            else:
                # Just add this line
                arJson.append(strLine)
 

        # CLose the input file
        f.close()

        # Close the output file
        fl_out.close()

        # Output the results
        sMsg = "{}\t{}\t{}\t{}\t{}\t{}\n".format(
            oStatus['dictionary.lemma'],
            oStatus['dictionary.description'],
            oStatus['dictionary.lemmadescr'],
            oStatus['dictionary.trefwoord'],
            oStatus['dictionary.entry'],
            oStatus['dictionary.dialect'],
            )
        print(sMsg)

        # return positively
        return True
    except:
        errHandle.DoError("wldfixscan")
        return False


# ----------------------------------------------------------------------------------
# Goal :  If user calls this as main, then follow up on it
# History:
# 18/jun/2016    ERK Created
# ----------------------------------------------------------------------------------
if __name__ == "__main__":
  # Call the main function with two arguments: program name + remainder
  main(sys.argv[0], sys.argv[1:])