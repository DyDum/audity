# AUdit script with debug logging
sudo ./venv/bin/python main.py --verbose scan --rules ./rules --output ./reports_debug 2>&1 | tee scan_debug.log

# AUdit script with automatic correction
#sudo ./venv/bin/python main.py --verbose scan --rules ./rules --output ./reports_correction --fix
