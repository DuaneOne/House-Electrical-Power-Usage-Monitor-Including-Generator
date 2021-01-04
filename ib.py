#!/usr/bin/python3

"""
InfluxDB backup script.   Backs up the entire DB to the external USB drive pluigged 
into the RPi.   The /media folder is standard location to map to USB drives.  
The backups are stored in seperate subfolders by date. This script is
completely free, open source.
---Duane Thorpe, Janurary 2021.  

********TODO************* write another script to mount then wait for user input before unmount. 
 This would allow you to see the files using sudo ls or FileZilla.
"""



import os, sys
from datetime import date

today = date.today()
dt = today.strftime("%Y_%m_%d")

# First create the folder
folder = "/media/influx-backup/" + dt
command = "sudo mkdir " + folder
os.system(command)


# mount the USB drive (assumes only one drive is plugged in)
# -o allows you to add extra options. 
# umask option to allows everyone user to read/write on the device
command = "sudo mount /dev/sda1 " + folder + " -o umask=000"
os.system(command)

#  verify drive is mounted
command = "lsblk /dev/sda1"
result = os.system(command)  # 0 = sucess
if result:
	sys.exit("ERROR - USB drive cannot be mounted - InfluxDB NOT backedup")
		

# issue the backup command to influxDB
command = "sudo influxd backup -portable " + folder
os.system(command)

# un-mount the USB drive folder
# After the drive is unmounted, you cannot see the individual files using sudo ls or FileZilla
# Copy this to look at files   sudo mount /dev/sda1 /media/influx-backup
# copy this to unmount   sudo umount /dev/sda1
command = "sudo umount /dev/sda1"
os.system(command)

print("InfluxDB Backup Finished ", dt)