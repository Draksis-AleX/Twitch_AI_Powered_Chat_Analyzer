import requests
import os
import dotenv
import json
import time
from flask import Flask, jsonify

emotes_list = []

def get_channel_id(nome_canale, client_id, client_secret):
    # Ottieni il token di accesso
    url_token = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    token_response = requests.post(url_token, params=params)
    access_token = token_response.json().get('access_token')

    if access_token:
        # Effettua la richiesta all'API di Twitch per ottenere l'ID del canale
        url_api = 'https://api.twitch.tv/helix/users'
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}'
        }
        params = {'login': nome_canale}
        response = requests.get(url_api, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()['data']
            if data:
                return data[0]['id']  # Restituisce l'ID del canale
            else:
                return "Canale non trovato."
        else:
            return "Errore nella richiesta API."
    else:
        return "Errore nell'ottenimento del token."

def get_7tv_emotes(channel_id):
    url = f"https://7tv.io/v3/users/twitch/{channel_id}"
    print(f'Downloading 7TV Emotes for {channel_id}...\n')
    
    response = requests.get(url)
    if response.status_code == 200:
        emotes = response.json()['emote_set']['emotes']

        for emote in emotes:
            emotes_list.append(emote['name']) 
        
    else:
        print("Errore nella richiesta delle emote 7TV")

def get_twitch_emotes(channel_id, client_id, client_secret):
    url_token = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    token_response = requests.post(url_token, params=params)
    access_token = token_response.json().get('access_token')

    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }

    url = f"https://api.twitch.tv/helix/chat/emotes?broadcaster_id={channel_id}" # Channel relative emotes --------------------------
    print(f'Downloading Twitch Emotes for {channel_id}...\n')

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        emote_data = response.json()['data']
        for emote in emote_data:
            emotes_list.append(emote['name'])

    url = f"https://api.twitch.tv/helix/chat/emotes/global" # Global emotes -----------------------------------------------
    print(f'Downloading Global Twitch Emotes ...\n')

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        emote_data = response.json()['data']
        for emote in emote_data:
            emotes_list.append(emote['name'])

    else:
        print("Errore nella richiesta delle emote Twitch:", response.content)

app = Flask(__name__)

@app.route('/')
def home():
    return "Benvenuto all'endpoint!"

@app.route('/get_emotes')
def get_emotes():

    emotes_list.clear()

    dotenv_file = dotenv.find_dotenv('.env')
    dotenv.load_dotenv(dotenv_file, override=True)
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('SECRET')
    nome_canale = os.getenv('CHANNEL')
    print(nome_canale, client_id, client_secret)

    channel_id = get_channel_id(nome_canale, client_id, client_secret)

    get_twitch_emotes(channel_id, client_id, client_secret)
    get_7tv_emotes(channel_id)
    print('Done!', emotes_list, flush=True)

    with open('emotes.json', 'w') as file:
        json.dump(emotes_list, file, indent=4) # Dump on file

    print('Emotes wrote on file "emotes.json"', flush=True)

    return jsonify(emotes_list), 200




#====================================================================================================

def getEmotes():

    dotenv_file = dotenv.find_dotenv('.env')
    dotenv.load_dotenv(dotenv_file)
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('SECRET')
    nome_canale = os.getenv('CHANNEL')
    print(nome_canale, client_id, client_secret)

    channel_id = get_channel_id(nome_canale, client_id, client_secret)

    get_twitch_emotes(channel_id, client_id)
    get_7tv_emotes(channel_id)
    print('Done!', emotes_list)

    with open('emotes.json', 'a') as file:
        json.dump(emotes_list, file, indent=4) # Dump on file

    print('Emotes wrote on file "emotes.json"')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12345)

