"""
Process Manager Module
Handles process-related operations including start, stop, and status checking.

This module provides classes for managing Windows processes across local and remote machines
using PowerShell remoting. It includes connection pooling, retry logic, and proper resource cleanup.

Classes:
    ProcessConfig: Configuration container for process-specific commands
    ProcessManager: Main class handling process operations and connection management
"""
import time
from typing import Dict, Tuple, Optional
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan
from threading import Lock

class ProcessConfig:
    """
    Configuration class for process management.
    
    This class encapsulates the configuration for a specific process, including
    its name and the commands used to start and stop it. If no specific commands
    are provided, it generates default commands using the process name.
    
    Attributes:
        name (str): Name of the process
        start_command (str): PowerShell command to start the process
        stop_command (str): PowerShell command to stop the process
    """
    def __init__(self, name: str, start_command: Optional[str] = None, stop_command: Optional[str] = None):
        """
        Initialize a new ProcessConfig instance.
        
        Args:
            name: Name of the process
            start_command: Optional custom command to start the process
            stop_command: Optional custom command to stop the process
        """
        self.name = name
        self.start_command = start_command or f"Start-Process {name}"
        self.stop_command = stop_command or f"Stop-Process -Name {name} -Force"

    def to_dict(self):
        """
        Convert process config to dictionary format.
        
        Returns:
            dict: Dictionary containing process configuration
        """
        return {
            'name': self.name,
            'start_command': self.start_command,
            'stop_command': self.stop_command
        }

class ProcessManager:
    """
    Manages process operations using PowerShell remoting.
    
    This class handles all process-related operations including starting, stopping,
    and monitoring processes across local and remote machines. It maintains a pool
    of PowerShell sessions for better performance and implements retry logic for
    reliability.
    
    Attributes:
        MAX_RETRIES (int): Maximum number of retry attempts for operations
        RETRY_DELAY (int): Delay in seconds between retry attempts
        SESSION_TIMEOUT (int): Session timeout in seconds
        _sessions (Dict): Dictionary of active PowerShell sessions
        _lock (Lock): Thread lock for session management
    """
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    SESSION_TIMEOUT = 300  # 5 minutes
    
    def __init__(self):
        """
        Initialize a new ProcessManager instance.
        
        Sets up the session pool and thread lock for managing PowerShell connections.
        """
        self._sessions: Dict[str, Tuple[RunspacePool, float]] = {}  # (session, last_used_timestamp)
        self._lock = Lock()
        
    def _get_session(self, server_config: dict) -> RunspacePool:
        """
        Get or create a PowerShell session for a server.
        
        This method manages the session pool, creating new sessions when needed
        and reusing existing ones when available. It also handles session
        expiration and cleanup.
        
        Args:
            server_config: Dictionary containing server connection details
                         (computer_name, username, ssl)
        
        Returns:
            RunspacePool: Active PowerShell session for the server
        
        Raises:
            Exception: If unable to create or retrieve a valid session
        """
        server_key = f"{server_config['computer_name']}_{server_config.get('username', 'local')}"
        
        with self._lock:
            # Check for existing valid session
            if server_key in self._sessions:
                session, last_used = self._sessions[server_key]
                if time.time() - last_used < self.SESSION_TIMEOUT:
                    self._sessions[server_key] = (session, time.time())  # Update timestamp
                    return session
                else:
                    # Session expired, clean it up
                    self._cleanup_session(server_key)
            
            # Create new session
            wsman = WSMan(server_config['computer_name'],
                         username=server_config.get('username'),
                         ssl=server_config.get('ssl', False))
            session = RunspacePool(wsman)
            session.open()
            self._sessions[server_key] = (session, time.time())
            return session
    
    def _cleanup_session(self, server_key: str):
        """
        Clean up a specific PowerShell session.
        
        Closes and removes a session from the session pool. Handles any
        errors that occur during cleanup gracefully.
        
        Args:
            server_key: Unique identifier for the server session
        """
        if server_key in self._sessions:
            session, _ = self._sessions[server_key]
            try:
                session.close()
            except:
                pass  # Ignore cleanup errors
            del self._sessions[server_key]
    
    def cleanup_all_sessions(self):
        """
        Clean up all PowerShell sessions.
        
        Closes and removes all sessions from the session pool. This should be
        called when the ProcessManager is no longer needed or during shutdown.
        """
        with self._lock:
            for server_key in list(self._sessions.keys()):
                self._cleanup_session(server_key)
    
    def _execute_with_retry(self, server_config: dict, operation: callable) -> Tuple[bool, str]:
        """
        Execute an operation with retry logic.
        
        Attempts to execute the given operation multiple times, with delays
        between attempts. Handles session cleanup and recreation on failures.
        
        Args:
            server_config: Dictionary containing server connection details
            operation: Callable that performs the actual operation
        
        Returns:
            Tuple[bool, str]: Success status and result/error message
        """
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                session = self._get_session(server_config)
                ps = PowerShell(session)
                return operation(ps)
            except Exception as e:
                last_error = str(e)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                    # Force session cleanup on error
                    server_key = f"{server_config['computer_name']}_{server_config.get('username', 'local')}"
                    self._cleanup_session(server_key)
                    
        return False, f"Operation failed after {self.MAX_RETRIES} attempts. Last error: {last_error}"
    
    def get_process_status(self, server_config: dict, process_name: str) -> Tuple[bool, dict]:
        """
        Check if a process is running with detailed status information.
        
        Retrieves detailed information about a process including its running state,
        PID, CPU usage, memory usage, and start time.
        
        Args:
            server_config: Dictionary containing server connection details
            process_name: Name of the process to check
        
        Returns:
            Tuple[bool, dict]: Success status and process information/error message
        """
        def check_status(ps):
            script = f"""
                $process = Get-Process {process_name} -ErrorAction SilentlyContinue
                if ($process) {{
                    @{{
                        'running' = $true
                        'pid' = $process.Id
                        'cpu' = $process.CPU
                        'memory' = $process.WorkingSet64
                        'start_time' = $process.StartTime.ToString('o')
                    }} | ConvertTo-Json
                }} else {{
                    @{{'running' = $false}} | ConvertTo-Json
                }}
            """
            result = ps.add_script(script).invoke()
            if result:
                import json
                status = json.loads(result[0])
                return True, status
            return False, {'running': False}
            
        success, result = self._execute_with_retry(server_config, check_status)
        if success:
            return True, result
        return False, {'running': False, 'error': result}

    def start_process(self, server_config: dict, process_config: ProcessConfig) -> Tuple[bool, str]:
        """
        Start a process using its configured start command.
        
        Attempts to start the process and verifies that it has started successfully.
        Includes checks to prevent starting already-running processes.
        
        Args:
            server_config: Dictionary containing server connection details
            process_config: ProcessConfig instance with process details
        
        Returns:
            Tuple[bool, str]: Success status and result/error message
        """
        def start_operation(ps):
            # First check if already running
            status_success, status = self.get_process_status(server_config, process_config.name)
            if status_success and status.get('running', False):
                return True, f"Process {process_config.name} is already running"
            
            # Execute start command
            ps.add_script(process_config.start_command).invoke()
            
            # Verify process started
            time.sleep(1)  # Give process time to start
            status_success, status = self.get_process_status(server_config, process_config.name)
            if status_success and status.get('running', False):
                return True, f"Successfully started {process_config.name}"
            return False, f"Failed to start {process_config.name}"
            
        return self._execute_with_retry(server_config, start_operation)

    def stop_process(self, server_config: dict, process_config: ProcessConfig) -> Tuple[bool, str]:
        """
        Stop a process using its configured stop command.
        
        Attempts to stop the process and verifies that it has stopped successfully.
        Includes checks to prevent stopping already-stopped processes.
        
        Args:
            server_config: Dictionary containing server connection details
            process_config: ProcessConfig instance with process details
        
        Returns:
            Tuple[bool, str]: Success status and result/error message
        """
        def stop_operation(ps):
            # First check if actually running
            status_success, status = self.get_process_status(server_config, process_config.name)
            if not status_success or not status.get('running', False):
                return True, f"Process {process_config.name} is not running"
            
            # Execute stop command
            ps.add_script(process_config.stop_command).invoke()
            
            # Verify process stopped
            time.sleep(1)  # Give process time to stop
            status_success, status = self.get_process_status(server_config, process_config.name)
            if status_success and not status.get('running', False):
                return True, f"Successfully stopped {process_config.name}"
            return False, f"Failed to stop {process_config.name}"
            
        return self._execute_with_retry(server_config, stop_operation)

    def __del__(self):
        """
        Cleanup method called when the ProcessManager is destroyed.
        
        Ensures all PowerShell sessions are properly closed and cleaned up
        when the ProcessManager instance is garbage collected.
        """
        self.cleanup_all_sessions()
