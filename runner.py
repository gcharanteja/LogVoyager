#!/usr/bin/env python3

import sys
import requests
import json
from datetime import datetime
import os
import psutil
import time
import platform
import subprocess

# Get the directory of this script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# Load configuration
def load_config():
    """Load configuration from pymon.config.toml or environment variables"""
    config = {
        'server_url': os.environ.get('PYMON_SERVER_URL', 'http://localhost:5000/post'),
        'timeout': int(os.environ.get('PYMON_TIMEOUT', '10'))
    }
    
    # Try to load from config file in the same directory as this script
    config_file = os.path.join(SCRIPT_DIR, 'pymon.config.toml')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    if 'url =' in line:
                        config['server_url'] = line.split('=')[1].strip().strip('"')
                    elif 'timeout =' in line:
                        config['timeout'] = int(line.split('=')[1].strip())
        except Exception as e:
            print(f"Warning: Could not parse config file: {e}")
            pass  # Use defaults if config file can't be loaded
    
    return config

def get_system_metrics():
    """Gather system metrics before and after command execution"""
    metrics = {}
    
    # CPU metrics
    metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
    metrics['cpu_count'] = psutil.cpu_count()
    metrics['cpu_threads'] = psutil.cpu_count(logical=True)
    
    # Memory metrics
    memory = psutil.virtual_memory()
    metrics['memory_total_mb'] = round(memory.total / (1024**2), 2)
    metrics['memory_available_mb'] = round(memory.available / (1024**2), 2)
    metrics['memory_used_mb'] = round(memory.used / (1024**2), 2)
    metrics['memory_percent'] = memory.percent
    
    # Disk metrics
    disk_usage = psutil.disk_usage('/')
    metrics['disk_total_gb'] = round(disk_usage.total / (1024**3), 2)
    metrics['disk_used_gb'] = round(disk_usage.used / (1024**3), 2)
    metrics['disk_free_gb'] = round(disk_usage.free / (1024**3), 2)
    metrics['disk_percent'] = (disk_usage.used / disk_usage.total) * 100
    
    # Network metrics (cumulative since boot)
    net_io = psutil.net_io_counters()
    metrics['network_bytes_sent'] = net_io.bytes_sent
    metrics['network_bytes_recv'] = net_io.bytes_recv
    
    # Disk I/O metrics
    disk_io = psutil.disk_io_counters()
    if disk_io:
        metrics['disk_read_bytes'] = disk_io.read_bytes
        metrics['disk_write_bytes'] = disk_io.write_bytes
    else:
        metrics['disk_read_bytes'] = 0
        metrics['disk_write_bytes'] = 0
    
    return metrics


def capture_command_output():
    """Capture the output of a command along with system information"""
    
    # Get the current command that was executed
    command_executed = ' '.join(sys.argv)
    
    # Get current working directory
    cwd = os.getcwd()
    
    # Get system information
    hostname = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
    
    # Get additional system information
    import sys as sys_module
    
    # Record start time
    start_time = datetime.now()
    
    # Gather system metrics before execution
    metrics_before = get_system_metrics()
    
    # Prepare the command to run (the original Python script)
    script_to_run = sys.argv[1] if len(sys.argv) > 1 else 'minimal_py_code.py'
    
    try:
        # Run the command and capture all output (stdout and stderr)
        result = subprocess.run(
            [sys.executable, script_to_run], 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        
        # Calculate runtime
        end_time = datetime.now()
        runtime = end_time - start_time
        
        # Gather system metrics after execution
        metrics_after = get_system_metrics()
        
        # Calculate differences in metrics
        metrics_diff = {}
        for key in metrics_before:
            if isinstance(metrics_before[key], (int, float)):
                metrics_diff[f"{key}_diff"] = metrics_after[key] - metrics_before[key]
        
        # Get directory listing
        dir_listing = os.listdir(cwd)
        
        # Combine stdout and stderr
        all_output = f"Start time: {start_time.strftime('%B %d, %Y %I:%M:%S %p')}\n"
        all_output += f"Runtime: {runtime}\n"
        all_output += f"Tracked hours: {runtime}\n"
        all_output += f"Run path: {cwd}\n"
        all_output += f"Hostname: {hostname}\n"
        all_output += f"OS: {platform.platform()}\n"
        all_output += f"Python version: {platform.python_implementation()} {platform.python_version()}\n"
        all_output += f"Python executable: {sys_module.executable}\n"
        all_output += f"Command: {command_executed}\n"
        all_output += f"System Hardware:\n"
        all_output += f"  CPU count: {psutil.cpu_count()}\n"
        all_output += f"  Logical CPU count: {psutil.cpu_count(logical=True)}\n"
        all_output += f"Directory Listing ({len(dir_listing)} items):\n"
        for item in sorted(dir_listing):
            item_path = os.path.join(cwd, item)
            if os.path.isdir(item_path):
                all_output += f"  [DIR]  {item}\n"
            else:
                size = os.path.getsize(item_path)
                all_output += f"  [FILE] {item} ({size} bytes)\n"
        all_output += f"Return code: {result.returncode}\n"
        all_output += "\n--- SYSTEM METRICS BEFORE EXECUTION ---\n"
        for key, value in metrics_before.items():
            all_output += f"{key}: {value}\n"
        all_output += "\n--- SYSTEM METRICS AFTER EXECUTION ---\n"
        for key, value in metrics_after.items():
            all_output += f"{key}: {value}\n"
        all_output += "\n--- SYSTEM METRICS DIFFERENCE ---\n"
        for key, value in metrics_diff.items():
            all_output += f"{key}: {value}\n"
        # Capture raw logs
        all_output += "\n--- STDOUT ---\n"
        all_output += result.stdout
        all_output += "--- STDERR ---\n"
        all_output += result.stderr
        
        # Also capture structured logs with timestamps if present
        all_output += "\n--- STRUCTURED LOGS ---\n"
        
        # Combine stdout and stderr for log parsing
        combined_logs = result.stdout + result.stderr
        
        # Parse logs with timestamps
        import re
        log_lines = combined_logs.split('\n')
        structured_logs = []
        
        i = 0
        while i < len(log_lines):
            line = log_lines[i].strip()
            # Look for timestamp patterns like YYYY-MM-DD HH:MM:SS
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                
                # The actual log message might be on the next line
                # Check if the current line has additional content after the timestamp
                log_message = line[timestamp_match.end():].strip()
                
                # If the current line after timestamp is empty, look at the next line
                if not log_message and i + 1 < len(log_lines):
                    next_line = log_lines[i + 1].strip()
                    # If the next line doesn't look like a timestamp, treat it as the message
                    if not re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', next_line):
                        log_message = next_line
                        i += 1  # Skip the next line since we used it
                
                if log_message.startswith('|'):
                    log_message = log_message[1:].strip()
                structured_logs.append({
                    'timestamp': timestamp,
                    'message': log_message
                })
            i += 1
        
        if structured_logs:
            for log_entry in structured_logs:
                all_output += f"{log_entry['timestamp']} {log_entry['message']}\n"
        else:
            all_output += "No timestamped logs found in output.\n"
        all_output += f"\n--- EXECUTION TIME ---\n{end_time.isoformat()}\n"
        
        return all_output, result.returncode
        
    except Exception as e:
        # Calculate runtime even in case of exception
        end_time = datetime.now()
        runtime = end_time - start_time
        
        # Gather system metrics after exception
        metrics_after = get_system_metrics()
        
        # Calculate differences in metrics
        metrics_diff = {}
        for key in metrics_before:
            if isinstance(metrics_before[key], (int, float)):
                metrics_diff[f"{key}_diff"] = metrics_after[key] - metrics_before[key]
        
        # Get directory listing
        dir_listing = os.listdir(cwd)
        
        error_output = f"Start time: {start_time.strftime('%B %d, %Y %I:%M:%S %p')}\n"
        error_output += f"Runtime: {runtime}\n"
        error_output += f"Tracked hours: {runtime}\n"
        error_output += f"Run path: {cwd}\n"
        error_output += f"Hostname: {hostname}\n"
        error_output += f"OS: {platform.platform()}\n"
        error_output += f"Python version: {platform.python_implementation()} {platform.python_version()}\n"
        error_output += f"Python executable: {sys_module.executable}\n"
        error_output += f"Command: {command_executed}\n"
        error_output += f"System Hardware:\n"
        error_output += f"  CPU count: {psutil.cpu_count()}\n"
        error_output += f"  Logical CPU count: {psutil.cpu_count(logical=True)}\n"
        error_output += f"Directory Listing ({len(dir_listing)} items):\n"
        for item in sorted(dir_listing):
            item_path = os.path.join(cwd, item)
            if os.path.isdir(item_path):
                error_output += f"  [DIR]  {item}\n"
            else:
                size = os.path.getsize(item_path)
                error_output += f"  [FILE] {item} ({size} bytes)\n"
        error_output += f"Exception occurred: {str(e)}\n"
        error_output += "\n--- SYSTEM METRICS BEFORE EXECUTION ---\n"
        for key, value in metrics_before.items():
            error_output += f"{key}: {value}\n"
        error_output += "\n--- SYSTEM METRICS AFTER EXECUTION ---\n"
        for key, value in metrics_after.items():
            error_output += f"{key}: {value}\n"
        error_output += "\n--- SYSTEM METRICS DIFFERENCE ---\n"
        for key, value in metrics_diff.items():
            error_output += f"{key}: {value}\n"
        
        # Also capture structured logs with timestamps if present
        error_output += "\n--- STRUCTURED LOGS ---\n"
        
        # Since this is an exception case, there's no result.stdout/stderr
        # But we can still include the exception in the log parsing
        exception_text = f"Exception occurred: {str(e)}"
        
        # Parse logs with timestamps
        import re
        log_lines = [exception_text]  # Just the exception in this case
        structured_logs = []
        
        for line in log_lines:
            # Look for timestamp patterns like YYYY-MM-DD HH:MM:SS
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                log_message = line[timestamp_match.end():].strip()
                if log_message.startswith('|'):
                    log_message = log_message[1:].strip()
                structured_logs.append({
                    'timestamp': timestamp,
                    'message': log_message
                })
        
        if structured_logs:
            for log_entry in structured_logs:
                error_output += f"{log_entry['timestamp']} {log_entry['message']}\n"
        else:
            error_output += "No timestamped logs found in output.\n"
        error_output += f"--- EXECUTION TIME ---\n{end_time.isoformat()}\n"

        return error_output, -1

def send_to_external_service(data, service_url=None):
    """Send captured data to an external service"""
    
    config = load_config()
    if service_url is None:
        service_url = config['server_url']
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'PyMon/1.0'
        }
        
        payload = {
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'source': f"{os.uname().nodename if hasattr(os, 'uname') else 'unknown'}:{os.getcwd()}",
            'type': 'cli_execution_log'
        }
        
        response = requests.post(service_url, json=payload, headers=headers, timeout=config['timeout'])
        
        print(f"Data sent successfully to {service_url}")
        print(f"Response status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response preview: {str(response_data)[:200]}...")
        except:
            print(f"Response text preview: {str(response.text)[:200]}...")
        
        return True, response
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to send data to {service_url}: {str(e)}")
        return False, None
    except Exception as e:
        print(f"Unexpected error when sending data: {str(e)}")
        return False, None

def main():
    if len(sys.argv) < 2:
        print("Usage: python capture_and_send.py <script_to_run>")
        sys.exit(1)
    
    # Capture all output from the command
    captured_data, return_code = capture_command_output()
    
    # Print the captured data to console (so user can see it too)
    print(captured_data)
    
    # Send the captured data to an external service
    success, response = send_to_external_service(captured_data)
    
    if success:
        print("\nData successfully captured and sent to external service!")
    else:
        print("\nFailed to send data to external service.")
        # Still exit with the original return code
        sys.exit(return_code if return_code != 0 else 1)

if __name__ == "__main__":
    main()


