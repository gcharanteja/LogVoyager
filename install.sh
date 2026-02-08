#!/bin/bash
# PyMon Installation Script

set -e

echo "🚀 PyMon Installation"
echo "===================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}📦 Installing dependencies...${NC}"
pip install -r requirements.txt

echo ""
echo -e "${BLUE}🔧 Setting up PyMon...${NC}"

# Make pymon executable
chmod +x "$SCRIPT_DIR/pymon"

# Create symlink
INSTALL_DIR="/usr/local/bin"
if [ -w "$INSTALL_DIR" ]; then
    ln -sf "$SCRIPT_DIR/pymon" "$INSTALL_DIR/pymon"
    echo -e "${GREEN}✅ PyMon installed to $INSTALL_DIR${NC}"
else
    echo -e "${YELLOW}⚠️  Need sudo to install to $INSTALL_DIR${NC}"
    sudo ln -sf "$SCRIPT_DIR/pymon" "$INSTALL_DIR/pymon"
    echo -e "${GREEN}✅ PyMon installed to $INSTALL_DIR${NC}"
fi

echo ""
echo -e "${BLUE}⚙️  Configuration${NC}"
echo ""
echo "Please configure your server URL:"
read -p "Enter server URL (default: http://localhost:5000/post): " SERVER_URL
SERVER_URL=${SERVER_URL:-http://localhost:5000/post}

# Create/update config
cat > "$SCRIPT_DIR/pymon.config.toml" << EOF
[server]
url = "$SERVER_URL"
timeout = 10

[monitoring]
capture_stdout = true
capture_stderr = true
capture_system_metrics = true
capture_file_listing = true

[metrics]
cpu = true
memory = true
disk = true
network = true

[display]
show_progress = true
verbose = false
EOF

echo ""
echo -e "${GREEN}✅ Configuration saved!${NC}"
echo ""
echo -e "${BLUE}📚 Quick Start Guide:${NC}"
echo ""
echo "  1. Run a script with monitoring:"
echo "     ${YELLOW}pymon your_script.py${NC}"
echo ""
echo "  2. Enable auto-monitoring:"
echo "     ${YELLOW}pymon activate${NC}"
echo "     ${YELLOW}source ~/.bashrc${NC}"
echo ""
echo "  3. Check status:"
echo "     ${YELLOW}pymon status${NC}"
echo ""
echo "  4. View help:"
echo "     ${YELLOW}pymon help${NC}"
echo ""
echo -e "${GREEN}🎉 Installation complete!${NC}"