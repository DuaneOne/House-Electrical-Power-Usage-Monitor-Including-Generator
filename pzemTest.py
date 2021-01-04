#!/usr/bin/env python3

"""
I found  this script on the internet and basically used it for first contact 
with each pzem to set the slaveAddress.  I pretty much used it as-is, with only minor changes.
The script has no loops, so it just executes once and exits.  
At the bottom, you can see various parts you can comment in/out to play around.

If not presiously installed on the Pi,  then   pip3 install minimalmodbus

to run:    python3 pzemTest.py

Driver for the PZEM-014 and PZEM-016 Energy monitors, for communication using the Modbus RTU protocol.
   ---- minor mods and comments only Duane Thorpe, Dec 2020

"""

__author__  = "Paul Burnell"        
__license__ = "TBC"

try:
	import minimalmodbus
except ImportError:
	print("Cannot import minimalmodbus, is it installed?\nExiting...")
	quit()

class pzem(minimalmodbus.Instrument):

	def __init__(self, serialPort, slaveAddress=1):
		"""
		Create monitor device instance
		"""
		try:
		       minimalmodbus.Instrument.__init__(self, serialPort, slaveAddress)
		       self.serial.timeout = 0.3
		       self.serial.baudrate = 9600
		except Exception as e:
			   print(e)

	def getData(self):
		"""
		Return array of [V, A, W, Wh, Hz, PF, alarm] values.
		"""
		for i in range(5):
			try:
				data = self.read_registers(0,10,4)
				break
			#except IOError as e:
			#   pass
			except Exception as e:
				print(e)
		if 'data' in locals():
			return [
				round((data[0]*0.1),1),                     # Voltage(0.1V)
				round(((data[1]+(data[2]*65536))*0.001),3), # Current(0.001A)
				round(((data[3]+(data[4]*65536))*0.1),1),   # Power(0.1W)
				int(((data[5]+(data[6]*65536))*1)),         # Energy(1Wh)
				round((data[7]*0.1),1),                     # Frequency(0.1Hz)
				round((data[8]*0.01),2),                    # Power Factor(0.01)
				int(data[9]>0)]                             # Alarm(1)
		else:
			return False

	def getVoltage(self):
		"""
		Return the line voltage (0.1V precision).
		"""
		return self.read_register(0,1,4)

	def getCurrent(self):
		"""
		Return the load current (0.001A precision).
		"""
		#return round((self.read_long(1,4)*0.001),3)
		data = self.read_registers(1,2,4)
		return round(((data[0]+(data[1]*65536))*0.001),3)

	def getPower(self):
		"""
		Return the real power (0.1W precision).
		"""
		#return round((self.read_long(3,4)*0.1),1)
		data = self.read_registers(3,2,4)
		return round(((data[0]+(data[1]*65536))*0.1),1)

	def getEnergy(self):
		"""
		Return the real energy (1Wh precision).
		"""
		#return self.read_long(5,4)
		data = self.read_registers(5,2,4)
		return int(data[0]+(data[1]*65536))

	def getFrequency(self):
		"""
		Return the line frequency (0.1Hz precision).
		"""
		return self.read_register(7,1,4)

	def getPowerFactor(self):
		"""Return the power factor (0.01 precision).
		"""
		return self.read_register(8,2,4)

	def getAlarmStatus(self):
		"""Return the alarm status (0 or 1 for True or False).
		"""
		return 1 if self.read_register(9,0,4) == 65535 else 0

	def getAlarmThreshold(self):
		"""
		Return the power alarm threshold (1W precision).
		"""
		return self.read_register(1,0,3)

	def setAlarmThreshold(self, watts):
		"""
		Set the power alarm threshold (1W precision).
		"""
		# alarmMax = 23000        # 2300 max for pzem014 or 23000 max for pzem016
		# if int(watts) > 0 and int(watts) <= alarmMax:
		try:
			self.write_register(1,watts,0,6)
			return True
		except Exception as e:
			pass
		return False

	def setZeroEnergy(self):
		"""
		Reset the energy accumulator total to zero.
		"""
		try: 
			self._performCommand(66,'')
		except Exception as e:
			return False
		return True

	def setSlaveAddress(self, address):
		"""
		Set a new slave address (1 to 247), initially set to 1 from factory.
		Each device must have a unique address, Max of 31 devices per network.
		"""
		return self.write_register(2,address,0,6)
	
	
	def getSlaveAddress(self):        
		return self.read_register(2,0,3)  # get slaveAddress
		

	#def setCalibration(self):                #  warning!   be certain if you use this.
	#    return self._performCommand(61,'')


if __name__ == "__main__":
	
	import time
	
	# several choices for testing
	
	serialPort = "/dev/ttyUSB0"    #  verified this works for Pi3B+ and factory pzem
	#serialPort = "/dev/ttyUSB1"
	#serialPort = "/dev/ttyUSB2"
	#serialPort = "/dev/serial0"
	#serialPort = "/dev/ttyS0"
	#serialPort = "ttyUSB001"
	


	# Using a slave address.   factory default is "1".
	slaveAddress = 1
	pz = pzem(serialPort, slaveAddress)

	# while True:
	#     print(' '.join(str(v) for v in [time.time(),pz.address]+pz.getData()))
	#     time.sleep(10)


	print (pz.getData())
	#print(pz.getPower())
	#print(pz.getEnergy())
	
	#print (pz.getSlaveAddress())     #  not too useful since you need to know the SA to send the command


	# #pz.setZeroEnergy()

	#pz.setSlaveAddress(6)      #  used 4,5,6 for houseMonitor
	
	#pz._performCommand(66, '')   # reset pzem (does not change the slave address)
	
	#print (pz.getData())

	# print(pz.setAlarmThreshold(22099))

	# print(pz.getAlarmThreshold())

