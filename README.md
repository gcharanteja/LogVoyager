# 🔍 PyMon - Python Script Monitor

**Automatic Python script monitoring with system metrics and remote logging**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Features

- ✅ **Automatic Monitoring** - Captures stdout/stderr from any Python script
- 📊 **System Metrics** - CPU, RAM, disk, and network usage tracking
- 🏷️ **Unique Run IDs** - Every execution gets a UUID for easy tracking
- ⏱️ **Timestamped Logs** - Structured logs with millisecond precision
- 🌐 **Remote Storage** - Send data to your own server
- 🚀 **Zero Configuration** - Works out of the box

## 📦 Quick Installation

```bash
# Clone the repository
git clone https://github.com/gcharanteja/LogVoyager
cd LogVoyager
$ chmod +x install.sh
# Run the installer
./install.sh
```

## 🎯 Usage

### Basic Usage

```bash
# Monitor a script
pymon your_script.py

# With arguments
pymon train.py --epochs 100 --lr 0.001
```

### Automatic Monitoring

```bash
# Enable auto-monitoring (makes python3 automatically monitor)
pymon activate
source ~/.bashrc

# Now all python3 commands are monitored!
python3 your_script.py
```

### Check Status

```bash
pymon status
```

### Get Help

```bash
pymon help
```

## ⚙️ Configuration

Edit `pymon.config.toml` to configure your server:

```toml
[server]
url = "https://abc.com/post"  # Your remote server
timeout = 10

[monitoring]
capture_stdout = true
capture_stderr = true
capture_system_metrics = true
```

Or use environment variables:

```bash
export PYMON_SERVER_URL="https://abc.com/post"
export PYMON_TIMEOUT="10"
```

## 🌐 Server Setup

The monitoring data is sent to a Flask server. You can:

1. **Host your own server** - Deploy `server.py` to your infrastructure
2. **Use the cloud** - Deploy to AWS, GCP, Azure, or DigitalOcean
3. **Local testing** - Run `python3 server.py` locally

### Quick Server Deploy (Example)

```bash
# On your server (abc.com)
git clone https://github.com/yourusername/pymon-server.git
cd pymon-server
pip install -r requirements.txt
python3 server.py
```

## 📊 Data Format

Each run generates structured JSON data:

```json
{
  "run_id": "a3f8d9c2-1e4b-4c8a-9f2d-7b5e3a1c6d8f",
  "overview": {
    "start_time": "February 08, 2026 11:17:51 AM",
    "runtime": "0:00:02.526514",
    "command": "python3 train.py"
  },
  "system_stats": {
    "cpu_percent": "1.0",
    "memory_used_mb": "2535.9"
  },
  "logs": {
    "stdout": "...",
    "stderr": "...",
    "structured_logs": [...]
  }
}
```

## 🔧 Requirements

- Python 3.8+
- `psutil`
- `requests`

## 📝 Examples

### Monitor ML Training

```python
# train.py
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

for epoch in range(100):
    log.info(f"Epoch {epoch} - loss: 0.42")
```

```bash
pymon train.py
# All logs automatically captured and sent to your server!
```

### Monitor with Custom Arguments

```bash
pymon inference.py --model resnet50 --batch-size 64
```

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a PR.

## 📄 License

MIT License - see LICENSE file for details

## 🛠️ Troubleshooting

### Server not reachable

```bash
# Check server URL in config
cat pymon.config.toml

# Or set environment variable
export PYMON_SERVER_URL="https://your-server.com/post"
```

### Permission denied

```bash
# Re-run installation with sudo
sudo ./install.sh
```

## 📞 Support

- Issues: [GitHub Issues](https://github.com/yourusername/pymon/issues)
- Docs: [Full Documentation](https://github.com/yourusername/pymon/wiki)

---

Made with ❤️ for Python developers
