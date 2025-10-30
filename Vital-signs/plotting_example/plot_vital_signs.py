#!/usr/bin/python
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
from time import sleep
from  ipv_data_source import ipv_data_source as device
import os

class plot_vital_signs:
	
	def __init__(self, duration=60, init_timestamp_poll="00:00:00"):
		
		plt.axis([0, duration, 0, 200])
		plt.xlabel('minutes')
		plt.yticks(np.arange(0, 201, step=20))
		plt.xticks(np.arange(0, duration+1, step=5))
		plt.grid()
		
		
		green_patch = mpatches.Patch(color='#3ddc01', label='Heart rate')
		blue_patch = mpatches.Patch(color='#006eca', label='Oxygen saturation')
		red_patch = mpatches.Patch(color='red', label='Blood pressure')
		plt.legend(handles=[green_patch, blue_patch, red_patch])
		
		self.last_pl=0
		self.last_sa=0
		self.last_tm_pl=0
		self.last_tm_sa=0
		self.start_plot_pl=True
		self.start_plot_sa=True
	
	def set_patient_info(self, patient_name="", patient_id=""):
		"""Update plot title with patient information"""
		title = "Vital Signs Monitor"
		if patient_name or patient_id:
			title += "\n"
			if patient_name:
				title += f"Patient: {patient_name}"
			if patient_id:
				if patient_name:
					title += f" | "
				title += f"ID: {patient_id}"
		plt.title(title, fontsize=12, fontweight='bold')
		
	
	def write_vital_signs_to_file(self, patient_name="", patient_id="", heart_rate=0, oxygen=0, bp_sys=0, bp_dias=0, timestamp=None):
		"""Write vital signs data to text file when BP is captured"""
		try:
			filename = "vital_signs.txt"
			
			# Format timestamp
			if timestamp is None:
				timestamp = datetime.now()
			timestamp_str = timestamp.strftime('%d.%m.%Y %H:%M:%S')
			
			# Clean up patient data - remove extra spaces between characters
			patient_name = ' '.join(patient_name.split())
			patient_id = ' '.join(patient_id.split())
			
			# Format vital signs (values are already validated before being passed in)
			heart_rate_str = f"{heart_rate:.0f} bpm" if heart_rate > 0 else "N/A"
			oxygen_str = f"{oxygen:.1f}%" if oxygen > 0 else "N/A"
			
			# Prepare the data line
			data_line = f"{timestamp_str} | Patient: {patient_name} | ID: {patient_id} | Heart Rate: {heart_rate_str} | Oxygen: {oxygen_str} | BP: {bp_sys:.0f}/{bp_dias:.0f} mmHg\n"
			
			# Write to file (append mode)
			with open(filename, 'a') as f:
				f.write(data_line)
			
			print(f"Vital signs recorded: {patient_name} ({patient_id}) - HR: {heart_rate_str}, O2: {oxygen_str}, BP: {bp_sys:.0f}/{bp_dias:.0f}")
		except Exception as e:
			print(f"Error writing to vital signs file: {e}")
	
	def plot_new_values(self, time_stamp, RRsys=0, RRdias=0, Pulse=0, SaO2=0):
		if(((RRsys > 0)and(RRdias > 0))and((RRsys < 300)and(RRdias < 300))):
			plt.plot([time_stamp], [RRsys], 'rv', [time_stamp], [RRdias], 'r^')
			plt.plot([time_stamp,time_stamp], [RRsys,RRdias], color='r', linewidth=1)
		if((Pulse > 0)and(Pulse < 300)):
			if(self.start_plot_pl==True):
				self.last_pl=Pulse
				self.start_plot_pl=False
			plt.plot([self.last_tm_pl, time_stamp], [self.last_pl, Pulse], color='#3ddc01', marker='.', linewidth=1)
			self.last_pl=Pulse
			self.last_tm_pl=time_stamp
		if((SaO2 > 0)and(SaO2 < 150)):
			if(self.start_plot_sa==True):
				self.last_sa=SaO2
				self.start_plot_sa=False
			plt.plot([self.last_tm_sa, time_stamp], [self.last_sa, SaO2], color='#006eca', linewidth=1)
			self.last_sa=SaO2
			self.last_tm_sa=time_stamp
		#plt.text(30, 1, "txt", color='blue', fontsize=8)
		

#timescale of plot in min
duration=30

#insert correct monitor IP here
dev_1 = device("192.168.0.5")

plot_v = plot_vital_signs(duration)

dev_1.start_client()

dev_1.start_watchdog()

last_vital_time=0
last_NBP_time=datetime.strptime("01.01.1990 00:00:00",'%d.%m.%Y %H:%M:%S')

#track last displayed patient info to detect changes
last_patient_name = ""
last_patient_id = ""

#track last VALID heart rate and oxygen values
last_valid_heart_rate = 0
last_valid_oxygen = 0

#counter for periodic patient data refresh
refresh_counter = 0
refresh_interval = 10  # request patient data update every 10 iterations (~20 seconds)

try:
	while True:
		#get new patient data
		temp_l=dev_1.get_vital_signs()
		
		#periodically request patient data updates from the device
		refresh_counter += 1
		if refresh_counter >= refresh_interval:
			dev_1.refresh_patient_data()
			refresh_counter = 0
		
		#get and display patient information (update if changed)
		try:
			patient_data = dev_1.get_patient_data()
			patient_id = patient_data[0][1]  # ID
			patient_prename = patient_data[1][1]  # prename
			patient_name = patient_data[2][1]  # name
			full_name = f"{patient_prename} {patient_name}".strip()
		except:
			# If patient data fails, use last known values or defaults
			patient_id = last_patient_id if last_patient_id else "Unknown"
			full_name = last_patient_name if last_patient_name else "Unknown"
		
		#update plot title if patient info has changed
		if full_name != last_patient_name or patient_id != last_patient_id:
			if full_name or patient_id:
				plot_v.set_patient_info(full_name, patient_id)
				last_patient_name = full_name
				last_patient_id = patient_id
		###########################################
		#RR/SaO2
		#get time in minutes since connection started
		diff_time=((temp_l[8][1]*0.000125)/60)-((temp_l[9][1]*0.000125)/60)
		#if new data is available: plot data
		if(diff_time!=last_vital_time):
			current_oxygen = float(temp_l[5][1])
			current_heart_rate = float(temp_l[6][1])
			
			# Store last valid values (check for parsing errors - 8388607 or very large values)
			if current_heart_rate < 300 and current_heart_rate != 8388607:
				last_valid_heart_rate = current_heart_rate
			if current_oxygen <= 100 and current_oxygen != 8388607:
				last_valid_oxygen = current_oxygen
			
			plot_v.plot_new_values(diff_time, SaO2=current_oxygen, Pulse=current_heart_rate)
			last_vital_time=diff_time
		##########################################
		#NBP
		#get times
		v=temp_l[4][1]
		w=temp_l[10][1]
		#if time in minutes since connection started >0 and new data is available: plot data
		if(((v-w).total_seconds()>0)and(last_NBP_time!=v)):
			calc_time=(float((v-w).total_seconds())/60)
			bp_sys = float(temp_l[0][1])
			bp_dias = float(temp_l[1][1])
			
			# Use the last VALID heart rate and oxygen values (not the raw parsed values which might be invalid)
			# This prevents writing 8388607 error values when BP is captured
			print(f"BP captured - Time: {calc_time:.2f}min, BP: {bp_sys:.0f}/{bp_dias:.0f}, HR: {last_valid_heart_rate:.0f}, O2: {last_valid_oxygen:.1f}")
			
			# Plot the BP data
			plot_v.plot_new_values(calc_time, RRsys=bp_sys, RRdias=bp_dias)
			
			# Write all vital signs to file (BP capture acts as trigger)
			try:
				plot_v.write_vital_signs_to_file(
					patient_name=full_name,
					patient_id=patient_id,
					heart_rate=last_valid_heart_rate,
					oxygen=last_valid_oxygen,
					bp_sys=bp_sys,
					bp_dias=bp_dias,
					timestamp=v
				)
			except Exception as e:
				print(f"Warning: Could not write vital signs to file: {e}")
			
			last_NBP_time=v
		plt.pause(2)
		#plt.show()
#except (KeyboardInterrupt, SystemExit):
#	raise
except:
	dev_1.halt_client()
	print("\nclient halted...\n")
	plt.close()
	print("exit...[OK]")
