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
    return User(username)  # Accept any username

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Accept any credentials
        user = User(username)
        login_user(user)
        session['password'] = password
        flash(f'Welcome {username}!', 'success')
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

@app.route('/test_ps_connection', methods=['POST'])
@login_required
def test_ps_connection():
    try:
        data = request.get_json()
        computer = data.get('computer', 'localhost')
        command = data.get('command', '')
        
        # Get the current password from the session (if available)
        password = session.get('password', '')
        # Obscure half of the password
        if password:
            half_length = len(password) // 2
            obscured_password = password[:half_length] + '*' * (len(password) - half_length)
        else:
            obscured_password = '********'
        
        # Create a display version of the command with partially obscured credentials
        display_command = f"# Command that will be used:\n"
        display_command += f"$securePass = ConvertTo-SecureString '{obscured_password}' -AsPlainText -Force\n"
        display_command += f"$cred = New-Object System.Management.Automation.PSCredential('{current_user.id}', $securePass)\n"
        display_command += f"Enter-PSSession -ComputerName {computer} -Credential $cred\n"
        display_command += f"{command}"
        
        if command.strip().lower() == 'get-process':
            command = "Get-Process | Select-Object Name, @{Name='Running'; Expression={$_.Responding}} | ConvertTo-Json"
        else:
            # For other commands, execute them without forcing JSON output
            command = f"{command}"
        
        # Create a WSMan connection
        wsman = WSMan(computer, ssl=False)
        
        with RunspacePool(wsman) as pool:
            ps = PowerShell(pool)
            ps.add_script(command)
            output = ps.invoke()
            
            # Check if this is a Get-Process command
            if command.strip().lower() == 'get-process':
                processes = []
                for item in output:
                    try:
                        if isinstance(item, str):
                            processes.extend(json.loads(item))
                        else:
                            processes.append({"name": item.Name, "running": item.Running})
                    except json.JSONDecodeError:
                        processes.append({"name": str(item.Name), "running": bool(item.Running)})
                
                return jsonify({
                    "success": True,
                    "message": "PowerShell command executed successfully",
                    "command": display_command,
                    "processes": processes
                })
            else:
                # For other commands, return the raw output
                result = []
                for item in output:
                    if isinstance(item, str):
                        result.append(item)
                    else:
                        # For non-string objects, convert them to string representation
                        result.append(str(item))
                
                return jsonify({
                    "success": True,
                    "message": "PowerShell command executed successfully",
                    "command": display_command,
                    "output": result
                })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to execute PowerShell command: {str(e)}"
        }), 500

@app.route('/processes', methods=['GET'])
@login_required
def get_processes():
    # Dummy data for processes
    processes = [
        {'name': 'Process1', 'running': True},
        {'name': 'Process2', 'running': False},
        {'name': 'Process3', 'running': True}
    ]
    return jsonify(processes)

@app.route('/process/start/<process_name>', methods=['POST'])
@login_required
def start_process(process_name):
    # Logic to start the process
    return jsonify({'success': True, 'message': f'{process_name} started successfully'})

@app.route('/process/stop/<process_name>', methods=['POST'])
@login_required
def stop_process(process_name):
    # Logic to stop the process
    return jsonify({'success': True, 'message': f'{process_name} stopped successfully'})

if __name__ == '__main__':
    app.run(debug=True)
