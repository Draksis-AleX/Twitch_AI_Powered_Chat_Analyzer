import os
import json
import datetime
import sys
import traceback
import locale
import requests
import dotenv
import aiohttp
from dotenv import load_dotenv
from twitchio.ext import commands

class Bot(commands.Bot):

    def __init__(self):
        load_dotenv(override=True) # Ricarica le variabili d'ambiente

        # Riempi la lista channels con i canali specificati come argomenti della riga di comando, se presenti, altrimenti usa il canale specificato nell'ambiente
        channels = []
        if len(sys.argv) > 1:
            for i in range(1,len(sys.argv)):
                channels.append(sys.argv[i])
        else:
            channels = [os.getenv('CHANNEL')]

        print("Listening following channels: ", channels, flush=True)
        super().__init__(token=os.getenv('ACCESS_TOKEN'), prefix=os.getenv('BOT_PREFIX'), initial_channels=channels)

    async def event_ready(self):
        print(f'Logged in as | {self.nick}', flush=True)
        print(f'User id is | {self.user_id}', flush=True)

    async def event_message(self, message):
        #if message.echo:
        #    return

        # Definisco il messaggio
        msg = { "channel" : message.channel.name,
                "timestamp" : message.timestamp.strftime('%d-%m-%Y %H:%M:%S'),
                "chatter_name" : message.author.display_name,
                "is_broadcaster" : message.author.is_broadcaster,
                "is_mod" : message.author.is_mod,
                "is_subscriber" : message.author.is_subscriber,
                "is_vip" : message.author.is_vip,
                "content" : message.content
                }

        print(msg, flush=True)
        
        try:
            # Invia il messaggio al servizio di ingestion (logstash)
            async with aiohttp.ClientSession() as session:
                async with session.post(os.getenv('INGESTOR_URL'), json=msg) as response:
                    response_text = await response.text()
                    print(f"Sent msg to '{os.getenv('INGESTOR_URL')}', RESPONSE = {response_text}", flush=True)
        
        except Exception as e:
            print(f"An error occurred: {e}", flush=True)
            traceback.print_exc()

        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)

    async def event_error(self, error, data):
        if isinstance(error, Exception):
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        print(f"Data received with error: {data}", file=sys.stderr)

def getToken():
    load_dotenv(override=True)

    #Ottieni o aggiorna il token per leggere la chat
    url = 'https://id.twitch.tv/oauth2/token'
    header = {'Content-Type' : 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'refresh_token',
            'refresh_token': os.getenv('REFRESH_TOKEN'),
            'client_id': os.getenv('CLIENT_ID'),
            'client_secret': os.getenv('SECRET')}

    response = requests.post(url, data=data, headers=header)

    if response.status_code == 200:
        res = response.json()

        print("Success:", response.text, flush=True)
        print("Access Token : ", res['access_token'], flush=True)
        print("Refresh Token : ", res['refresh_token'], flush=True)

        dotenv.set_key(dotenv_file, "ACCESS_TOKEN", res['access_token'])
        dotenv.set_key(dotenv_file, "REFRESH_TOKEN", res['refresh_token'])

        print("[OK] Refreshed token...", flush=True)
        return 1
    else:
        print("Error:", response.status_code, response.text, flush=True)
        return 0
    
def main():
    print(sys.executable, flush=True)
    bot = Bot()
    bot.run()   
    
if __name__ == "__main__":
    dotenv_file = dotenv.find_dotenv('.env')
    dotenv.load_dotenv(dotenv_file)
    if getToken():
        main()
