from flask import Flask, request, jsonify, render_template
import subprocess
import sys
from flask_socketio import SocketIO, emit
import kafka
import threading
import requests

app = Flask(__name__)
socketio = SocketIO(app)
process = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/script-status') # Endpoint per verificare lo stato del processo chat_listener
def get_script_status():
    if process is None:
        return jsonify(status=False)
    else:
        return jsonify(status=True)

@app.route('/update-channel', methods=['POST']) # Endpoint per aggiornare il canale nel file .env
def update_channel():
    new_channel = request.json['channel']
    with open('.env', 'r') as file:
        lines = file.readlines()
    with open('.env', 'w') as file:
        for line in lines:
            if line.startswith('CHANNEL='):
                file.write(f'CHANNEL={new_channel}\n')
            else:
                file.write(line)
    return jsonify(message='Canale aggiornato con successo!')

@app.route('/run-script') # Endpoint per avviare lo script chat_listener
def run_script():
    global process
    script_path = './chat_listener.py'
    
    try:
        # Esegui lo script in background
        if process is None:
            process = subprocess.Popen(['python', script_path])
            print(f'[WEB_INTERFACE] - Script path: {script_path}', flush=True)
            print(f'[WEB_INTERFACE] - Script avviato con PID: {process.pid}', flush=True)

            response = requests.get('http://host.docker.internal:12345/get_emotes') # Richiede al servizio emote_downloader di scaricare le emote relative al canale
            if response.status_code == 200:
                print('Emote ottenute con successo:', response.json())
            else:
                print('Errore nella richiesta delle emote:', response.status_code)

            return jsonify(message='Script avviato in background.'), 200
        else: 
            print('Script già in esecuzione', flush=True)
            return jsonify(message='Script già in esecuzione.'), 400
        
    except Exception as e:
        print('Errore durante l\'esecuzione del script:',str(e), flush=True)
        return jsonify(message=str(e)), 500
    
@app.route('/stop-script') # Endpoint per fermare lo script chat_listener
def stop_script():
    global process
    if process is not None:
        process.terminate()  
        process.wait()  
        process = None
        return jsonify(message='Script fermato'), 200
    else:
        return jsonify(message='Nessun script in esecuzione'), 400

@app.route('/env') # Endpoint per verificare il percorso del python interpreter
def show_env():
    python_path = sys.executable
    return f'The current Python interpreter is located at: {python_path}'

@socketio.on('connect')
def handle_connect():
    emit('status', {'message': 'Connected to WebSocket'})

def consume_messages(): # Funzione per consumare i messaggi dal servizio Kafka
    consumer = kafka.KafkaConsumer('enriched_chat', bootstrap_servers=['host.docker.internal:9092'])
    for message in consumer:
        socketio.emit('new_message', {'message': message.value.decode()})
        print(f'[CONSUMER] - {message.value.decode()}', flush=True)

if __name__ == '__main__':

    thread = threading.Thread(target=consume_messages) # Avvia il thread per consumare messaggi da Kafka
    thread.daemon = True  # Imposta il thread come daemon così si chiude con il programma
    thread.start()

    # Avvia il server Flask
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, host='0.0.0.0')

