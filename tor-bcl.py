#!/usr/bin/python
#------------------------------------------
#
#    A script to control BerryClip LEDs
#    based on Tor relay bandwidth data
#
# Author : Luiz Kill
# Date   : 09/10/2014
#
# http://lzkill.com
#
#------------------------------------------

import os
import sys
import time
import random
import functools
import threading
import subprocess
import RPi.GPIO as GPIO
from stem.control import EventType, Controller, Signal
		  

LED_PIN = {
	1: 4,
	2: 17,
	3: 22,
	4: 10,
	5: 9,
	6: 11,
}


SW1_PIN = 7    # Switch 1
SW2_PIN = 25   # Switch 2
BZR_PIN = 8    # Buzzer

TOR_CONTROL_PORT = 9051
TOR_ADDRESS = "127.0.0.1"
TOR_CONTROLLER_PASSWD = ""

# See /etc/tor/torrc
tor_relay_bw_rate = None
tor_relay_bw_burst = None 
tor_bw_event_handler = None

SW_BOUNCE_DELAY = 200

LED_BOOT_DELAY = 5.0
LED_BLINK_DELAY = 0.1
LED_WARNING_DELAY = 5.0

BUZZER_SOUND_DELAY = 0.2

# LEDs 'power on/of'
led_feedback = True

# How long the script accumulates data before modifying the LEDs
STATS_DELAY = 1

INTERNET_CHECK_DELAY = 5.0
TOR_RECONNECT_DELAY = 5.0

# The Tor controller object
tor_controller = None

is_tor_alive = False

is_internet_on = False
is_network_up = True

DROP_NETWORK_CMD = "ifdown --force eth0"
RISE_NETWORK_CMD = "ifup eth0"

# (bytes downloaded, bytes uploaded) tuples for every second
tor_bandwidth = []

PING_TEST_IP = ["8.8.8.8"]


def main():
	GPIO.setmode(GPIO.BCM)

	try:

		boot()
		GPIO.add_event_detect(SW1_PIN, GPIO.FALLING, callback=sw1_handle, bouncetime=SW_BOUNCE_DELAY)
		GPIO.add_event_detect(SW2_PIN, GPIO.FALLING, callback=sw2_handle, bouncetime=SW_BOUNCE_DELAY)
		thread_start(tor_connect)
		thread_start(internet_check)

		while True:
			if led_feedback == True:
				if is_tor_alive == False:
					led_blink1(LED_BLINK_DELAY)

				elif is_network_up == False:
					led_blink2(LED_BLINK_DELAY)

				elif is_internet_on == False:
					led_blink3(LED_BLINK_DELAY)

			time.sleep(LED_WARNING_DELAY)

	except KeyboardInterrupt:
		print(time.ctime(), 'Script stopped by the user')
		pass

	except Exception as exc:
		print(time.ctime(),exc)

	finally:
		tor_disconnect()
		GPIO.cleanup()


def thread_start(t):
	t = threading.Thread(target=t)
	t.setDaemon(True)
	t.start()


def sw1_handle(channel):
	
	global led_feedback

	print(time.ctime(),'SW1 hit')
	# SW1 pressed => 'power' all LEDs on/off
	if led_feedback == True:
		led_set_all(False)
	led_feedback = not led_feedback


def sw2_handle(channel):

	global is_network_up

	print(time.ctime(),'SW2 hit')
	if is_network_up == True:
		tor_unbind()
		led_set_all(False)
		os.system(DROP_NETWORK_CMD)
	else:
		os.system(RISE_NETWORK_CMD)
		tor_bind()

	is_network_up = not is_network_up


def internet_check():
	global is_internet_on

	while True:
		is_internet_on = ping(PING_TEST_IP)
		
		if is_internet_on == False:
			print(time.ctime(),'Offline')		

		time.sleep(INTERNET_CHECK_DELAY)


def ping(ips):
	ip = random.choice(ips)
	# Use the system ping command with count of 1 and wait time of 1.
	ret = subprocess.call(['ping', '-c', '1', '-W', '1', ip],
	stdout=open('/dev/null', 'w'), stderr=open('/dev/null', 'w'))
	return ret == 0 # Return True if our ping command succeeds


def tor_connect():
	global is_tor_alive
	global tor_controller

	while True:
		if tor_controller == None:
			try:
				tor_controller = Controller.from_port(address=TOR_ADDRESS, port=TOR_CONTROL_PORT)
			except Exception as exc:
				print(time.ctime(),exc)

		elif tor_controller.is_authenticated() == False:
			try:
				tor_controller.authenticate(password=TOR_CONTROLLER_PASSWD)
			except Exception as exc:
				print(time.ctime(),exc)
			else:
				tor_get_conf()
				tor_bind()
					
		is_tor_alive = (tor_controller != None and tor_controller.is_authenticated())
		time.sleep(TOR_RECONNECT_DELAY)	
	
			
def tor_disconnect():
	global is_tor_alive
	global tor_controller

	if tor_controller:
		try:    
			tor_unbind()
			tor_controller.close()
			
		except Exception as exc:
			print(time.ctime(),exc)
			pass

		is_tor_alive = False
		tor_controller = None

		
def tor_die():
	if tor_controller:
		tor_controller.signal(Signal.SHUTDOWN)
		tor_disconnect()


def boot():
	for x in range(1,len(LED_PIN)+1):
		GPIO.setup(LED_PIN[x], GPIO.OUT, initial=False)

	# Set Buzzer as output
	GPIO.setup(BZR_PIN, GPIO.OUT, initial=False)

	# Set Switches GPIO as input
	GPIO.setup(SW1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(SW2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	sound_buzzer()

	led_blink1(LED_BOOT_DELAY)


def tor_get_conf():
	global tor_relay_bw_rate
	global tor_relay_bw_burst 

	tor_relay_bw_rate = float(tor_controller.get_conf('RelayBandwidthRate', '0', False))
	tor_relay_bw_burst = float(tor_controller.get_conf('RelayBandwidthBurst', '0', False))
	

def tor_bind():
	global tor_controller
	global tor_bw_event_handler
	if tor_controller:
		tor_bw_event_handler = functools.partial(handle_bandwidth_event)
		tor_controller.add_event_listener(tor_bw_event_handler, EventType.BW)


def tor_unbind():
	global tor_controller
	global tor_bw_event_handler
	if tor_controller:
		tor_controller.remove_event_listener(tor_bw_event_handler)


def handle_bandwidth_event(event):
	global tor_bandwidth

	# callback for when tor provides us with a BW event
	tor_bandwidth.append((event.read, event.written))
		
	if len(tor_bandwidth) == STATS_DELAY:
		if led_feedback == True:
			led_modify(tor_bandwidth)
		tor_bandwidth = []


def avg(l):
	return sum(l, 0.0) / len(l)

  
def led_modify(tor_bandwidth):
	download_bw = [entry[0] for entry in tor_bandwidth]
	upload_bw = [entry[1] for entry in tor_bandwidth]
	avg_download_bw = avg(download_bw)
	avg_upload_bw = avg(upload_bw)
	 
	half_burst = (tor_relay_bw_burst - tor_relay_bw_rate)/2

	# LED1
        if(avg_download_bw > 0):
                GPIO.output(LED_PIN[1], True)
        else:
                GPIO.output(LED_PIN[1], False)

        # LED2
        if(avg_download_bw >= tor_relay_bw_rate and avg_download_bw < (tor_relay_bw_rate + half_burst)):
                GPIO.output(LED_PIN[2], True)
        else:
                GPIO.output(LED_PIN[2], False)

        # LED3
        if(avg_download_bw >= (tor_relay_bw_rate + half_burst)):
                GPIO.output(LED_PIN[3], True)
        else:
                GPIO.output(LED_PIN[3], False)

        # LED4
        if(avg_upload_bw > 0):
                GPIO.output(LED_PIN[4], True)
        else:
                GPIO.output(LED_PIN[4], False)

        # LED5
        if(avg_upload_bw >= tor_relay_bw_rate and avg_upload_bw < (tor_relay_bw_rate + half_burst)):
                GPIO.output(LED_PIN[5], True)
        else:
                GPIO.output(LED_PIN[5], False)

        # LED6
        if(avg_upload_bw >= (tor_relay_bw_rate + half_burst)):
                GPIO.output(LED_PIN[6], True)
        else:
                GPIO.output(LED_PIN[6], False)


def led_set_all(status):
	global LED_PIN

	if led_feedback == True:
		for x in range(1,len(LED_PIN)+1):
			GPIO.output(LED_PIN[x], status)


def led_blink1(delay):
	if led_feedback == True:
		led_set_all(True)
		time.sleep(delay)
		led_set_all(False)


def led_blink2(delay):         
	if led_feedback == True:
		led_set_all(False)

		for x in range(1,len(LED_PIN)+1):
			 GPIO.output(LED_PIN[x], True)
			 time.sleep(delay)

		led_set_all(False)


def led_blink3(delay):         
	if led_feedback == True:
		led_set_all(False)

		for x in range(1,len(LED_PIN)+1):
			 GPIO.output(LED_PIN[x], True)
			 time.sleep(delay)

		for x in reversed(range(1,len(LED_PIN)+1)):
			 GPIO.output(LED_PIN[x], False)
			 time.sleep(delay)


def sound_buzzer():
	GPIO.output(BZR_PIN, True)
	time.sleep(BUZZER_SOUND_DELAY)
	GPIO.output(BZR_PIN, False)


if __name__ == '__main__':
	main()
	
