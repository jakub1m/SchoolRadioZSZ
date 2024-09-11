from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import os
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

ToDo = ToDoNow = "Pass"

PASSWORD_AIMP = ""
PASSWORD_LOGS = ""
LOG_FILE_PATH = ""
SONGS_URL = ""

@app.route('/')
def index():
    """
    Render the index page.
    
    Returns:
        str: The rendered HTML template for the index page.
    """
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    """
    Handle login redirection based on the selected option.
    
    Returns:
        werkzeug.wrappers.Response: A redirect to the appropriate login page.
    """
    option = request.form['option']
    if option == 'Aimp':
        return redirect(url_for('login_aimp'))
    elif option == 'Songs':
        return redirect(url_for('send_mail'))
    elif option == 'Logs':
        return redirect(url_for('login_logs'))

# ================================= AIMP =========================================

@app.route('/aimp/login', methods=['GET', 'POST'])
def login_aimp():
    """
    Handle login for the AIMP panel.
    
    Returns:
        str: The rendered HTML template for the AIMP login page, or a redirect to the AIMP dashboard.
    """
    if request.method == 'POST':
        password_attempt = request.form['password']
        if password_attempt == PASSWORD_AIMP:
            session.pop('aimp_panel', None)
            session['logged_in_aimp'] = True
            return redirect(url_for('aimp_dashboard'))
        else:
            return render_template('login_aimp.html', error="Nieprawidłowe hasło")
    return render_template('login_aimp.html', error=None)

@app.route('/aimp/logout')
def logout_aimp():
    """
    Log out from the AIMP panel.
    
    Returns:
        werkzeug.wrappers.Response: A redirect to the index page.
    """
    session.pop('logged_in_aimp', None)
    return redirect(url_for('index'))

@app.route('/aimp/panel')
def aimp_dashboard():
    """
    Display the AIMP dashboard.
    
    Returns:
        str: The rendered HTML template for the AIMP dashboard or a redirect to the index page.
    """
    if 'logged_in_aimp' in session:
        session.pop('logged_in_aimp', None)
        session['aimp_panel'] = True
        return render_template('aimp_dashboard.html')

    return redirect(url_for('index'))

@app.route('/aimp/update', methods=['POST'])
def update():
    """
    Update the ToDo variable based on the received JSON data.
    
    Returns:
        flask.Response: A JSON response indicating the success or failure of the update.
    """
    if 'aimp_panel' in session:
        global ToDo
        button_value = request.json.get('button', '')
        ToDo = button_value
        return jsonify({'message': 'Wartość zmiennej ToDo została zaktualizowana.', 'ToDo': ToDo})
    return jsonify({'Error': 'Unautorized attempt'})

@app.route('/get', methods=['GET'])
def get_x():
    """
    Get the current value of the ToDoNow variable.
    
    Returns:
        flask.Response: A JSON response with the current value of ToDoNow.
    """
    global ToDo, ToDoNow
    ToDoNow = ToDo
    ToDo = "Pass"
    return jsonify({'ToDo': ToDoNow})

# ================================== LOGS =======================================

@app.route('/logs/login', methods=['GET', 'POST'])
def login_logs():
    """
    Handle login for the Logs panel.
    
    Returns:
        str: The rendered HTML template for the Logs login page, or a redirect to the Logs dashboard.
    """
    if request.method == 'POST':
        password_attempt = request.form['password']
        if password_attempt == PASSWORD_LOGS:
            session.pop('logs_panel', None)
            session['logged_in_logs'] = True
            return redirect(url_for('logs_dashboard'))
        else:
            return render_template('login_logs.html', error="Nieprawidłowe hasło")
    return render_template('login_logs.html', error=None)

@app.route('/logs/panel')
def logs_dashboard():
    """
    Display the Logs dashboard.
    
    Returns:
        str: The rendered HTML template for the Logs dashboard or a redirect to the index page.
    """
    if 'logged_in_logs' in session:
        session.pop('logged_in_logs', None)
        session['logs_panel'] = True
        return render_template('logs_dashboard.html')

    return redirect(url_for('index'))

@app.route('/get_logs')
def get_logs():
    """
    Retrieve and return the contents of the log file.
    
    Returns:
        flask.Response: A JSON response with the log file contents or an error message.
    """
    if 'logs_panel' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        with open(LOG_FILE_PATH, 'r') as f:
            logs = f.read().splitlines()
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logs/logout')
def logout_logs():
    """
    Log out from the Logs panel.
    
    Returns:
        werkzeug.wrappers.Response: A redirect to the index page.
    """
    session.pop('logged_in_logs', None)
    return redirect(url_for('index'))

# ================================== ACCEPT SONGS =================================

@app.route('/songs')
def send_mail():
    """
    Display the page for sending an email regarding songs.
    
    Returns:
        str: The rendered HTML template for the send email page.
    """
    session['email_sent'] = True
    return render_template('send_email.html', email_api_url=f"{SONGS_URL}/sendadminemail")

@app.route('/songs/login')
def login_songs():
    """
    Display the login page for the Songs panel.
    
    Returns:
        str: The rendered HTML template for the Songs login page.
    """
    return render_template('login_songs.html')

@app.route('/songs/panel')
def songs_dashboard():
    """
    Display the Songs dashboard after successful login and API request.
    
    Returns:
        str: The rendered HTML template for the Songs dashboard with the song data, or a redirect to the send email page.
    """
    if 'logged_in_songs' in session:
        session.pop('logged_in_songs', None)
        params = {'adminCode': session['request_code']}
        code = params['adminCode']
        print(code)
        songs_data = requests.get(f"{SONGS_URL}/songstocheck?adminCode={code}").json()
        print(songs_data)
        return render_template('songs_dashboard.html', songs_data=songs_data)
    return redirect(url_for('send_mail'))

@app.route('/songs/verify', methods=['POST'])
def verify():
    """
    Verify the admin code for accessing the Songs panel.
    
    Returns:
        werkzeug.wrappers.Response: A redirect to the Songs dashboard or an error message.
    """
    code = request.form['code']
    response = requests.post(f"{SONGS_URL}/adminlogin?code={code}")
    
    if response.status_code == 200:
        if response.text:
            session['request_code'] = response.text
            session['logged_in_songs'] = True
            session['accept_songs'] = True
            return redirect(url_for('songs_dashboard'))
        else:
            return render_template('login_songs.html', error='Nieprawidłowy kod')
    else:
        return render_template('login_songs.html', error='Błąd serwera. Spróbuj ponownie później.')

@app.route('/acceptsong/<song_id>', methods=['POST'])
def accept_song(song_id):
    """
    Handle the acceptance of a song.
    
    Args:
        song_id (str): The ID of the song to accept.
    
    Returns:
        flask.Response: A JSON response indicating the success or failure of the acceptance.
    """
    if 'accept_songs' in session:
        try:
            response = requests.post(f"{SONGS_URL}/acceptsong/{song_id}")
            if response.status_code == 200:
                return jsonify({'message': 'Song accepted successfully.'})
            else:
                return jsonify({'error': 'Failed to accept the song.'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/refusesong/<song_id>', methods=['POST'])
def refuse_song(song_id):
    """
    Handle the refusal of a song.
    
    Args:
        song_id (str): The ID of the song to refuse.
    
    Returns:
        flask.Response: A JSON response indicating the success or failure of the refusal.
    """
    if 'accept_songs' in session:
        try:
            response = requests.post(f"{SONGS_URL}/refusesong/{song_id}")
            if response.status_code == 200:
                return jsonify({'message': 'Song refused successfully.'})
            else:
                return jsonify({'error': 'Failed to refuse the song.'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Unauthorized'}), 401

if __name__ == '__main__':
    app.run(debug=True)
