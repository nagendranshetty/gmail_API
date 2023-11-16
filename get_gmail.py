import pickle
import os.path
from apiclient import errors
import email
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def search_message(service, user_id, search_string):
    """
    Search the inbox for emails using standard gmail search parameters
    and return a list of email IDs for each result

    PARAMS:
        service: the google api service object already instantiated
        user_id: user id for google api service ('me' works here if
        already authenticated)
        search_string: search operators you can use with Gmail
        (see https://support.google.com/mail/answer/7190?hl=en for a list)

    RETURNS:
        List containing email IDs of search query
    """
    try:
        # initiate the list for returning
        list_ids = []

        # get the id of all messages that are in the search string
        search_ids = service.users().messages().list(userId=user_id, q=search_string).execute()
        
        # if there were no results, print warning and return empty string
        try:
            ids = search_ids['messages']

        except KeyError:
            print("WARNING: the search queried returned 0 results")
            print("returning an empty string")
            return ""

        if len(ids)>1:
            for msg_id in ids:
                list_ids.append(msg_id['id'])
            return(list_ids)

        else:
            list_ids.append(ids['id'])
            return list_ids
        
    except (errors.HttpError):
        print("An error occured: %s")


def get_message(service, user_id, msg_id):
    """
    Search the inbox for specific message by ID and return it back as a 
    clean string. String may contain Python escape characters for newline
    and return line. 
    
    PARAMS
        service: the google api service object already instantiated
        user_id: user id for google api service ('me' works here if
        already authenticated)
        msg_id: the unique id of the email you need

    RETURNS
        A string of encoded text containing the message body
    """
    try:
        # grab the message instance
        message = service.users().messages().get(userId=user_id, id=msg_id,format='raw').execute()

        # decode the raw string, ASCII works pretty well here
        msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

        # grab the string from the byte object
        mime_msg = email.message_from_bytes(msg_str)

        # check if the content is multipart (it usually is)
        content_type = mime_msg.get_content_maintype()
        if content_type == 'multipart':
            # there will usually be 2 parts the first will be the body in text
            # the second will be the text in html
            parts = mime_msg.get_payload()

            # return the encoded text
            final_content = parts[0].get_payload()
            return final_content

        elif content_type == 'text':
            return mime_msg.get_payload()

        else:
            return ""
            print("\nMessage is not text or multipart, returned an empty string")
    # unsure why the usual exception doesn't work in this case, but 
    # having a standard Exception seems to do the trick
    except Exception:
        print("An error occured: %s")


def get_service():
    """
    Authenticate the google api client and return the service object 
    to make further calls

    PARAMS
        None

    RETURNS
        service api object from gmail for making calls
    """
    creds = None

    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)


    service = build('gmail', 'v1', credentials=creds)

    return service


def readEmails(service, user_id):
    """
    Search the latest unread main from inbox and return href https link 
    
    PARAMS
        service: the google api service object already instantiated
        user_id: user id for google api service ('me' works here if
        already authenticated)

    RETURNS
        A string of href https link
    """    
    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
        messages = results.get('messages',[]);
        if not messages:
            print('No new messages.')
        else:
            message_count = 0
            for message in messages:
                msg = service.users().messages().get(userId=user_id, id=message['id']).execute()                
                email_data = msg['payload']['headers']
                for values in email_data:
                    name = values['name']
                    if name == 'From':
                        from_name= values['value']
                        for part in msg['payload']['parts']:
                            try:
                                data = part['body']["data"]
                                byte_code = base64.urlsafe_b64decode(data)

                                text = byte_code.decode("utf-8")
                                print ("This is the message: "+ str(text))

                                import AdvancedHTMLParser
                                parser = AdvancedHTMLParser.AdvancedHTMLParser()
                                parser.parseStr(text)

                                link_items = parser.getElementsByTagName('a')
                                from googletrans import Translator
                                translator = Translator()

                                for item in link_items:
                                    attributes = dict((item._attributes))
                                    translate_text = ''
                                    if item.innerText is not None:
                                        try:
                                            txt = item.innerText
                                            if txt == ' ':
                                                continue
                                            if 'google.com' in txt.strip().lower():
                                                translate_text = txt
                                            else:
                                                translate_text = translator.translate(txt, dest='en')                                            
                                        except:
                                            pass
                                        if 'google.com' in translate_text.strip().lower():
                                            return attributes['href']
                                            break
                                parser.close()

                                # mark the message as read (optional)
                                msg  = service.users().messages().modify(userId=user_id, id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
                            except BaseException as error:
                                pass
                if message:
                    break
    except Exception as error:
        print(f'An error occurred: {error}')

if __name__ == "__main__":
  
    # Get gmail service
    service = get_service()

    latestEmailHref = readEmails(service=service, user_id='me')

    print('Verification link: ', latestEmailHref)


#   search_message_id = search_message(service=service, user_id='me', search_string='myself')

#   print(search_message_id)

#   message = get_message(service=service, user_id='me', msg_id=search_message_id)
#   print(message)

#   for id in search_message_id:
#     message = get_message(service=service, user_id='me', msg_id=id)
#     print(message)