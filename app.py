import os
import json
import threading
import time
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

AUCTION_TIME = 20
PLAYERS_FILE = 'players.json'
players_queue = []
current_item = None
timer_thread = None
auction_lock = threading.Lock()
bid_history = []

# Load saved players
if os.path.exists(PLAYERS_FILE):
    try:
        with open(PLAYERS_FILE, 'r') as f:
            players_queue = json.load(f)
    except json.JSONDecodeError:
        players_queue = []
else:
    players_queue = []


def save_players():
    global players_queue, current_item
    to_save = players_queue.copy()
    if current_item:
        to_save = [current_item] + to_save
    with open(PLAYERS_FILE, 'w') as f:
        json.dump(to_save, f, indent=4)

def start_timer():
    global current_item
    time_left = AUCTION_TIME
    while time_left > 0 and current_item["status"] == "In Auction":
        socketio.emit('timer', {"time": time_left}, broadcast=True)
        time.sleep(1)
        time_left -= 1
    with auction_lock:
        if current_item["status"] == "In Auction":
            current_item["status"] = "UNSOLD ❌"
            save_players()
            socketio.emit('update', current_item, broadcast=True)
            start_next_player()

def start_next_player():
    global current_item, timer_thread, bid_history
    bid_history = []
    if players_queue:
        current_item = players_queue.pop(0)
        current_item["current_bid"] = current_item["base_price"]
        current_item["status"] = "In Auction"
        current_item["team"] = ""
        save_players()
        socketio.emit('update', current_item, broadcast=True)
        timer_thread = threading.Thread(target=start_timer)
        timer_thread.start()
    else:
        current_item = None
        socketio.emit('update', {"name":"Auction Finished","status":"--"}, broadcast=True)

@app.route('/admin')
def admin():
    return render_template('admin.html', queue_len=len(players_queue), current_item=current_item)

@app.route('/')
def display():
    return render_template('display.html', item=current_item, bid_history=bid_history)

@app.route('/upload', methods=['POST'])
def upload():
    global players_queue
    name = request.form['name']
    category = request.form['category']
    base_price = int(request.form['base_price'])
    stats = {
        "Matches": request.form['matches'],
        "Runs": request.form['runs'],
        "Average": request.form['avg'],
        "Strike Rate": request.form['sr'],
        "Wickets": request.form['wickets'],
        "Economy": request.form['econ']
    }

    player = {
        "name": name,
        "category": category,
        "base_price": base_price,
        "current_bid": base_price,
        "status": "Waiting",
        "stats": stats,
        "image": None,
        "team_logo": None,
        "team": ""
    }

    if 'image' in request.files:
        img = request.files['image']
        if img.filename != "":
            filename = secure_filename(img.filename)
            img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            player['image'] = filename

    if 'team_logo' in request.files:
        logo = request.files['team_logo']
        if logo.filename != "":
            filename = secure_filename(logo.filename)
            logo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            player['team_logo'] = filename

    players_queue.append(player)
    save_players()

    with auction_lock:
        if current_item is None:
            start_next_player()

    return redirect(url_for('admin'))

@app.route('/bid', methods=['POST'])
def bid():
    global current_item, bid_history
    increment = int(request.form['increment'])
    current_item["current_bid"] += increment
    bid_history.append(f"+{increment} L")
    save_players()
    socketio.emit('update', current_item, broadcast=True)
    socketio.emit('bid_history', bid_history, broadcast=True)
    return redirect(url_for('admin'))

@app.route('/status', methods=['POST'])
def status():
    global current_item
    action = request.form['action']
    team_name = request.form.get('team_name', '')
    current_item["team"] = team_name
    if action=="sold":
        current_item["status"] = "SOLD ✅"
    else:
        current_item["status"] = "UNSOLD ❌"
    save_players()
    socketio.emit('update', current_item, broadcast=True)
    start_next_player()
    return redirect(url_for('admin'))

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
