#This script is responsible for actually sending the sms message to the emergency contact
import vonage 
from dotenv import load_dotenv
import os

# Load .env file from project root (parent of app directory)
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=env_path, override=True)
VONAGE_API_KEY = os.getenv("VONAGE_API_KEY") #API keys for vonage free sms service
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")

def send_sms(to_number,message):
   auth = vonage.Auth(api_key=VONAGE_API_KEY, api_secret=VONAGE_API_SECRET)
   client = vonage.Vonage(auth)
   
   try:
      response = client.sms.send({ #Sending messages
          "from_":"+15714678280", #vonage phone number don't change
         "to": f"+1{to_number}",
         "text": message
         })
      
      msg = response["messages"][0]
      status = msg["status"]

      if status == "0":
         return{
            "status": "success",
            "to": to_number
         }
      else:
         return{
            "status":"error",
            "error": msg.get("error-text", "Unknown error"),
            "to":to_number
         }
      
      
   except Exception as e:
      return{"status": "error", "error": str(e), "to": to_number}

   




