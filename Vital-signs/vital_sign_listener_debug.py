#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Vital Sign Listener - DEBUG VERSION
====================================
This version logs ALL temperature-related physio IDs to help identify
the correct ID for temperature probe readings.

Run this instead of vital_sign_listener.py when debugging temperature probe.
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


class VitalSignListenerDebug:
    """Debug version - logs all temperature IDs"""
    
    def __init__(self):
        # Load configuration from environment variables
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000').rstrip('/')
        self.api_passphrase = os.getenv('API_PASSPHRASE', '')
        self.api_username = os.getenv('API_USERNAME', '')
        self.api_password = os.getenv('API_PASSWORD', '')
        self.monitor_ip = os.getenv('MONITOR_IP', '192.168.0.5')
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '2'))
        self.refresh_interval = int(os.getenv('REFRESH_INTERVAL', '10'))
        self.max_connection_errors = int(os.getenv('MAX_CONNECTION_ERRORS', '3'))
        self.reconnect_delay = int(os.getenv('RECONNECT_DELAY', '10'))
        
        # Track patient info
        self.last_patient_name = ""
        self.last_patient_id = ""
        
        # Track last valid vital signs
        self.last_valid_heart_rate = 0
        self.last_valid_oxygen = 0
        self.last_valid_temp = 0
        self.last_valid_resp_rate = 0
        
        # Debug: track all temperature values seen
        self.temp_history = []
        self.last_p_temp = 0
        
        # Log file for temperature debug
        self.temp_log_path = os.path.join(os.path.dirname(__file__), 'temp_probe_debug.log')
        
    def log(self, message, level="INFO"):
        """Print log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)
        
        # Also write to log file with UTF-8 encoding
        with open(self.temp_log_path, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    
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
    
    def connect_device(self):
        """Connect to the device with error handling"""
        dev = device(self.monitor_ip)
        
        # Enable FULL debug mode for temperature probe detection
        dev.debug_info = True
        dev.debug_error = True
        
        dev.start_client()
        dev.start_watchdog()
        
        return dev
    
    def run(self):
        """Main loop to listen for vital signs and send to API with auto-reconnect"""
        # Clear log file
        with open(self.temp_log_path, "w") as f:
            f.write(f"=== Temperature Probe Debug Session ===\n")
            f.write(f"Started: {datetime.now()}\n\n")
        
        self.log("=" * 70)
        self.log("VITAL SIGN LISTENER - DEBUG MODE FOR TEMPERATURE PROBE")
        self.log("=" * 70)
        self.log(f"Monitor IP: {self.monitor_ip}")
        self.log(f"API Server: {self.api_base_url}")
        self.log(f"Log File: {self.temp_log_path}")
        self.log("")
        self.log("This version logs ALL temperature values to help identify probe readings")
        self.log("Watch for *** markers when you take a probe temperature reading")
        self.log("=" * 70)
        
        # Check configuration
        if not self.api_username or not self.api_password:
            self.log("WARNING: No API credentials configured", "WARNING")
        if not self.api_passphrase:
            self.log("WARNING: No API passphrase configured", "WARNING")
        
        # Main connection loop with auto-reconnect
        while True:
            try:
                # Initialize device connection
                self.log(f"Connecting to monitor at {self.monitor_ip}...")
                dev = self.connect_device()
                self.log("✓ Device connection started")
                
                # Wait for connection to establish
                wait_count = 0
                while not dev.is_active and wait_count < 30:
                    time.sleep(1)
                    wait_count += 1
                    self.log(f"  Waiting for connection... ({wait_count}s)")
                
                if not dev.is_active:
                    self.log("✗ Failed to connect, will retry...", "ERROR")
                    time.sleep(self.reconnect_delay)
                    continue
                
                self.log("✓ Device is active!")
                
                # Initialize tracking variables
                last_vital_time = 0
                last_NBP_time = datetime.strptime("01.01.1990 00:00:00", '%d.%m.%Y %H:%M:%S')
                refresh_counter = 0
                connection_error_count = 0
                
                # Data collection loop
                self._data_collection_loop(dev, last_vital_time, last_NBP_time, refresh_counter, connection_error_count)
                
            except KeyboardInterrupt:
                self.log("Shutdown requested by user...")
                try:
                    dev.halt_client()
                    self.log("Client halted")
                except:
                    pass
                self.log("Exit...[OK]")
                break
                
            except Exception as e:
                self.log(f"Connection error: {e}", "ERROR")
                try:
                    dev.halt_client()
                except:
                    pass
                self.log(f"Reconnecting in {self.reconnect_delay} seconds...", "WARNING")
                time.sleep(self.reconnect_delay)
    
    def _data_collection_loop(self, dev, last_vital_time, last_NBP_time, refresh_counter, connection_error_count):
        """Inner loop for data collection with temperature debug"""
        poll_count = 0
        
        try:
            while True:
                poll_count += 1
                
                # Check if device is still active
                if not dev.is_active:
                    self.log("Device connection lost - will reconnect", "WARNING")
                    raise ConnectionError("Device connection inactive")
                
                # Get vital signs from device
                temp_l = dev.get_vital_signs()
                
                # Reset error counter on successful data retrieval
                connection_error_count = 0
                
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
                
                # ============================================================
                # DEBUG: Log temperature values from device
                # ============================================================
                current_p_temp = dev.p_temp  # Direct access to device's temp value
                
                # Get temp from vital signs array
                try:
                    current_temp = float(temp_l[11][1]) if len(temp_l) > 11 else 0
                    current_resp_rate = float(temp_l[12][1]) if len(temp_l) > 12 else 0
                except (IndexError, ValueError):
                    current_temp = 0
                    current_resp_rate = 0
                
                # Check if temperature changed (this is the key for detecting probe readings!)
                if current_p_temp != self.last_p_temp:
                    if current_p_temp > 0 and current_p_temp != 8388607:  # 8388607 is error value
                        self.log("")
                        self.log("*" * 60)
                        self.log("*** TEMPERATURE CHANGE DETECTED! ***")
                        self.log(f"*** p_temp: {self.last_p_temp} -> {current_p_temp}")
                        self.log("*** If you just used the probe, this is your reading!")
                        self.log("*" * 60)
                        self.log("")
                        
                        # Store in history
                        self.temp_history.append({
                            'time': datetime.now(),
                            'value': current_p_temp,
                            'poll': poll_count
                        })
                    
                    self.last_p_temp = current_p_temp
                
                # Log temperature status every 10 polls
                if poll_count % 10 == 0:
                    self.log(f"[Poll #{poll_count}] p_temp={current_p_temp}, temp_l[11]={current_temp}, RR={current_resp_rate}")
                
                # ============================================================
                # END DEBUG
                # ============================================================
                
                # Process SpO2 and Heart Rate
                diff_time = ((temp_l[8][1] * 0.000125) / 60) - ((temp_l[9][1] * 0.000125) / 60)
                
                if diff_time != last_vital_time:
                    current_oxygen = float(temp_l[5][1])
                    current_heart_rate = float(temp_l[6][1])
                    
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

                    # Ignore invalid BP readings (systolic < 10)
                    if bp_sys < 10:
                        last_NBP_time = v
                        continue
                    
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
                
        except Exception as e:
            # Log the error and let it bubble up to trigger reconnect
            self.log(f"Error in data collection: {e}", "ERROR")
            
            # Print temperature history before exiting
            if self.temp_history:
                self.log("")
                self.log("=== TEMPERATURE HISTORY ===")
                for entry in self.temp_history:
                    self.log(f"  {entry['time']}: {entry['value']}°C (poll #{entry['poll']})")
                self.log("===========================")
            
            raise


def main():
    """Entry point"""
    listener = VitalSignListenerDebug()
    listener.run()


if __name__ == "__main__":
    main()
