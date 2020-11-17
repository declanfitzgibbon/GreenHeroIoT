import glob
import time
import RPi.GPIO as GPIO
import urllib.request
import requests
import json
import datetime
#import requests
#from pymongo import MongoClient

#DATABASE STUFF
#client = MongoClient('mongodb://localhost:27017')
#db = client.greenhero
#ac_state = Check current state of AC in DB (boolean)

#this is for the temp sensor to work
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

#this is for the motor to work
servoPIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(servoPIN, GPIO.OUT)
p = GPIO.PWM(servoPIN, 50)

#reads temp in computer format via temp sensor
def read_temp_raw():
	f = open(device_file, 'r')
	lines = f.readlines()
	f.close()
	return lines

#Translates raw temp to celcius for human reading.
#temp_c is celcius temp(float) and should update the temperature db table.
def read_temp():
	lines = read_temp_raw()
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		lines = read_temp_raw()
	equals_pos = lines[1].find('t=')
	if equals_pos != -1:
		temp_string = lines[1][equals_pos+2:]
		temp_c = float(temp_string) / 1000.0
		#tempBacknd = db.Temperature.insert_one({'temperature': temp_c})
		post_TemperatureRecord('https://greenhero.herokuapp.com/Temperature',temp_c)
		temp_f = temp_c * 9.0 / 5.0 + 32.0
		print('The temperature in celcius is: ')
		return temp_c

#Controls AC via the motor. First Reads from temp sensor. Then operates AC.
#Should post new AcState to DB
def control_temp():
	ac_state = get_LatestAcStateRecord('https://greenhero.herokuapp.com/AcState/getLatestAcState')
	temp_want = get_LatestTemperatureDesired('https://greenhero.herokuapp.com/TemperatureDesired/getLatestTemperatureDesired')
	lines = read_temp_raw()
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		lines = read_temp_raw()
	equals_pos = lines[1].find('t=')
	if equals_pos < temp_want and ac_state == True:
		p.start(2.5)
		time.sleep(2)
		p.ChangeDutyCycle(0)
		print('Turning off AC')
		post_AcStateRecord('https://greenhero.herokuapp.com/AcState',False)
		#return new ac_state to db
	elif equals_pos > temp_want and ac_state == False:
		p.start(10)
		time.sleep(2)
		p.ChangeDutyCycle(0)
		print('Turning on AC')
		post_AcStateRecord('https://greenhero.herokuapp.com/AcState', True)
	#return new_acstate to db
	elif equals_pos > temp_want and ac_state ==True:
		print('AC is already on')
	else:
		print('Temperature at suitable level. AC is off')

# This function can get all the temperature data in the database.
def get_TemperatureRecord(url):
	resp = urllib.request.urlopen(url)
	ele_json = json.loads(resp.read())
	return ele_json
# This function post a new temperature in current time to the database.
def post_TemperatureRecord(url,temperature):
	now_time = datetime.datetime.now()
	str_p = datetime.datetime.strftime(now_time, '%Y-%m-%dT%H:%M:%S.000Z')
	data = {
        	"time":  str_p,
            	"temperature": temperature
            	}
	data_json = json.dumps(data)
	headers = {'content-type': 'application/json'}
	r = requests.post(url, data=data_json, headers=headers)
	return
# This function get the latest state of AC.
def get_LatestAcStateRecord(url):
	resp = urllib.request.urlopen(url)
	ele_json = json.loads(resp.read())
	latestState = ele_json.get('state')
	return latestState

# Function to see the latest desired temperature
def get_LatestTemperatureDesired(url):
	resp = urllib.request.urlopen(url)
	ele_json = json.loads(resp.read())
	latestTemp = ele_json.get('temperatureDesired')
	return latestTemp

# This function post the current state of AC.
def post_AcStateRecord(url,ac_state):
	now_time = datetime.datetime.now()
	str_p = datetime.datetime.strftime(now_time, '%Y-%m-%dT%H:%M:%S.000Z')
	data = {
		"time":  str_p,
		"state": ac_state
		}
	data_json = json.dumps(data)
	headers = {'content-type': 'application/json'}
	r = requests.post(url, data=data_json, headers=headers)
	return

while True:
	print(read_temp())
	print(control_temp())
	time.sleep(5)
	p.stop()
	GPIO.cleanup()
