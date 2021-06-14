import sys
from django.conf import settings
from django import http

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
        sNewMsg = self.get_error_message()
        self.loc_errStack.append(sNewMsg)
        # Is this a fatal error that requires exiting?
        if (bExit):
            sys.exit(2)
        # Otherwise: return the string that has been made
        return "<br>".join(self.loc_errStack)


    def get_error_message(self):
        arInfo = sys.exc_info()
        if len(arInfo) == 3:
            sMsg = str(arInfo[1])
            if arInfo[2] != None:
                sMsg += " at line " + str(arInfo[2].tb_lineno)
            return sMsg
        else:
            return ""


class BlockedIpMiddleware(object):

    bot_list = ['bot.htm', '/petalbot', 'crawler.com' ]

    def process_request(self, request):
        if request.META['REMOTE_ADDR'] in settings.BLOCKED_IPS:
            return http.HttpResponseForbidden('<h1>Forbidden</h1>')
        else:
            # Get the user agent
            user_agent = request.META.get('HTTP_USER_AGENT')
            if user_agent == None or user_agent == "":
                # This is forbidden...
                return http.HttpResponseForbidden('<h1>Forbidden</h1>')
            else:
                # Check what the user agent is...
                user_agent = user_agent.lower()
                for bot in self.bot_list:
                    if bot in user_agent:
                        ip = request.META.get('REMOTE_ADDR')
                        # Print it for logging
                        msg = "blocking bot: [{}] {}: {}".format(ip, bot, user_agent)
                        print(msg, file=sys.stderr)
                        return http.HttpResponseForbidden('<h1>Forbidden</h1>')
        return None
