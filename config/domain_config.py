# Network Configuration Settings

NETWORK_CONFIG = {
    'HOST': '0.0.0.0',  # Bind to all network interfaces
    'PORT': 5000,       # Default port
    'DEBUG': True       # Debug mode for development
}

def get_network_config():
    """Get the current network configuration."""
    return NETWORK_CONFIG

def update_network_config(key, value):
    """Update a specific network configuration setting."""
    if key in NETWORK_CONFIG:
        NETWORK_CONFIG[key] = value
        return True
    return False
