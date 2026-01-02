#!/bin/bash
# ===========================================
# Vital Signs Service Setup Script
# ===========================================
# This script sets up:
# 1. The main Vital Signs Listener service
# 2. The log cleanup service and timer
#
# Run with: sudo ./setup.sh
# ===========================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN} Vital Signs Service Setup${NC}"
echo -e "${GREEN}=========================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${YELLOW}Working directory: ${SCRIPT_DIR}${NC}"

# ===========================================
# 1. Create Main Vital Signs Service
# ===========================================
echo ""
echo -e "${GREEN}[1/5] Creating Vital Signs Listener service...${NC}"

cat > /etc/systemd/system/vital-signs.service << 'EOF'
[Unit]
Description=Vital Signs Listener Service
After=network.target

[Service]
# Environment setup
User=qmed
Group=qmed
WorkingDirectory=/home/qmed/qmed/mp5sc_work/Vital-signs

# Paths verified from your 'ls' and 'which python'
ExecStart=/home/qmed/qmed/mp5sc_work/venv/bin/python /home/qmed/qmed/mp5sc_work/Vital-signs/vital_sign_listener.py

# Reliability settings
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Created /etc/systemd/system/vital-signs.service${NC}"

# ===========================================
# 2. Create Log Cleanup Service
# ===========================================
echo ""
echo -e "${GREEN}[2/5] Creating Log Cleanup service...${NC}"

cat > /etc/systemd/system/vital-signs-log-cleanup.service << 'EOF'
[Unit]
Description=Vital Signs Log Cleanup Service
After=network.target

[Service]
Type=oneshot
User=qmed
Group=qmed
WorkingDirectory=/home/qmed/qmed/mp5sc_work/Vital-signs
ExecStart=/home/qmed/qmed/mp5sc_work/Vital-signs/cleanup_logs.sh

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Created /etc/systemd/system/vital-signs-log-cleanup.service${NC}"

# ===========================================
# 3. Create Log Cleanup Timer
# ===========================================
echo ""
echo -e "${GREEN}[3/5] Creating Log Cleanup timer (runs daily at 6 AM)...${NC}"

cat > /etc/systemd/system/vital-signs-log-cleanup.timer << 'EOF'
[Unit]
Description=Daily Log Cleanup Timer for Vital Signs
Requires=vital-signs-log-cleanup.service

[Timer]
# Run daily at 6:00 AM
OnCalendar=*-*-* 06:00:00
# Ensure the job runs even if the system was off at scheduled time
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo -e "${GREEN}✓ Created /etc/systemd/system/vital-signs-log-cleanup.timer${NC}"

# ===========================================
# 4. Make cleanup script executable
# ===========================================
echo ""
echo -e "${GREEN}[4/5] Making cleanup script executable...${NC}"
chmod +x "${SCRIPT_DIR}/cleanup_logs.sh"
echo -e "${GREEN}✓ chmod +x cleanup_logs.sh${NC}"

# ===========================================
# 5. Reload and Enable Services
# ===========================================
echo ""
echo -e "${GREEN}[5/5] Reloading systemd and enabling services...${NC}"

# Reload systemd
systemctl daemon-reload
echo -e "${GREEN}✓ Reloaded systemd daemon${NC}"

# Enable and start vital-signs service
systemctl enable vital-signs.service
systemctl start vital-signs.service
echo -e "${GREEN}✓ Enabled and started vital-signs.service${NC}"

# Enable and start log cleanup timer
systemctl enable vital-signs-log-cleanup.timer
systemctl start vital-signs-log-cleanup.timer
echo -e "${GREEN}✓ Enabled and started vital-signs-log-cleanup.timer${NC}"

# ===========================================
# Final Status
# ===========================================
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN} Setup Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${YELLOW}Service Status:${NC}"
systemctl status vital-signs.service --no-pager -l | head -10
echo ""
echo -e "${YELLOW}Timer Status:${NC}"
systemctl list-timers | grep vital-signs || echo "Timer scheduled"
echo ""
echo -e "${GREEN}Useful Commands:${NC}"
echo "  Check service status:  sudo systemctl status vital-signs.service"
echo "  View service logs:     sudo journalctl -u vital-signs -f"
echo "  Restart service:       sudo systemctl restart vital-signs.service"
echo "  Manual log cleanup:    sudo systemctl start vital-signs-log-cleanup.service"
echo ""
