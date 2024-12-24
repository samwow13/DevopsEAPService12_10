from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan
import json
from config.server_config import SERVER_CONFIGS
from config.ui_config import get_ui_config
from config.domain_config import get_network_config, update_network_config

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
    ui_config = get_ui_config()
    return render_template('dashboard.html', 
                         username=current_user.id, 
                         connection_mode=session['connection_mode'],
                         ui_config=ui_config,
                         servers=list(SERVER_CONFIGS.keys()))

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

@app.route('/update_server', methods=['POST'])
@login_required
def update_server():
    server = request.json.get('server')
    if server in SERVER_CONFIGS:
        config = SERVER_CONFIGS[server]
        # Replace {user} placeholder with actual username
        config['username'] = config['username'].format(user=current_user.id)
        session['current_server'] = server
        session['server_config'] = config
        return jsonify({'success': True, 'message': f'Connected to {server}'})
    return jsonify({'success': False, 'message': 'Invalid server selection'}), 400

@app.route('/get_process_commands', methods=['POST'])
@login_required
def get_process_commands():
    data = request.get_json()
    server_name = data.get('server', 'Local PC')  # Default to Local PC
    process_name = data.get('process')
    
    if not server_name or not process_name:
        return jsonify({
            'success': False,
            'message': 'Server name and process name are required'
        })
    
    if server_name in SERVER_CONFIGS and process_name in SERVER_CONFIGS[server_name]['processes']:
        process_config = SERVER_CONFIGS[server_name]['processes'][process_name]
        return jsonify({
            'success': True,
            'start_command': process_config['start_command'],
            'stop_command': process_config['stop_command']
        })
    return jsonify({
        'success': False,
        'message': f'Process {process_name} not found for server {server_name}'
    })

@app.route('/execute_process', methods=['POST'])
@login_required
def execute_process():
    """Execute a process action (start/stop) on a specified server"""
    # TODO: Hook this up to the UI
    data = request.get_json()
    server_name = data.get('server', 'Local PC')
    process_name = data.get('process')
    action = data.get('action')  # 'start' or 'stop'
    
    if not all([server_name, process_name, action]) or action not in ['start', 'stop']:
        return jsonify({
            'success': False,
            'message': 'Invalid request parameters'
        })
    
    if server_name not in SERVER_CONFIGS:
        return jsonify({
            'success': False,
            'message': f'Server {server_name} not found'
        })
        
    server_config = SERVER_CONFIGS[server_name]
    if process_name not in server_config['processes']:
        return jsonify({
            'success': False,
            'message': f'Process {process_name} not found for server {server_name}'
        })
    
    try:
        # Create WSMan connection
        wsman = WSMan(server_config['computer_name'], 
                     username=server_config.get('username'),
                     ssl=server_config.get('ssl', False))
        
        # Create process configuration
        process_config = {
            'name': process_name,
            'start_command': server_config['processes'][process_name]['start_command'],
            'stop_command': server_config['processes'][process_name]['stop_command']
        }
        
        # Execute the action
        with RunspacePool(wsman) as pool:
            ps = PowerShell(pool)
            if action == 'start':
                ps.add_script(process_config['start_command']).invoke()
                return jsonify({
                    'success': True,
                    'message': f'Process {process_name} started successfully'
                })
            else:
                ps.add_script(process_config['stop_command']).invoke()
                return jsonify({
                    'success': True,
                    'message': f'Process {process_name} stopped successfully'
                })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error executing {action} for {process_name}: {str(e)}'
        })

@app.route('/process_status', methods=['POST'])
@login_required
def process_status():
    """Get the current status of a process on a specified server"""
    # TODO: Hook this up to the UI
    data = request.get_json()
    server_name = data.get('server', 'Local PC')
    process_name = data.get('process')
    
    if not all([server_name, process_name]):
        return jsonify({
            'success': False,
            'message': 'Server name and process name are required'
        })
    
    if server_name not in SERVER_CONFIGS:
        return jsonify({
            'success': False,
            'message': f'Server {server_name} not found'
        })
        
    server_config = SERVER_CONFIGS[server_name]
    if process_name not in server_config['processes']:
        return jsonify({
            'success': False,
            'message': f'Process {process_name} not found for server {server_name}'
        })
    
    try:
        # Create WSMan connection
        wsman = WSMan(server_config['computer_name'], 
                     username=server_config.get('username'),
                     ssl=server_config.get('ssl', False))
        
        # Check process status
        with RunspacePool(wsman) as pool:
            ps = PowerShell(pool)
            ps.add_script(f"Get-Process -Name {process_name} -ErrorAction SilentlyContinue")
            output = ps.invoke()
            is_running = len(output) > 0
            
            return jsonify({
                'success': True,
                'status': 'running' if is_running else 'stopped',
                'process': process_name,
                'server': server_name
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error checking status for {process_name}: {str(e)}'
        })

@app.route('/update_ui_config', methods=['POST'])
def update_ui_config():
    """Update UI configuration settings."""
    try:
        data = request.get_json()
        show_powershell = data.get('show_powershell', False)
        
        # Update the configuration
        ui_config = get_ui_config()
        ui_config['show_powershell_remote_session'] = show_powershell
        
        return jsonify({'success': True, 'show_powershell': show_powershell})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    network_config = get_network_config()
    app.run(
        host=network_config['HOST'],
        port=network_config['PORT'],
        debug=network_config['DEBUG']
    )
