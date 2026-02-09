#!/bin/bash

# -------------------------------
# 🔹 System Info
# -------------------------------
echo "=== System Check Log ===" > log.txt
echo "Date & Time: $(date)" >> log.txt
echo "Disk Usage:" >> log.txt
df -h >> log.txt
echo "Current User: $(whoami)" >> log.txt

# -------------------------------
# 🔹 Directory Automation
# -------------------------------
if [ ! -d "deploy_app" ]; then
    mkdir deploy_app
    echo "Created deploy_app directory" >> log.txt
fi

# Move log.txt inside deploy_app if not already
mv log.txt deploy_app/ 2>/dev/null || echo "log.txt already moved"
