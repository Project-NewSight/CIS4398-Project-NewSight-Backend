import vonage
from dotenv import load_dotenv
import os

load_dotenv()

VONAGE_API_KEY = os.getenv("VONAGE_API_KEY")
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")

def send_sms(to_number,message):
   auth = vonage.Auth(api_key=VONAGE_API_KEY, api_secret=VONAGE_API_SECRET)
   client = vonage.Vonage(auth)
   
   response = client.sms.send({
       "from_":"+16033338616", 
       "to": to_number,
       "text": message
       })
   
   for msg in response.messages:
      if msg.status == "0":
         print("Message sent sucessfully")
      else:
         print("Failed to send message")
     


send_sms("+4012888347", "The Generator VJ Edgecomb is the goat")



