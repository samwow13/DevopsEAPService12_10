"""
Server configuration module.
Contains server definitions and their associated process lists.
"""

# Server Configuration
# Add your server configurations here in the following format:
# 'DISPLAY_NAME': {
#     'computer_name': 'actual.server.name',
#     'username': 'domain\\{user}',  # {user} will be replaced with logged in username
#     'ssl': True/False,
#     'auth': 'type of authentication',
#     'processes': {
#         'process_name': {
#             'start_command': 'command to start process',
#             'stop_command': 'command to stop process'
#         }
#     }
# }

SERVER_CONFIGS = {
    'Local PC': {
        'computer_name': 'localhost',
        'username': None,
        'ssl': False,
        'auth': None,
        'processes': {
            "notepad": {
                "start_command": "Start-Process notepad",
                "stop_command": "Stop-Process -Name notepad -Force"
            },
            "SnippingTool": {
                "start_command": "Start-Process SnippingTool",
                "stop_command": "Stop-Process -Name SnippingTool -Force"
            },
            "calc": {
                "start_command": "Start-Process calc",
                "stop_command": "Stop-Process -Name CalculatorApp -Force"
            },
            "mspaint": {
                "start_command": "Start-Process mspaint",
                "stop_command": "Stop-Process -Name mspaint -Force"
            }
        }
    },
    'PROD-1': {
        'computer_name': 'prod1.example.com',  # Replace with actual server name
        'username': 'DOMAIN\\{user}',  # Will use logged in username
        'ssl': True,
        'auth': 'default',
        'processes': {}  # Add specific processes with their commands
    },
    'DEV-1': {
        'computer_name': 'dev1.example.com',  # Replace with actual server name
        'username': 'DOMAIN\\{user}',  # Will use logged in username
        'ssl': True,
        'auth': 'default',
        'processes': {}  # Add specific processes with their commands
    }
    # Add more server configurations as needed
}
