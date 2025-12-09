#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Vital Sign Listener
Listens to vital signs from medical monitor device and sends to API server.
No graphical plotting - headless operation for server/background use.
"""

import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from ipv_data_source import ipv_data_source as device

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class VitalSignListener:
    """Listens to vital signs and sends them to API server"""
    
    def __init__(self):
        # Load configuration from environment variables
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000').rstrip('/')
        self.api_passphrase = os.getenv('API_PASSPHRASE', '')
        self.api_username = os.getenv('API_USERNAME', '')
        self.api_password = os.getenv('API_PASSWORD', '')
        self.monitor_ip = os.getenv('MONITOR_IP', '192.168.0.5')
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '2'))
        self.refresh_interval = int(os.getenv('REFRESH_INTERVAL', '10'))
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
        # Track patient info
        self.last_patient_name = ""
        self.last_patient_id = ""
        
        # Track last valid vital signs
        self.last_valid_heart_rate = 0
        self.last_valid_oxygen = 0
        self.last_valid_temp = 0
        self.last_valid_resp_rate = 0
        
    def log(self, message, level="INFO"):
        """Print log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")
    
    def send_vital_signs(self, patient_name="", patient_id="", heart_rate=0, oxygen=0, 
                         bp_sys=0, bp_dias=0, temperature=0, resp_rate=0, timestamp=None):
        """Send vital signs data to the API server (per-request authentication)"""
        try:
            api_url = f"{self.api_base_url}/vital-signs"
            
            # Format timestamp
            if timestamp is None:
                timestamp = datetime.now()
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # Clean up patient data
            patient_name = ' '.join(patient_name.split())
            patient_id = ' '.join(patient_id.split())
            
            # Prepare API payload with authentication credentials in body
            payload = {
                "username": self.api_username,
                "password": self.api_password,
                "patient_code": patient_id,  # Required field
                "measured_at": timestamp_str
            }
            
            # Add optional fields only if they have valid values
            if bp_sys > 0 and bp_sys < 300:
                payload["blood_pressure_systolic"] = int(bp_sys)
            
            if bp_dias > 0 and bp_dias < 200:
                payload["blood_pressure_diastolic"] = int(bp_dias)
            
            if heart_rate > 0 and heart_rate < 300:
                payload["pulse_rate"] = int(heart_rate)
            
            if oxygen > 0 and oxygen <= 100:
                payload["spo2"] = round(oxygen, 1)
            
            if temperature > 20 and temperature < 50:
                payload["temperature"] = round(temperature, 1)
            
            if resp_rate > 0 and resp_rate < 100:
                payload["respiratory_rate"] = int(resp_rate)
            
            # Set headers with X-Passphrase
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Passphrase": self.api_passphrase
            }
            
            # Send POST request to API
            response = requests.post(api_url, json=payload, headers=headers, timeout=5)
            
            # Check response
            if response.status_code in [200, 201]:
                response_data = response.json()
                patient_info = f"{patient_name} ({patient_id})" if patient_name else f"ID: {patient_id}"
                vitals_str = f"HR: {heart_rate:.0f}, O2: {oxygen:.1f}%, BP: {bp_sys:.0f}/{bp_dias:.0f}"
                if temperature > 0:
                    vitals_str += f", Temp: {temperature:.1f}°C"
                if resp_rate > 0:
                    vitals_str += f", RR: {resp_rate:.0f}"
                self.log(f"✓ Vital signs sent: {patient_info} - {vitals_str}")
                return True
            else:
                self.log(f"✗ API Error ({response.status_code}): {response.text}", "ERROR")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log(f"✗ Connection Error: Cannot reach API at {api_url}", "ERROR")
            return False
        except requests.exceptions.Timeout:
            self.log("✗ Timeout Error: API did not respond in time", "ERROR")
            return False
        except Exception as e:
            self.log(f"✗ Error sending vital signs: {e}", "ERROR")
            return False
    
    def run(self):
        """Main loop to listen for vital signs and send to API"""
        self.log("=" * 60)
        self.log("Vital Sign Listener Starting...")
        self.log(f"Monitor IP: {self.monitor_ip}")
        self.log(f"API Server: {self.api_base_url}")
        self.log(f"API Endpoint: {self.api_base_url}/vital-signs")
        if self.debug_mode:
            self.log("Debug mode: ENABLED")
        self.log("=" * 60)
        
        # Check configuration
        if not self.api_username or not self.api_password:
            self.log("WARNING: No API credentials configured", "WARNING")
        if not self.api_passphrase:
            self.log("WARNING: No API passphrase configured", "WARNING")
        
        # Initialize device connection
        self.log(f"Connecting to monitor at {self.monitor_ip}...")
        dev = device(self.monitor_ip)
        
        # Enable device debug mode if debug is enabled
        if self.debug_mode:
            dev.debug_info = True
        
        dev.start_client()
        dev.start_watchdog()
        
        self.log("✓ Device connection started")
        
        # Initialize tracking variables
        last_vital_time = 0
        last_NBP_time = datetime.strptime("01.01.1990 00:00:00", '%d.%m.%Y %H:%M:%S')
        refresh_counter = 0
        
        try:
            while True:
                # Get vital signs from device
                temp_l = dev.get_vital_signs()
                
                # Periodically request patient data updates
                refresh_counter += 1
                if refresh_counter >= self.refresh_interval:
                    dev.refresh_patient_data()
                    refresh_counter = 0
                
                # Get patient information (name is optional, only ID is required)
                try:
                    patient_data = dev.get_patient_data()
                    patient_id = str(patient_data[0][1]).strip() if patient_data[0][1] else ""
                    patient_prename = str(patient_data[1][1]).strip() if patient_data[1][1] else ""
                    patient_name = str(patient_data[2][1]).strip() if patient_data[2][1] else ""
                    full_name = f"{patient_prename} {patient_name}".strip()
                    
                    # Use last known values if current values are empty
                    if not patient_id:
                        patient_id = self.last_patient_id if self.last_patient_id else ""
                    if not full_name:
                        full_name = self.last_patient_name if self.last_patient_name else ""
                except Exception as e:
                    # Silently use last known values on error
                    patient_id = self.last_patient_id if self.last_patient_id else ""
                    full_name = self.last_patient_name if self.last_patient_name else ""
                
                # Update if patient info has changed
                if full_name != self.last_patient_name or patient_id != self.last_patient_id:
                    if patient_id:  # Only log if we have at least an ID
                        if full_name:
                            self.log(f"Patient: {full_name} (ID: {patient_id})")
                        else:
                            self.log(f"Patient ID: {patient_id}")
                        self.last_patient_name = full_name
                        self.last_patient_id = patient_id
                
                # Process SpO2 and Heart Rate
                diff_time = ((temp_l[8][1] * 0.000125) / 60) - ((temp_l[9][1] * 0.000125) / 60)
                
                if diff_time != last_vital_time:
                    current_oxygen = float(temp_l[5][1])
                    current_heart_rate = float(temp_l[6][1])
                    
                    # Safely get temp and resp_rate (may not exist on all devices)
                    try:
                        current_temp = float(temp_l[11][1]) if len(temp_l) > 11 else 0
                        current_resp_rate = float(temp_l[12][1]) if len(temp_l) > 12 else 0
                    except (IndexError, ValueError):
                        current_temp = 0
                        current_resp_rate = 0
                    
                    # Debug mode: show raw values from device
                    if self.debug_mode:
                        self.log(f"[DEBUG] Raw values - HR: {current_heart_rate}, O2: {current_oxygen}, "
                                f"Temp: {current_temp}, RR: {current_resp_rate}", "DEBUG")
                    
                    # Store last valid values (filter out error values like 8388607)
                    if current_heart_rate < 300 and current_heart_rate != 8388607:
                        self.last_valid_heart_rate = current_heart_rate
                    if current_oxygen <= 100 and current_oxygen != 8388607:
                        self.last_valid_oxygen = current_oxygen
                    if current_temp > 20 and current_temp < 50 and current_temp != 8388607:
                        self.last_valid_temp = current_temp
                    if current_resp_rate > 0 and current_resp_rate < 100 and current_resp_rate != 8388607:
                        self.last_valid_resp_rate = current_resp_rate
                    
                    last_vital_time = diff_time
                
                # Process NBP (Blood Pressure) - triggers API send
                v = temp_l[4][1]  # NBP timestamp
                w = temp_l[10][1]  # Connection start time
                
                if (((v - w).total_seconds() > 0) and (last_NBP_time != v)):
                    calc_time = float((v - w).total_seconds()) / 60
                    bp_sys = float(temp_l[0][1])
                    bp_dias = float(temp_l[1][1])
                    
                    patient_info = f"{full_name} ({patient_id})" if full_name else f"ID: {patient_id}"
                    vitals_str = f"BP: {bp_sys:.0f}/{bp_dias:.0f}, HR: {self.last_valid_heart_rate:.0f}, O2: {self.last_valid_oxygen:.1f}"
                    if self.last_valid_temp > 0:
                        vitals_str += f", Temp: {self.last_valid_temp:.1f}°C"
                    if self.last_valid_resp_rate > 0:
                        vitals_str += f", RR: {self.last_valid_resp_rate:.0f}"
                    self.log(f"BP captured - {patient_info} - Time: {calc_time:.2f}min, {vitals_str}")
                    
                    # Send vital signs to API (BP capture acts as trigger)
                    # Only send if we have a patient ID (required by API)
                    if patient_id:
                        self.send_vital_signs(
                            patient_name=full_name,
                            patient_id=patient_id,
                            heart_rate=self.last_valid_heart_rate,
                            oxygen=self.last_valid_oxygen,
                            bp_sys=bp_sys,
                            bp_dias=bp_dias,
                            temperature=self.last_valid_temp,
                            resp_rate=self.last_valid_resp_rate,
                            timestamp=v
                        )
                    else:
                        self.log("✗ Cannot send vital signs: No patient ID available", "WARNING")
                    
                    last_NBP_time = v
                
                # Wait before next poll
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            self.log("Shutdown requested by user...")
        except Exception as e:
            self.log(f"Error in main loop: {e}", "ERROR")
        finally:
            dev.halt_client()
            self.log("Client halted")
            self.log("Exit...[OK]")


def main():
    """Entry point"""
    listener = VitalSignListener()
    listener.run()


if __name__ == "__main__":
    main()

