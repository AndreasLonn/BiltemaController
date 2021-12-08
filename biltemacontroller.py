#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Control Biltema outlets (35-392) using
    MQTT and Python on a Raspberry Pi

    Example of a Home Assistant configuration.yaml
    entry using the MQTT Switch integration:

    switch:
      - platform: mqtt
        name: "My light"
        unique_id: biltema.switch.1
        retain: true
        command_topic: "biltemactrl/switch/1"
        state_topic: "biltemactrl/switch/1/state"
        availability_topic: "biltemactrl/availability"
        device:
            name: "Biltema Switch Channel 1"
            manufacturer: "Biltema"
            model: "35-392"
            identifiers: "35-392.c1"
"""

import argparse

# Set up command line arguments
parser = argparse.ArgumentParser(
    description='Control Biltema outlets using MQTT and Python on a Raspberry Pi.')

parser.add_argument('-c', dest='path', required=True,
    help='Absolute path to config file')

args = parser.parse_args()

import configparser, queue, signal, sys, time, urllib, ast,\
    paho.mqtt.client as mqttClient, RPi.GPIO as GPIO
from datetime import datetime


# Read the config file specified in the command line arguments or, if
# none were given, use the config file set as default
config = configparser.ConfigParser(
    interpolation=configparser.ExtendedInterpolation())
config.read(args.path)

# Set up GPIO and pins
GPIO.setmode(GPIO.BCM)

pins = ast.literal_eval(config['GPIO']['pins'])

for pin in pins.values():
    GPIO.setup(pin[False], GPIO.OUT)
    GPIO.output(pin[False], GPIO.LOW)
    GPIO.setup(pin[True], GPIO.OUT)
    GPIO.output(pin[True], GPIO.LOW)

def triggerChannel(channel, state, output=False,
    delay=float(config['GPIO']['triggerDelay'])):
    try:
        # Set all pins to LOW at first
        for pin in pins.values():
            GPIO.output(pin[False], GPIO.LOW)
            GPIO.output(pin[True], GPIO.LOW)

        if output: log('High:', pins[channel][state])

        # Set specified pin to HIGH for the delay specified
        GPIO.output(pins[channel][state], GPIO.HIGH)

        time.sleep(delay)

        if output: log('Low:', pins[channel][state])

        GPIO.output(pins[channel][state], GPIO.LOW)

        time.sleep(delay)
    except Exception as e:
        log('An error occurred while trying to trigger pins:', e)

# Create array of topics for the switches
# by looping through the array of channels
channelTopics = [config['MQTT State']['topicPrefix'] + str(channel)\
    for channel in pins]

# Create a queue of messages to handle multiple messages comming in at once
# This because we can't send multiple commands through the GPIO at a time
msgQ = queue.Queue()

# Function to print to screen and log file
def log(*message, sep=' ', end='\n'):
    print(*message, sep=sep, end=end)
    try:
        logfile = open(config['Log']['logfile'], 'a')
        logfile.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S > '))
        for (i, m) in enumerate(message):
            if i > 0: logfile.write(sep)
            logfile.write(str(m))
        logfile.write(end)
        logfile.close()
    except Exception as e:
        print('An error occurred while logging:', e)

log('Starting up...')

# Wait until network is available
while True:
    try:
        response = urllib.request.urlopen(
            config['Broker']['urlToConnectivityTest'], timeout=1)
        break
    except urllib.error.URLError:
        log('Waiting for network...')
        time.sleep(1)
        pass

def on_connect(client, userdata, flags, rc):
    try:
        log('Connected')
        if rc==0:
            log('Setting up subscriptions')

            # Tell anyone listening that we're online
            sendMessage(config['MQTT Availability']['connectionTopic'],
                config['MQTT Availability']['payloadConnect'], retain=True)

            # Set up subscriptions
            for channelTopic in channelTopics:
                log('Subscribing to:', channelTopic)
                client.subscribe(channelTopic)
            log('Subscription set up completed')
        else:
            log('Bad connection Returned code:',rc)
    except Exception as e:
        log('An error occurred while setting up subscriptions:', e)

def on_message(client, userdata, msg):
    try:
        # Add incomming messages to the queue
        global msgQ
        msgQ.put(msg)
    except Exception as e:
        log('An error occurred while adding recieved message to queue:', e)

def sendMessage(topic, message, retain=False):
    log(f'Sending message "{message}" on topic "{topic}"')
    client.publish(topic, message, retain=retain)

# Set up and connect to broker
client = mqttClient.Client()
if config['Broker']['brokerUsername'] and config['Broker']['brokerPassword']:
    client.username_pw_set(config['Broker']['brokerUsername'],
        config['Broker']['brokerPassword'])
client.on_connect=on_connect
client.on_message=on_message

# Tell broker to send unavalability message if connection is lost
# without calling 'disconnect()'
client.will_set(config['MQTT Availability']['connectionTopic'],
    config['MQTT Availability']['payloadDisconnect'], retain=True)

log('Connecting to broker')
client.connect(config['Broker']['brokerURL'])

# Handle terminate signal from systemctl
def sigterm_handler(_signo, _stack_frame): sys.exit(0)
signal.signal(signal.SIGTERM, sigterm_handler)

try:
    # Start listening to MQTT messages
    client.loop_start()
    while True:
        try:
            # Handle messages
            msg = msgQ.get()

            # Read topic and payload
            topic = msg.topic
            payload = str(msg.payload.decode('utf-8'))

            if topic in channelTopics:
                values = payload.split(',')
                state = values[0]

                if state == config['MQTT State']['payloadOn']\
                    or\
                   state == config['MQTT State']['payloadOff']:

                    triggerChannel(
                        topic.removeprefix(config['MQTT State']['topicPrefix']),
                        state == config['MQTT State']['payloadOn'])

                    # Send new state
                    sendMessage(
                        topic + config['MQTT State']['topicStateSuffix'], state)
                else:
                    log('Unknown state:', state)
            else:
                log('Unknown topic:', topic)
        # Stop at KeyboardInterrupt:ions
        except KeyboardInterrupt: raise
        except Exception as e:
            log('An error occurred while handling recieved message:', e)
finally:
    # Send unavailability message, disconnect and clean up GPIO
    log('Cleaning up...')
    sendMessage(config['MQTT Availability']['connectionTopic'],
        config['MQTT Availability']['payloadDisconnect'], retain=True)
    client.disconnect()
    GPIO.cleanup()
    log('Done')
