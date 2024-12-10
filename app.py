from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    return User(username)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # For demo purposes, accept any credentials
        user = User(username)
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Default to Local mode if not set
    if 'connection_mode' not in session:
        session['connection_mode'] = 'Local'
    return render_template('dashboard.html', username=current_user.id, connection_mode=session['connection_mode'])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/test_connection', methods=['POST'])
@login_required
def test_connection():
    data = request.get_json()
    try:
        if data.get('computer_name') and data.get('username') and data.get('password'):
            # Attempt remote connection
            wsman = WSMan(data['computer_name'], username=data['username'], password=data['password'])
            with RunspacePool(wsman) as pool:
                ps = PowerShell(pool)
                ps.add_script("$env:COMPUTERNAME")
                output = ps.invoke()
                session['connection_mode'] = 'Remote'
                return jsonify({'success': True, 'message': f'Successfully connected to {output[0]}'})
        else:
            session['connection_mode'] = 'Local'
            return jsonify({'success': False, 'message': 'Missing connection details'})
    except Exception as e:
        session['connection_mode'] = 'Local'
        return jsonify({'success': False, 'message': str(e)})

@app.route('/execute', methods=['POST'])
@login_required
def execute_command():
    data = request.get_json()
    command = data.get('command', '')
    
    try:
        # Create a WSMan connection and RunspacePool
        wsman = WSMan("localhost", ssl=False)
        with RunspacePool(wsman) as pool:
            ps = PowerShell(pool)
            output = ps.add_script(command).invoke()
            return jsonify({
                'success': True,
                'output': [str(item) for item in output]
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'output': f'Error executing command: {str(e)}'
        })

if __name__ == '__main__':
    app.run(debug=True)
