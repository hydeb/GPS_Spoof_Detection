#Used https://fishandwhistle.net/post/2016/using-pyserial-pynmea2-and-raspberry-pi-to-log-nmea-output/ as a base for this file

import pynmea2, serial, os, time, sys, glob, pytz, calendar
from datetime import datetime, timezone
TIME_THRESHOLD = 300 # Time in seconds
MINUTES_POSITION = 100
HOURS_POSITION = 10000
HOURS_PER_DAY = 24
NO_FIX = 1
FIX_2D = 2
FIX_3D = 3
TIME_ZONE_OFFSET = -5 #EDT = UTC-5:00

GPGSA_msg = pynmea2.parse("$GPGSA,A,1,,,,,,,,,,,,,99.99,99.99,99.99*30")
msg = GPGSA_msg

def _scan_ports():
	if sys.platform.startswith('win'):
		ports = ['COM%s' % (i + 1) for i in range(256)]
	elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
		# this excludes your current terminal "/dev/tty"
		patterns = ('/dev/tty[A-Za-z]*', '/dev/ttyUSB*')
		ports = [glob.glob(pattern) for pattern in patterns]
		ports = [item for sublist in ports for item in sublist]  # flatten
	elif sys.platform.startswith('darwin'):
		patterns = ('/dev/*serial*', '/dev/ttyUSB*', '/dev/ttyS*')
		ports = [glob.glob(pattern) for pattern in patterns]
		ports = [item for sublist in ports for item in sublist]  # flatten
	else:
		raise EnvironmentError('Unsupported platform')
	return ports

def logfilename():
	now = datetime.now()
	return 'NMEA_%0.4d-%0.2d-%0.2d_%0.2d-%0.2d-%0.2d.nmea' % \
				(now.year, now.month, now.day,
				 now.hour, now.minute, now.second)

current_datetime = datetime.utcnow()
print(current_datetime)
current_timetuple = current_datetime.utctimetuple()
print(current_timetuple)
current_timestamp = calendar.timegm(current_timetuple)
print(current_timestamp)

try:
	while True:
		ports = _scan_ports()
		if len(ports) == 0:
			sys.stderr.write('No ports found, waiting 10 seconds...press Ctrl-C to quit...\n')
			time.sleep(10)
			continue

		for port in ports:
			# try to open serial port
			sys.stderr.write('Trying port %s\n' % port)
			try:
				# try to read a line of data from the serial port and parse
				with serial.Serial(port, 4800, timeout=1) as ser:
					# 'warm up' with reading some input
					for i in range(10):
						ser.readline()
					# try to parse (will throw an exception if input is not valid NMEA)
					pynmea2.parse(ser.readline().decode('ascii', errors='replace'))
				
					# log data
					outfname = logfilename()
					sys.stderr.write('Logging data on %s to %s\n' % (port, outfname))
					with open(outfname, 'wb') as f:
						# loop will exit with Ctrl-C, which raises a
						# KeyboardInterrupt
						while True:
							line = ser.readline()
							print(line.decode('ascii', errors='replace').strip())
							f.write(line)
							
							msg = pynmea2.parse(line.decode('ascii', errors='replace').strip())
							#msg2 = pynmea2.parse(line)
							#print(f"{msg=}")
							print("messages:", repr(type(msg)))
							if 'GSA' in repr(type(msg)):
								# Save GPGSA message to check the GPS fix
								GPGSA_msg = msg
								print("GPGSA message:", msg)
							if ('RMC' in repr(type(msg))) and (FIX_2D <= int(GPGSA_msg.mode_fix_type)):
								print("Message timestamp:", msg.timestamp)
								print("Message date:", msg.datetime)
								# UTC time status of position (hours/minutes/seconds/ decimal seconds), hhmmss.ss, eg. 202134.00
								gps_utc_time = (HOURS_POSITION * msg.timestamp.hour) + (MINUTES_POSITION * msg.timestamp.minute) + msg.timestamp.second
								gps_utc_date = msg.datetime
								print("gps_utc_date", gps_utc_date)
								now = datetime.utcnow()
								#u = u.replace(tzinfo=pytz.utc) #NOTE: it works only with a fixed utc offset
								print ("utctime: ", now)
								#now = datetime.now()
								sys_time_utc = now.replace(tzinfo=timezone.utc).timestamp()
								print("sys_time_utc", sys_time_utc)
								print('Current time (UTC):', int(sys_time_utc))
								
								msg_timetuple = gps_utc_date.utctimetuple()
								print(msg_timetuple)
								msg_timestamp = calendar.timegm(msg_timetuple)
								print(msg_timestamp)
								a = int(sys_time_utc)-msg_timestamp
								print("int(sys_time_utc)-msg_timestamp = ", a)
								if abs(int(sys_time_utc)-msg_timestamp)>TIME_THRESHOLD:
									#f = open("logfile.txt", "a")
									warning_message = "WARNING; GPS spoofing is likely occuring. Timestamp:" + str(msg.timestamp) + "\n"
									print(warning_message)
									#f.write(warning_message)
									#f.close()
				
			except Exception as e:
				sys.stderr.write('Error reading serial port %s: %s\n' % (type(e).__name__, e))
			except KeyboardInterrupt as e:
				sys.stderr.write('Ctrl-C pressed, exiting log of %s to %s\n' % (port, outfname))

		sys.stderr.write('Scanned all ports, waiting 10 seconds...press Ctrl-C to quit...\n')
		time.sleep(10)
except KeyboardInterrupt:
	sys.stderr.write('Ctrl-C pressed, exiting port scanner\n')