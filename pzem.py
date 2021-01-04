#!/usr/bin/python3

"""
Monitor a house electrical consumption and Post the measurements to influx database every 5 seconds.  
My electricity is supplied from either my electrical utility company or my small gasoline/propane 
portable generator.  My environment is a USA standard  200A residential house.  This script is
completely free, open source.
---Duane Thorpe, Janurary 2021.  

The house circuit panel is laid out with two main lines for 240VAC, with two phases 120V A&B.
One pzem016 sensor module is connected to each: mainA, mainB, and gen,
Total of three modules.  Sensor captures both A&B of Gen since Gen output is single phase.
The modules are powered from dedicated 15A breakers, corresponding to sensor phase.
USB adapter is attached to one of those breakers to power a raspberry Pi, external to the panel.

USB cables can be connected to any of the four RPi USB port connectors in any order.
pzem with slaveAddress 4 is sensing mainA
pzem with slaveAddress 5 is sensing mainB
pzem with slaveAddress 6 is sensing gen



pzem016 register definitions read using function 4
RegAddr Description                 Resolution
0x0000  Voltage value               1LSB correspond to 0.1V       
0x0001  Current value low 16 bits   1LSB correspond to 0.001A
0x0002  Current value high 16 bits  
0x0003  Power value low 16 bits     1LSB correspond to 0.1W
0x0004  Power value high 16 bits  
0x0005  Energy value low 16 bits    1LSB correspond to 1Wh
0x0006  Energy value high 16 bits 
0x0007  Frequency value             1LSB correspond to 0.1Hz
0x0008  Power factor value          1LSB correspond to 0.01
0x0009  Alarm status  0xFFFF is alarm，0x0000is not alarm

pzem016 register definitions read using function 3
RegAddr Description                 Resolution
0x0001  Power alarm threshhold      1LSB correspond to 1W
0x0002  Modbus-RTU address		    range is 0x0001 thru 0x00F7 (1 to 247), factory default is 1, 0 is broadcast


Make sure RPi raspi-config,Interfacing Options,  select “No” to login shell to be accessible over serial, 
then “Yes” to want to make use of the Serial Port Hardware is enabled.

$ Pip3 install minimalmodbus   # used to read pzem modules

$ sudo apt install python3-gpiozero   # used to get RPi cpu temperature


"""


import minimalmodbus		# main library to talk to PZEM devices via USB ports using Serial
import sys, requests, time
from time import sleep
from gpiozero import CPUTemperature          # internal RPi cpu sensor

#------------------------------------------------------------------------------------
#  Initialize Global variables

#  port names the OS gives to the first 3 detected devices for RPi3B+ 
#  may be different for your RPi or OS version.  Note if the RPi has power
#  from either the Electrical Power Company or by my generator, then all 
#  three pzems will be powered also.   
usb_RPi_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2']

# This inits each of the three instances with arguments of 
# RPi port name, pzem slaveAddress.   Each instance of pzX is attached to 
# the pzem slave address and cannot change.  The assigned RPi 
# port name can (and will likely) be changed during execution.
pzMainA = minimalmodbus.Instrument(usb_RPi_ports[1], 4)    # 
pzMainB = minimalmodbus.Instrument(usb_RPi_ports[2], 5)    # 
pzGen = minimalmodbus.Instrument(usb_RPi_ports[0], 6)    # 

usingGen = True   # true is generator power.  false is Utility Co. power. 

#------------------------------------------------------------------------------------

"""
	pairs up each pzem with a RPi port name.  If it can't
	comunicate with the pzem, it exits this program with a
	error message.  systemd should restart the script.
	"""

def set_RPi_ports():
	pzMainA.serial.baudrate = 9600
	pzMainA.serial.timeout = 0.2
	p = find_port(pzMainA)	# find the RPi port that is connected to pzem slaveAddress 4
	if p == None:			#  the pzems and RPi use same power, so this should never occur
		sys.exit("RPi cannot communicate with pzMainA, slaveAddress 4")
	pzMainA.serial.port = p		# set the port
	
	pzMainB.serial.baudrate = 9600
	pzMainB.serial.timeout = 0.2	
	p = find_port(pzMainB)
	if p == None:			#  the pzems and RPi use same power, so this should never occur
		sys.exit("RPi cannot communicate with pzMainB, slaveAddress 5")
	pzMainB.serial.port = p
	
	pzGen.serial.baudrate = 9600
	pzGen.serial.timeout = 0.2
	p = find_port(pzGen)
	if p == None:			#  the pzems and RPi use same power, so this should never occur
		sys.exit("RPi cannot communicate with pzGen, slaveAddress 6")
	pzGen.serial.port = p



def find_port(thispz):		# find the RPi port that is connected to pzem slaveAddress 
	for p in usb_RPi_ports:
		try:
			thispz.serial.port = p
			data = thispz.read_registers(1,2,4)       #  this attempts to read measured current
			return p    #  communication was sucessful so return port
		except:
			pass       # else there will be an error so try next port
	return None    # return None if there was no sucess--- should not happen



def test_if_using_gen():
	"""
	tries to get the current from gen, if there is even a little current,
	then must be using generator power.  Else using Utility Co. power.
	"""
	global usingGen			#  we are modifying global variable
	usingGen = False
	try:
		data = pzGen.read_registers(1,2,4)
		d = round(((data[0]+(data[1]<<16))*0.001),3) 
		if d > 0.3 :
			usingGen = True
	except:					# no communication on Gen means should be on Utility Co. power
		pass
	return usingGen
	


def read_meter():
	# first get the temperature of the raspberry pi cpu
	RPIcpu = CPUTemperature()      # create the object
	Tcpu = round(RPIcpu.temperature,1)   #  get the value, float.1, degC
	
	# now get the data from the PZE-016 sensors
	if usingGen:    # single phase
		for i in range(3):      # try 3 times before returning empty
			try:
				data = pzGen.read_registers(0,9,4)		#  Generator, read  the PZE-016 registers 0 thru 8 at once using function 4
				break
			except:
				data = None
		if data:	
			data_A = [
				round((data[0] * 0.1),1),                     	# Voltage(0.1V)
				round(((data[1]+(data[2] << 16)) * 0.001),3), 	# Current(0.001A)
				round(((data[3]+(data[4] << 16)) * 0.1),1),   	# Power(0.1W)
				int(((data[5]+(data[6] << 16))*1)),         	# Energy(1Wh)
				round((data[8]*0.01),2)  ]                    	# Power Factor(0.01)
			return data_A + [Tcpu]                            
		else: return  None   # data will be None
	
	
	else:    # must be using Utility Co. power so need to read both phases
		#  Main phase B
		for i in range(3):      # try 3 times before returning None
			try:
				data = pzMainA.read_registers(0,9,4)		#  Main phase A, read  the PZE-016 registers 0 thru 8 at once using function 4
				break
			except:
				data = None
		if data:	
			data_A = [
				round((data[0] * 0.1),1),                     	# Voltage(0.1V)
				round(((data[1]+(data[2] << 16)) * 0.001),3), 	# Current(0.001A)
				round(((data[3]+(data[4] << 16)) * 0.1),1),   	# Power(0.1W)
				int(((data[5]+(data[6] << 16))*1)),         	# Energy(1Wh)
				round((data[8]*0.01),2)  ]                    	# Power Factor(0.01)
		else: return None  # data will be None
		
		#  Main phase B
		for i in range(3):      # try 3 times before returning None
			try:
				data = pzMainB.read_registers(0,9,4)		#  Main phase B, read  the PZE-016 registers 0 thru 8 at once using function 4
				break
			except:
				data = None
		if data:	
			data_B = [
				round((data[0] * 0.1),1),                     	# Voltage(0.1V)
				round(((data[1]+(data[2] << 16)) * 0.001),3), 	# Current(0.001A)
				round(((data[3]+(data[4] << 16)) * 0.1),1),   	# Power(0.1W)
				int(((data[5]+(data[6] << 16))*1)),         	# Energy(1Wh)
				round((data[8]*0.01),2)  ]                    	# Power Factor(0.01)		
			return data_A + data_B + [Tcpu]	
		else: return None   # data will be None
	



def post_data():
	"""
	post data to InfluxDB which is running on the same RPi.

	"""
	meas = "ALL_SENSORS"
	pzemData = []
	if usingGen:
		field = ["GEN_VOLT", "GEN_AMPS", "GEN_WATT", "GEN_WHRS", "GEN_PZPF", "T_cpu"]		
	else:
		field = ["MAIN-A_VOLT", "MAIN-A_AMPS", "MAIN-A_WATT", "MAIN-A_WHRS", "MAIN-A_PZPF", 
		"MAIN-B_VOLT", "MAIN-B_AMPS", "MAIN-B_WATT", "MAIN-B_WHRS", "MAIN-B_PZPF", "T_cpu" ]	
				
	data = read_meter()		#  read all the PZE-016 registers at once
	#print ("data  ", data)
		
	if data:          # if data is  not None
		try:	
			for i in range (len(field)):
				# the "line protocol" format for the post to InfluxDB is measurement field=value.
				# must be one space between measurement and field and no other spaces in the line.
				# newline '\n' is allowed.
				pzemData.append('{} {}={}'.format(meas, field[i], data[i]))
				pData = '\n'.join(pzemData)
			
			#print (pData)
			
			# http post is not the most efficient, but it doesn't require any other libraries.
			# Post allows another remote device (pi or esp32 or... )to also post remotely to the InfluxDB.
			# The .write function of the InfluxDBClient may be a better technique.
			e = requests.post('http://192.168.1.49:8086/write?db=housePower', data=pData)		# post to inFluxDB on the same RPi
			
			#print ("post  ", e)   # the nornmal InfluxDB response is 204
		except:
			print ("error  ", e)
	else: pass      # TODO if no data, reset the PZEM016??




def setSlaveAddress(address):
	"""
	This is used only for initial testing, not used normally.
	Set a new slave address (1 to 247) for pzMainA. initially set to 1 from factory.
	Each device must have a unique address, Max of 31 devices per network.
	"""
   # return pzMainA.write_register(2,address,0,6)
	pass



def pzems_reset():
	"""
	 reset the PZE-016, but not sure what it really does.
	 it does NOT clear the assigned slaveAddress.  Not used,
	 but kept for reference purposes.
	"""
	pzMainA._performCommand(66, '')	  
	pzMainB._performCommand(66, '')	  
	pzGen._performCommand(66, '')	


		
def main():
	"""   
	Reads the pzem devices and posts to local InfluxDB approx every 5 minutes
	"""
	sleep(1)
	set_RPi_ports()
	if test_if_using_gen():
		print("pzem.py started monitoring generator power.")
	else: print("pzem.py started monitoring Utility Power Co. provided power.")
	
	while True:       # continuous loop of post measurements to InfluxDB -- sleep
		post_data()
		sleep(5)	# seconds. TODO may change to seperate cron schedule 

if __name__ == "__main__":
	main()
