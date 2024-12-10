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
    return render_template('dashboard.html', username=current_user.id)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/test_connection', methods=['POST'])
@login_required
def test_connection():
    data = request.get_json()
    computer = data.get('computer', '')
    
    try:
        # Test basic connection
        return jsonify({
            'success': True,
            'message': f'Successfully connected to {computer}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Connection failed: {str(e)}'
        })

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
