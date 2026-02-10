from flask import Flask, request, jsonify
from datetime import datetime
import uuid
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import os
import certifi

app = Flask(__name__)

# MongoDB Configuration
MONGODB_URI = os.environ.get(
    'MONGODB_URI',
    'mongodb+srv://gattucharanteja8143_db_user:BVrwcbN2RRdMrof6@logvdb.iwkosrh.mongodb.net/'
)
DATABASE_NAME = 'logvoyager'
COLLECTION_NAME = 'logs'

# Initialize MongoDB client with proper SSL configuration
try:
    client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        tls=True,
        tlsCAFile=certifi.where(),  # Use certifi's CA bundle
        retryWrites=True,
        w='majority'
    )
    
    # Test connection
    client.admin.command('ping')
    db = client[DATABASE_NAME]
    logs_collection = db[COLLECTION_NAME]
    
    # Create indexes for better performance
    logs_collection.create_index('run_id', unique=True)
    logs_collection.create_index('receipt_timestamp')
    logs_collection.create_index('source')
    logs_collection.create_index('overview.hostname')
    
    print("✅ MongoDB connected successfully!")
    print(f"   Database: {DATABASE_NAME}")
    print(f"   Collection: {COLLECTION_NAME}")
    MONGODB_CONNECTED = True
except ConnectionFailure as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("⚠️  Server will run in fallback mode (memory only)")
    MONGODB_CONNECTED = False
    logs_collection = None
except Exception as e:
    print(f"❌ Unexpected error connecting to MongoDB: {e}")
    print("⚠️  Server will run in fallback mode (memory only)")
    MONGODB_CONNECTED = False
    logs_collection = None

# Health check endpoint at root
@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint to verify server is running"""
    try:
        data_entries = 0
        mongodb_status = "disconnected"
        
        if MONGODB_CONNECTED and logs_collection is not None:
            try:
                data_entries = logs_collection.count_documents({})
                mongodb_status = "connected"
            except Exception as e:
                mongodb_status = f"error: {str(e)}"
        
        return jsonify({
            "status": "healthy",
            "service": "LogVoyager",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "mongodb_status": mongodb_status,
            "database": DATABASE_NAME,
            "collection": COLLECTION_NAME,
            "total_logs": data_entries
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/post', methods=['POST', 'OPTIONS'])
def receive_data():
    """Receive and store monitoring data"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response, 200
    
    try:
        # Check MongoDB connection
        if not MONGODB_CONNECTED or logs_collection is None:
            return jsonify({
                "status": "error",
                "message": "Database not available"
            }), 503
        
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
        
        # Extract directory listing
        if 'Directory Listing' in data_str:
            try:
                listing_section = data_str.split('Directory Listing')[1].split('Return code:')[0]
                listing_lines = listing_section.strip().split('\n')
                
                for line in listing_lines:
                    line = line.strip()
                    if line.startswith('[DIR]'):
                        dir_name = line.replace('[DIR]', '').strip()
                        structured_data['files'].append({
                            'type': 'directory',
                            'name': dir_name,
                            'size': None
                        })
                    elif line.startswith('[FILE]'):
                        file_info = line.replace('[FILE]', '').strip()
                        if '(' in file_info and 'bytes)' in file_info:
                            name = file_info.split('(')[0].strip()
                            size_str = file_info.split('(')[1].split('bytes')[0].strip()
                            structured_data['files'].append({
                                'type': 'file',
                                'name': name,
                                'size': int(size_str)
                            })
            except Exception as e:
                print(f"Warning: Could not parse directory listing: {e}")
        
        # Extract system stats
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
        
        if '--- STRUCTURED LOGS ---' in data_str:
            logs_data = data_str.split('--- STRUCTURED LOGS ---')[1].split('---')[0].strip()
            structured_data['logs']['structured'] = logs_data.split('\n')
        
        # Insert into MongoDB
        result = logs_collection.insert_one(structured_data)
        
        # Get total count
        total_logs = logs_collection.count_documents({})
        
        print(f"✅ Data received: {structured_data['type']} at {structured_data['receipt_timestamp']}")
        print(f"   Run ID: {run_id}")
        print(f"   MongoDB ID: {result.inserted_id}")
        print(f"   Total logs: {total_logs}")
        
        # Return success response
        response = jsonify({
            "status": "success", 
            "message": "Structured data received and stored successfully",
            "run_id": run_id,
            "stored_at": structured_data['receipt_timestamp'],
            "total_logs": total_logs
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
    """Endpoint to view stored data with pagination"""
    try:
        if not MONGODB_CONNECTED or logs_collection is None:
            return jsonify({"error": "Database not available"}), 503
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        skip = (page - 1) * limit
        
        # Get total count
        total = logs_collection.count_documents({})
        
        # Get paginated data (sorted by receipt_timestamp descending)
        cursor = logs_collection.find({}, {'_id': 0}).sort('receipt_timestamp', -1).skip(skip).limit(limit)
        data = list(cursor)
        
        response = jsonify({
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit,
            'data': data
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/view/<run_id>', methods=['GET'])
def view_run(run_id):
    """View a specific run by ID"""
    try:
        if not MONGODB_CONNECTED or logs_collection is None:
            return jsonify({"error": "Database not available"}), 503
        
        entry = logs_collection.find_one({'run_id': run_id}, {'_id': 0})
        
        if entry:
            response = jsonify(entry)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            return jsonify({"error": "Run ID not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get statistics about stored logs"""
    try:
        if not MONGODB_CONNECTED or logs_collection is None:
            return jsonify({"error": "Database not available"}), 503
        
        total = logs_collection.count_documents({})
        
        # Get unique hostnames
        hostnames = logs_collection.distinct('overview.hostname')
        
        # Get recent logs
        recent = list(logs_collection.find({}, {'_id': 0, 'run_id': 1, 'receipt_timestamp': 1, 'overview.hostname': 1})
                     .sort('receipt_timestamp', -1).limit(10))
        
        response = jsonify({
            'total_logs': total,
            'unique_hosts': len(hostnames),
            'hosts': hostnames,
            'recent_runs': recent
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 LogVoyager Server Starting...")
    print(f"🗄️  Database: {DATABASE_NAME}")
    print(f"📦 Collection: {COLLECTION_NAME}")
    print(f"🌐 Server: http://0.0.0.0:5000")
    print(f"💚 Health: http://0.0.0.0:5000/")
    print(f"📮 POST: http://0.0.0.0:5000/post")
    print(f"👀 View: http://0.0.0.0:5000/view")
    print(f"📊 Stats: http://0.0.0.0:5000/stats")
    
    app.run(host='0.0.0.0', port=5000, debug=True)