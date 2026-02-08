from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)
DATA_FILE = 'data.json'

# Health check endpoint at root
@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint to verify server is running"""
    return jsonify({
        "status": "healthy",
        "service": "LogVoyager",
        "timestamp": datetime.now().isoformat(),
        "data_file": DATA_FILE,
        "data_entries": len(json.load(open(DATA_FILE))) if os.path.exists(DATA_FILE) else 0
    }), 200

@app.route('/post', methods=['POST'])
def receive_data():
    try:
        # Get the JSON data from the request
        raw_data = request.get_json()
        
        # Parse the raw data string to extract different components
        data_str = raw_data['data']
        
        # Generate unique run ID
        run_id = str(uuid.uuid4())
        
        # Initialize structured data
        structured_data = {
            'run_id': run_id,
            'overview': {},
            'system_stats': {},
            'logs': {},
            'files': [],
            'file_contents': {},
            'errors': [],
            'source': raw_data['source'],
            'type': raw_data['type'],
            'timestamp': raw_data['timestamp'],
            'receipt_timestamp': datetime.now().isoformat()
        }
        
        # Extract overview information
        if 'Start time:' in data_str:
            start_time_line = data_str.split('Start time:')[1].split('\n')[0].strip()
            structured_data['overview']['start_time'] = start_time_line
            
        if 'Runtime:' in data_str:
            runtime_line = data_str.split('Runtime:')[1].split('\n')[0].strip()
            structured_data['overview']['runtime'] = runtime_line
            
        if 'Tracked hours:' in data_str:
            tracked_hours_line = data_str.split('Tracked hours:')[1].split('\n')[0].strip()
            structured_data['overview']['tracked_hours'] = tracked_hours_line
            
        if 'Run path:' in data_str:
            run_path_line = data_str.split('Run path:')[1].split('\n')[0].strip()
            structured_data['overview']['run_path'] = run_path_line
            
        if 'Hostname:' in data_str:
            hostname_line = data_str.split('Hostname:')[1].split('\n')[0].strip()
            structured_data['overview']['hostname'] = hostname_line
            
        if 'OS:' in data_str:
            os_line = data_str.split('OS:')[1].split('\n')[0].strip()
            structured_data['overview']['os'] = os_line
            
        if 'Python version:' in data_str:
            python_version_line = data_str.split('Python version:')[1].split('\n')[0].strip()
            structured_data['overview']['python_version'] = python_version_line
            
        if 'Python executable:' in data_str:
            python_executable_line = data_str.split('Python executable:')[1].split('\n')[0].strip()
            structured_data['overview']['python_executable'] = python_executable_line
            
        if 'Command:' in data_str:
            command_line = data_str.split('Command:')[1].split('\n')[0].strip()
            structured_data['overview']['command'] = command_line
            
        if 'Return code:' in data_str:
            return_code_line = data_str.split('Return code:')[1].split('\n')[0].strip()
            structured_data['overview']['return_code'] = return_code_line
            
        # Extract system stats
        if '--- SYSTEM METRICS BEFORE EXECUTION ---' in data_str:
            start_idx = data_str.find('--- SYSTEM METRICS BEFORE EXECUTION ---')
            end_idx = data_str.find('--- SYSTEM METRICS AFTER EXECUTION ---')
            before_section = data_str[start_idx:end_idx]
            
            for line in before_section.split('\n'):
                if ':' in line and not line.startswith('---'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        structured_data['system_stats'][f'before_{key}'] = value
        
        if '--- SYSTEM METRICS AFTER EXECUTION ---' in data_str:
            start_idx = data_str.find('--- SYSTEM METRICS AFTER EXECUTION ---')
            end_idx = data_str.find('--- SYSTEM METRICS DIFFERENCE ---')
            after_section = data_str[start_idx:end_idx]
            
            for line in after_section.split('\n'):
                if ':' in line and not line.startswith('---'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        structured_data['system_stats'][f'after_{key}'] = value
        
        if '--- SYSTEM METRICS DIFFERENCE ---' in data_str:
            start_idx = data_str.find('--- SYSTEM METRICS DIFFERENCE ---')
            end_idx = data_str.find('--- STDOUT ---')
            diff_section = data_str[start_idx:end_idx]
            
            for line in diff_section.split('\n'):
                if ':' in line and not line.startswith('---'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        structured_data['system_stats'][key] = value
        
        # Extract logs
        if '--- STDOUT ---' in data_str:
            start_idx = data_str.find('--- STDOUT ---')
            end_idx = data_str.find('--- STDERR ---')
            stdout_section = data_str[start_idx:end_idx]
            structured_data['logs']['stdout'] = stdout_section.replace('--- STDOUT ---', '').strip()
        
        if '--- STDERR ---' in data_str:
            start_idx = data_str.find('--- STDERR ---')
            next_section_idx = min(
                data_str.find('--- STRUCTURED LOGS ---') if '--- STRUCTURED LOGS ---' in data_str else len(data_str),
                data_str.find('--- EXECUTION TIME ---') if '--- EXECUTION TIME ---' in data_str else len(data_str)
            )
            stderr_section = data_str[start_idx:next_section_idx]
            structured_data['logs']['stderr'] = stderr_section.replace('--- STDERR ---', '').strip()
        
        # Extract structured logs with timestamps
        if '--- STRUCTURED LOGS ---' in data_str:
            start_idx = data_str.find('--- STRUCTURED LOGS ---')
            end_idx = data_str.find('--- EXECUTION TIME ---')
            if end_idx == -1:
                end_idx = len(data_str)
            structured_logs_section = data_str[start_idx:end_idx]
            
            # Parse timestamped logs
            import re
            all_lines = structured_logs_section.split('\n')
            parsed_logs = []
            
            i = 0
            while i < len(all_lines):
                line = all_lines[i].strip()
                if line and not line.startswith('---'):
                    # Look for timestamp patterns like YYYY-MM-DD HH:MM:SS
                    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                        
                        # The actual log message might be on the next line
                        # Check if the current line has additional content after the timestamp
                        log_message = line[timestamp_match.end():].strip()
                        
                        # If the current line after timestamp is empty, look at the next line
                        if not log_message and i + 1 < len(all_lines):
                            next_line = all_lines[i + 1].strip()
                            # If the next line doesn't look like a timestamp, treat it as the message
                            if not re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', next_line):
                                log_message = next_line
                                i += 1  # Skip the next line since we used it
                        
                        if log_message.startswith('|'):
                            log_message = log_message[1:].strip()
                        parsed_logs.append({
                            'timestamp': timestamp,
                            'message': log_message
                        })
                    elif line != "No timestamped logs found in output.":
                        # If it's not the "no logs found" message, add as a log without timestamp
                        parsed_logs.append({
                            'timestamp': None,
                            'message': line
                        })
                i += 1
            
            structured_data['logs']['structured_logs'] = parsed_logs
        
        # Extract errors
        if 'Traceback' in data_str:
            traceback_start = data_str.find('Traceback')
            traceback_end = data_str.find('--- EXECUTION TIME ---')
            if traceback_end == -1:
                traceback_end = len(data_str)
            traceback_section = data_str[traceback_start:traceback_end]
            structured_data['errors'].append(traceback_section.strip())
        
        if 'Exception occurred:' in data_str:
            exception_line = data_str.split('Exception occurred:')[1].split('\n')[0].strip()
            structured_data['errors'].append(exception_line)
        
        # Extract files
        if 'Directory Listing' in data_str:
            start_idx = data_str.find('Directory Listing')
            next_section_idx = data_str.find('Return code:')
            if next_section_idx == -1:
                next_section_idx = data_str.find('Exception occurred:')
            if next_section_idx == -1:
                next_section_idx = len(data_str)
                
            dir_section = data_str[start_idx:next_section_idx]
            
            # Parse directory listing
            for line in dir_section.split('\n'):
                if '[FILE]' in line or '[DIR]' in line:
                    structured_data['files'].append(line.strip())
                    
                    # Check if it's a .txt file and extract its name
                    if '[FILE]' in line and '.txt' in line:
                        # Extract filename from the line
                        parts = line.split('[FILE]')
                        if len(parts) > 1:
                            filename_part = parts[1].strip()
                            # Extract just the filename without size info
                            filename = filename_part.split('(')[0].strip()
                            
                            # Try to read the file content if it's in the run path
                            file_path = os.path.join(structured_data['overview'].get('run_path', ''), filename)
                            if os.path.exists(file_path):
                                try:
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()
                                        # Limit content size to prevent huge payloads
                                        if len(content) > 10000:  # 10KB limit
                                            content = content[:10000] + "... [TRUNCATED]"
                                        structured_data['file_contents'][filename] = content
                                except Exception as e:
                                    structured_data['file_contents'][filename] = f"[Could not read file: {str(e)}]"
        
        # Load existing data from the file
        existing_data = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
        
        # Append the new structured data
        existing_data.append(structured_data)
        
        # Write the updated data back to the file
        with open(DATA_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        print(f"Structured data received and stored: {structured_data['type']} at {structured_data['receipt_timestamp']}")
        print(f"Run ID: {run_id}")
        
        # Return a success response
        return jsonify({
            "status": "success", 
            "message": "Structured data received and stored successfully",
            "run_id": run_id,
            "stored_at": structured_data['receipt_timestamp']
        }), 200
        
    except Exception as e:
        print(f"Error receiving data: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Failed to receive data: {str(e)}"
        }), 500

@app.route('/view', methods=['GET'])
def view_data():
    """Endpoint to view stored data"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
                return jsonify(data)
            except json.JSONDecodeError:
                return jsonify([])
    else:
        return jsonify([])

if __name__ == '__main__':
    print("Starting data receiver server on http://localhost:5000")
    print(f"Data will be stored in {DATA_FILE}")
    app.run(host='0.0.0.0', port=5000, debug=True)