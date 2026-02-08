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
    try:
        data_entries = 0
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data_entries = len(json.load(f))
    except:
        data_entries = 0
    
    return jsonify({
        "status": "healthy",
        "service": "LogVoyager",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "data_file": DATA_FILE,
        "data_entries": data_entries
    }), 200

@app.route('/post', methods=['POST', 'OPTIONS'])  # <-- ADD OPTIONS for CORS
def receive_data():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response, 200
    
    try:
        # Get the JSON data from the request
        raw_data = request.get_json()
        
        if not raw_data:
            return jsonify({
                "status": "error",
                "message": "No JSON data received"
            }), 400
        
        # Parse the raw data string to extract different components
        data_str = raw_data.get('data', '')
        
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
            'source': raw_data.get('source', 'unknown'),
            'type': raw_data.get('type', 'unknown'),
            'timestamp': raw_data.get('timestamp', datetime.now().isoformat()),
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
            tracked_line = data_str.split('Tracked hours:')[1].split('\n')[0].strip()
            structured_data['overview']['tracked_hours'] = tracked_line
            
        if 'Run path:' in data_str:
            path_line = data_str.split('Run path:')[1].split('\n')[0].strip()
            structured_data['overview']['run_path'] = path_line
            
        if 'Hostname:' in data_str:
            hostname_line = data_str.split('Hostname:')[1].split('\n')[0].strip()
            structured_data['overview']['hostname'] = hostname_line
            
        if 'OS:' in data_str:
            os_line = data_str.split('OS:')[1].split('\n')[0].strip()
            structured_data['overview']['os'] = os_line
            
        if 'Python version:' in data_str:
            py_version_line = data_str.split('Python version:')[1].split('\n')[0].strip()
            structured_data['overview']['python_version'] = py_version_line
            
        if 'Python executable:' in data_str:
            py_exec_line = data_str.split('Python executable:')[1].split('\n')[0].strip()
            structured_data['overview']['python_executable'] = py_exec_line
            
        if 'Command:' in data_str:
            command_line = data_str.split('Command:')[1].split('\n')[0].strip()
            structured_data['overview']['command'] = command_line
            
        if 'Return code:' in data_str:
            return_code_line = data_str.split('Return code:')[1].split('\n')[0].strip()
            structured_data['overview']['return_code'] = return_code_line
        
        # Extract system stats (simplified)
        for metric_section in ['BEFORE', 'AFTER', 'DIFFERENCE']:
            section_key = f'--- SYSTEM METRICS {metric_section} ---'
            if section_key in data_str:
                section_data = data_str.split(section_key)[1].split('---')[0]
                metrics = {}
                for line in section_data.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metrics[key.strip()] = value.strip()
                structured_data['system_stats'][metric_section.lower()] = metrics
        
        # Extract logs
        if '--- STDOUT ---' in data_str:
            stdout_data = data_str.split('--- STDOUT ---')[1].split('---')[0].strip()
            structured_data['logs']['stdout'] = stdout_data
        
        if '--- STDERR ---' in data_str:
            stderr_data = data_str.split('--- STDERR ---')[1].split('---')[0].strip()
            structured_data['logs']['stderr'] = stderr_data
        
        # Extract structured logs
        if '--- STRUCTURED LOGS ---' in data_str:
            logs_data = data_str.split('--- STRUCTURED LOGS ---')[1].split('---')[0].strip()
            structured_data['logs']['structured'] = logs_data.split('\n')
        
        # Load existing data from the file
        existing_data = []
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    existing_data = json.load(f)
            except:
                existing_data = []
        
        # Append the new structured data
        existing_data.append(structured_data)
        
        # Write the updated data back to the file
        with open(DATA_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        print(f"✅ Data received: {structured_data['type']} at {structured_data['receipt_timestamp']}")
        print(f"   Run ID: {run_id}")
        print(f"   Total logs: {len(existing_data)}")
        
        # Return a success response with CORS headers
        response = jsonify({
            "status": "success", 
            "message": "Structured data received and stored successfully",
            "run_id": run_id,
            "stored_at": structured_data['receipt_timestamp'],
            "total_logs": len(existing_data)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        print(f"❌ Error receiving data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        response = jsonify({
            "status": "error", 
            "message": f"Failed to receive data: {str(e)}"
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/view', methods=['GET'])
def view_data():
    """Endpoint to view stored data"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            response = jsonify(data)
        else:
            response = jsonify([])
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/view/<run_id>', methods=['GET'])
def view_run(run_id):
    """View a specific run by ID"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            
            for entry in data:
                if entry.get('run_id') == run_id:
                    response = jsonify(entry)
                    response.headers.add('Access-Control-Allow-Origin', '*')
                    return response, 200
            
            return jsonify({"error": "Run ID not found"}), 404
        else:
            return jsonify({"error": "No data file found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 LogVoyager Server Starting...")
    print(f"📊 Data file: {DATA_FILE}")
    print(f"🌐 Server: http://0.0.0.0:5000")
    print(f"💚 Health: http://0.0.0.0:5000/")
    print(f"📮 POST: http://0.0.0.0:5000/post")
    print(f"👀 View: http://0.0.0.0:5000/view")
    
    # Create empty data file if it doesn't exist
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)
        print(f"✅ Created {DATA_FILE}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)