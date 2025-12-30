#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Temperature Probe Debug Script
==============================
This script connects to a Philips monitor and logs ALL incoming physio IDs
to help identify the correct ID for the temperature probe.

Uses the same connection pattern as vital_sign_listener.py.

Usage:
1. Run this script (it reads the monitor IP from .env)
2. Take a temperature reading with the probe
3. Watch the console output for new physio IDs
4. The script will save all captured data to a log file
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from ipv_data_source import ipv_data_source as device

# Load environment variables from parent .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


class TempProbeDebugger:
    
    def __init__(self):
        self.monitor_ip = os.getenv('MONITOR_IP', '192.168.0.5')
        self.dev = None
        self.captured_ids = {}  # Store all captured physio IDs with their values
        
        # Known physio IDs for reference
        self.known_ids = {
            # NBP
            18949: "NBP_sys",
            18950: "NBP_dias", 
            18951: "NBP_mean",
            61669: "NBP_pulse",
            # SpO2
            19384: "SPO2",
            18466: "SPO2_pulse",
            # ECG
            16770: "ECG_pulse",
            # Art Press
            18963: "ART_press_mean",
            # Temperature (known IDs)
            19272: "MDC_TEMP",
            19296: "MDC_TEMP_BODY",
            19328: "MDC_TEMP_SKIN",
            19360: "MDC_TEMP_TYMP",
            19330: "MDC_TEMP_RECT",
            19298: "MDC_TEMP_CORE",
            19394: "MDC_TEMP_ESOPH",
            188420: "TEMP_188420",
            61639: "Philips_MP5_temp",
            61665: "T1_probe",
            61666: "T2_probe",
            61667: "T3_probe",
            61668: "T4_probe",
            57344: "Philips_temp_probe_57344",
            57346: "Philips_temp_probe_57346",
            188452: "Temp_differential",
            # Respiratory Rate (known IDs)
            20490: "MDC_RESP_RATE",
            20498: "MDC_AWAY_RESP_RATE",
            20514: "MDC_CO2_RESP_RATE",
            20482: "MDC_RESP",
            151562: "RESP_pleth_derived",
            20480: "RESP_impedance",
            53250: "RESP_53250",
            63528: "Philips_MP5_RR",
        }
        
    def log(self, message):
        """Print with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        # Also append to log file
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_probe_debug.log')
        with open(log_path, "a") as f:
            f.write(log_line + "\n")
    
    def run(self, duration_seconds=120):
        """Main debug loop using the same pattern as vital_sign_listener"""
        self.log("=" * 70)
        self.log("TEMPERATURE PROBE DEBUG SCRIPT")
        self.log(f"Monitor IP: {self.monitor_ip} (from .env)")
        self.log(f"Will run for {duration_seconds} seconds")
        self.log("=" * 70)
        self.log("")
        self.log("Instructions:")
        self.log("1. Wait for connection to establish")
        self.log("2. Take a temperature reading with the probe")
        self.log("3. Watch for new values in the Temp field")
        self.log("4. Also check for any UNKNOWN physio IDs that appear")
        self.log("")
        
        # Clear log file
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_probe_debug.log')
        with open(log_path, "w") as f:
            f.write(f"Debug session started at {datetime.now()}\n")
            f.write(f"Monitor IP: {self.monitor_ip}\n\n")
        
        try:
            # Initialize device connection (same as vital_sign_listener)
            self.log(f"Connecting to monitor at {self.monitor_ip}...")
            self.dev = device(self.monitor_ip)
            
            # Enable FULL debug mode on the device
            self.dev.debug_info = True
            self.dev.debug_error = True
            
            # Start the client (spawns background thread)
            self.dev.start_client()
            
            self.log("✓ Device connection started")
            self.log("Waiting for device to become active...")
            
            # Wait for connection to establish
            wait_count = 0
            while not self.dev.is_active and wait_count < 30:
                time.sleep(1)
                wait_count += 1
                self.log(f"  Waiting... ({wait_count}s)")
            
            if not self.dev.is_active:
                self.log("✗ Failed to connect to device after 30 seconds")
                return
            
            self.log("")
            self.log("=" * 70)
            self.log("✓ Connected! Now monitoring vital signs...")
            self.log("  Take a temperature reading with the probe now!")
            self.log("=" * 70)
            self.log("")
            
            last_temp = 0
            poll_count = 0
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time and self.dev.is_active:
                poll_count += 1
                
                # Get vital signs from device
                try:
                    vitals = self.dev.get_vital_signs()
                    patient = self.dev.get_patient_data()
                    
                    # Extract values
                    # vitals structure based on get_vital_signs() method:
                    # [0] NBP_sys, [1] NBP_dias, [2] NBP_mean, [3] NBP_pulse
                    # [4] NBP_time, [5] SPO2, [6] SPO2_pulse, [7] ECG_pulse
                    # [8] Time rel, [9] Time rel since power-on, [10] Connection start time
                    # [11] Temp, [12] Resp_rate
                    
                    current_temp = float(vitals[11][1]) if len(vitals) > 11 else 0
                    current_resp = float(vitals[12][1]) if len(vitals) > 12 else 0
                    current_spo2 = float(vitals[5][1]) if len(vitals) > 5 else 0
                    current_hr = float(vitals[7][1]) if len(vitals) > 7 else 0
                    
                    # Get p_temp directly from device object
                    p_temp = self.dev.p_temp
                    
                    # Check if temperature changed
                    if p_temp != last_temp and p_temp > 0:
                        self.log("")
                        self.log("⭐⭐⭐ TEMPERATURE VALUE DETECTED! ⭐⭐⭐")
                        self.log(f"    p_temp = {p_temp}")
                        self.log(f"    This could be from temp probe or manual entry")
                        self.log("")
                        last_temp = p_temp
                    
                    # Log current state periodically
                    if poll_count % 5 == 0:  # Every 10 seconds (2s poll interval * 5)
                        self.log(f"Poll #{poll_count}")
                        self.log(f"  Temp (p_temp): {p_temp}")
                        self.log(f"  Temp (vitals): {current_temp}")
                        self.log(f"  SpO2: {current_spo2}, HR: {current_hr}, RR: {current_resp}")
                        
                        # Show patient info
                        if patient:
                            p_id = patient[0][1] if patient[0][1] else "N/A"
                            p_name = patient[2][1] if patient[2][1] else "N/A"
                            self.log(f"  Patient: {p_name} (ID: {p_id})")
                    
                except Exception as e:
                    self.log(f"Error getting vitals: {e}")
                
                time.sleep(2)
            
            self.log("")
            self.log("=" * 70)
            self.log("DEBUG SESSION COMPLETED")
            self.log("=" * 70)
            self.log(f"Check the log file for all captured data: {log_path}")
            
        except KeyboardInterrupt:
            self.log("\nInterrupted by user")
            
        finally:
            # Cleanup
            if self.dev:
                try:
                    self.dev.halt_client()
                    self.log("Device connection closed")
                except:
                    pass


def main():
    # Allow optional command line arguments
    duration = 120  # Default 2 minutes
    
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Usage: python debug_temp_probe.py [duration_seconds]")
            print("Example: python debug_temp_probe.py 60")
            sys.exit(1)
    
    debugger = TempProbeDebugger()
    debugger.run(duration)


if __name__ == "__main__":
    main()
