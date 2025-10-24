#This script is responsible for actually sending the sms message to the emergency contact
import vonage 
from dotenv import load_dotenv
import os

load_dotenv()
VONAGE_API_KEY = os.getenv("VONAGE_API_KEY") #API keys for vonage free sms service
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")

def send_sms(to_number,message):
   auth = vonage.Auth(api_key=VONAGE_API_KEY, api_secret=VONAGE_API_SECRET)
   client = vonage.Vonage(auth)
   
   response = client.sms.send({ #Sending messages
       "from_":"+16033338616", #vonage phone number don't change
       "to": f"+1{to_number}",
       "text": message
       })
   
   for msg in response.messages: #checking for sucessfull send
      if msg.status == "0":
         print("Message sent sucessfully")
      else:
         print("Failed to send message")



