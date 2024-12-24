"""
UI Configuration settings for the DevopsEAPService application.
This module contains settings that control various UI elements' visibility and behavior.
"""

UI_CONFIG = {
    # Controls the visibility of the PowerShell Remote Session dropdown
    'show_powershell_remote_session': True,  # Set to False to hide the dropdown completely
}

def get_ui_config():
    """
    Returns the current UI configuration settings.
    
    Returns:
        dict: Dictionary containing UI configuration settings
    """
    return UI_CONFIG
