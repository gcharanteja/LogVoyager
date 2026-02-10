#!/bin/bash
# PyMon Installation Script - Universal Linux Support

set -e

echo "🚀 PyMon Installation"
echo "===================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to detect Python command
detect_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        # Check if it's Python 3
        if python --version 2>&1 | grep -q "Python 3"; then
            echo "python"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Function to detect pip command
detect_pip() {
    if command -v pip3 &> /dev/null; then
        echo "pip3"
    elif command -v pip &> /dev/null; then
        # Check if it's for Python 3
        if pip --version 2>&1 | grep -q "python 3"; then
            echo "pip"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Detect Python
PYTHON_CMD=$(detect_python)
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ Error: Python 3 not found!${NC}"
    echo ""
    echo "Please install Python 3 first:"
    echo "  Ubuntu/Debian: sudo apt-get install python3"
    echo "  RHEL/CentOS:   sudo yum install python3"
    echo "  Fedora:        sudo dnf install python3"
    echo "  Arch:          sudo pacman -S python"
    exit 1
fi

# Detect pip
PIP_CMD=$(detect_pip)
if [ -z "$PIP_CMD" ]; then
    echo -e "${YELLOW}⚠️  pip not found. Attempting to install...${NC}"
    
    # Try to install pip
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-pip
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3-pip
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python-pip
    else
        echo -e "${RED}❌ Error: Could not install pip automatically${NC}"
        echo "Please install pip manually and run this script again"
        exit 1
    fi
    
    # Re-detect pip
    PIP_CMD=$(detect_pip)
    if [ -z "$PIP_CMD" ]; then
        echo -e "${RED}❌ Error: pip installation failed${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Detected Python: $PYTHON_CMD ($(${PYTHON_CMD} --version))${NC}"
echo -e "${GREEN}✅ Detected pip: $PIP_CMD ($(${PIP_CMD} --version | head -n1))${NC}"
echo ""

# Check if requirements.txt exists
if [ ! -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo -e "${RED}❌ Error: requirements.txt not found!${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Installing dependencies...${NC}"

# Try to install dependencies
if ! $PIP_CMD install -r "$SCRIPT_DIR/requirements.txt"; then
    echo ""
    echo -e "${YELLOW}⚠️  Standard installation failed. Trying with --user flag...${NC}"
    
    if ! $PIP_CMD install --user -r "$SCRIPT_DIR/requirements.txt"; then
        echo ""
        echo -e "${RED}❌ Error: Failed to install dependencies${NC}"
        echo ""
        echo "Try manual installation:"
        echo "  $PIP_CMD install psutil requests"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}🔧 Setting up PyMon...${NC}"

# Make pymon executable
chmod +x "$SCRIPT_DIR/pymon"

# Make runner.py executable
chmod +x "$SCRIPT_DIR/runner.py"

# Update shebang in pymon to use detected Python
sed -i "1s|.*|#!$(command -v ${PYTHON_CMD})|" "$SCRIPT_DIR/pymon"
sed -i "1s|.*|#!$(command -v ${PYTHON_CMD})|" "$SCRIPT_DIR/runner.py"

echo -e "${GREEN}✅ Updated shebangs to use: $PYTHON_CMD${NC}"

# Create symlink
INSTALL_DIR="/usr/local/bin"

# Check if we can write to /usr/local/bin
if [ -w "$INSTALL_DIR" ]; then
    ln -sf "$SCRIPT_DIR/pymon" "$INSTALL_DIR/pymon"
    echo -e "${GREEN}✅ PyMon installed to $INSTALL_DIR${NC}"
else
    # Try with sudo
    echo -e "${YELLOW}⚠️  Need sudo to install to $INSTALL_DIR${NC}"
    
    if sudo -n true 2>/dev/null; then
        # User has passwordless sudo
        sudo ln -sf "$SCRIPT_DIR/pymon" "$INSTALL_DIR/pymon"
        echo -e "${GREEN}✅ PyMon installed to $INSTALL_DIR${NC}"
    else
        # Ask for sudo password
        if sudo ln -sf "$SCRIPT_DIR/pymon" "$INSTALL_DIR/pymon" 2>/dev/null; then
            echo -e "${GREEN}✅ PyMon installed to $INSTALL_DIR${NC}"
        else
            # Fallback to user's local bin
            LOCAL_BIN="$HOME/.local/bin"
            mkdir -p "$LOCAL_BIN"
            ln -sf "$SCRIPT_DIR/pymon" "$LOCAL_BIN/pymon"
            echo -e "${GREEN}✅ PyMon installed to $LOCAL_BIN${NC}"
            
            # Check if LOCAL_BIN is in PATH
            if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
                echo -e "${YELLOW}⚠️  $LOCAL_BIN is not in your PATH${NC}"
                echo ""
                echo "Add this to your ~/.bashrc or ~/.zshrc:"
                echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
                
                # Offer to add it automatically
                read -p "Add to PATH automatically? (y/n): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    SHELL_RC="$HOME/.bashrc"
                    if [[ "$SHELL" == *"zsh"* ]]; then
                        SHELL_RC="$HOME/.zshrc"
                    fi
                    
                    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
                    echo -e "${GREEN}✅ Added to $SHELL_RC${NC}"
                    echo -e "${YELLOW}Please run: source $SHELL_RC${NC}"
                fi
            fi
        fi
    fi
fi

echo ""
echo -e "${BLUE}⚙️  Configuration${NC}"
echo ""
echo "Configure your server URL for log storage."
echo ""
read -p "Enter server URL (default: https://logv.onrender.com/post): " SERVER_URL
SERVER_URL=${SERVER_URL:-https://logv.onrender.com/post}

# Create/update config
cat > "$SCRIPT_DIR/pymon.config.toml" << EOF
[server]
# Production server URL
url = "$SERVER_URL"

# For local testing, uncomment:
# url = "http://localhost:5000/post"

timeout = 15

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
echo -e "${BLUE}   Server: ${YELLOW}$SERVER_URL${NC}"
echo ""
echo -e "${BLUE}📚 Quick Start Guide:${NC}"
echo ""
echo "  1. Run a script with monitoring:"
echo "     ${YELLOW}pymon your_script.py${NC}"
echo ""
echo "  2. Enable auto-monitoring (makes python3 auto-monitor):"
echo "     ${YELLOW}pymon activate${NC}"
echo "     ${YELLOW}source ~/.bashrc${NC}"
echo ""
echo "  3. Check status:"
echo "     ${YELLOW}pymon status${NC}"
echo ""
echo "  4. View logs online:"
echo "     ${YELLOW}https://logv.onrender.com/view${NC}"
echo ""
echo "  5. View help:"
echo "     ${YELLOW}pymon help${NC}"
echo ""

# Final verification
if command -v pymon &> /dev/null; then
    echo -e "${GREEN}🎉 Installation complete and verified!${NC}"
    echo ""
    echo "Test with: ${YELLOW}pymon --help${NC}"
else
    echo -e "${YELLOW}⚠️  Installation complete but 'pymon' command not found in PATH${NC}"
    echo ""
    echo "You can still run it with:"
    echo "  ${YELLOW}$SCRIPT_DIR/pymon your_script.py${NC}"
    echo ""
    echo "Or add to PATH manually:"
    echo "  ${YELLOW}export PATH=\"$SCRIPT_DIR:\$PATH\"${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Happy monitoring! All your Python runs are now tracked.${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"