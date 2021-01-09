#!/usr/bin/env python3
import os, sys, socket, traceback
from ssl import ALERT_DESCRIPTION_DECODE_ERROR
import json, time
from typing import List
import paho.mqtt.client as mqtt
from threading import Thread
from sensors import ds18b20, bme280, sht3x
from sensors.measurements import Measurement


class SensorAgent:
  mqtt_client     = None
  mqtt_connected  = False
  worker          = None

  ha_sensor_class_map = {
    Measurement.TEMPERATURE['name']:  'temperature',
    Measurement.HUMIDITY['name']:     'humidity',
    Measurement.LIGHT['name']:        'illuminance',
    Measurement.PRESSURE['name']:     'pressure',
    Measurement.PROXIMITY['name']:    None
  }

  default_config = {
    'update_period':  30,
    'verbose':        True,
    'host_device':    None,
    'sensor_types': [
      'ds18b20',
      'bme280',
      'sht3x'
    ],
    'sensor_name': None,
    'mqtt': {
      'broker':     None, # Must be overridden
      'port':       1883,
      'username':   None,
      'password':   None,
      'ha_prefix':  'homeassistant'
    },
    'precision': {
      'mqtt': {
        'temperature':  3,
        'pressure':     2,
        'humidity':     2,
        'proximity':    0,
        'lux':          5
      },
      'ha': {
        'temperature':  1,
        'pressure':     2,
        'humidity':     1,
        'proximity':    0,
        'lux':          5
      }
    }
  }


  def __init__(self, user_config):
    self.sensors = []
    # Merge user config with base config parameters;
    # user_config _must_ override ['mqtt']['broker']!
    self.config = { **self.default_config, **user_config }
    # Enumerate available sensors
    if len(self.config['sensor_types']) == 0:
      self.error("No sensor types were specified")
    else:
      for lib in self.config['sensor_types']:
        self.sensors.extend(globals()[lib].enumerate_sensors())

  def info(self, message):
    if self.config['verbose'] == True:
      sys.stdout.write('INFO: ' + message + '\n')
      sys.stdout.flush()

  def error(self, message):
    sys.stderr.write('ERROR: ' + message + '\n')
    sys.stderr.flush()

  def mqtt_connect(self):
    broker = "{}:{}".format(self.config['mqtt']['broker'], str(self.config['mqtt']['port']))
    if self.mqtt_broker_reachable():
      self.info("Connecting to MQTT broker at {} ...".format(broker))
      self.mqtt_client = mqtt.Client()
      if self.config['mqtt']['username'] is not None and self.config['mqtt']['password'] is not None:
        self.mqtt_client.username_pw_set(self.config['mqtt']['username'], self.config['mqtt']['password'])
      self.mqtt_client.on_connect = self.mqtt_on_connect
      self.mqtt_client.on_disconnect = self.mqtt_on_disconnect
      try:
        self.mqtt_client.connect(self.config['mqtt']['broker'], int(self.config['mqtt']['port']), 60)
        self.mqtt_client.loop_forever()
      except:
        self.error(traceback.format_exc())
        self.mqtt_client = None
    else:
      self.error("Unable to reach MQTT broker at {}".format(broker))

  def mqtt_on_connect(self, mqtt_client, userdata, flags, rc):
    self.mqtt_connected = True
    self.info('MQTT broker connected!')
    self.homeassistant_registration()

  def mqtt_on_disconnect(self, mqtt_client, userdata, rc):
    self.mqtt_connected = False
    self.info('MQTT broker disconnected! Will reconnect ...')
    if rc is 0:
      self.mqtt_connect()
    else:
      time.sleep(5)
      while not self.mqtt_broker_reachable():
        time.sleep(10)
      self.mqtt_client.reconnect()

  def mqtt_broker_reachable(self):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
      s.connect((self.config['mqtt']['broker'], int(self.config['mqtt']['port'])))
      s.close()
      return True
    except socket.error:
      return False

  def publish_message(self, topic, payload, qos=0, retain=False):
    if self.mqtt_connected:
      self.mqtt_client.publish(topic=topic, payload=str(payload), qos=qos, retain=retain)
    else:
      self.info("Message publishing is unavailable when the MQTT broker is not connected")


  def update(self):
    while True:
      for sensor in self.sensors:
        sensor.update_sensor()
        self.publish_message(topic="sensors/{}/status".format(sensor.id), payload="online")
        readings = {}
        for measurement in sensor.supported_measurements:
          val = getattr(sensor, measurement['name'])
          if measurement['name'] in self.config['precision']['mqtt']:
            p = self.config['precision']['mqtt'][measurement['name']]
            readings[measurement['name']] = round(val, p if p>0 else None)
          else:
            readings[measurement['name']] = val
        self.info("Publishing readings for sensor {}: {}".format(sensor.id, ", ".join(['{0}={1}'.format(k, v) for k,v in readings.items()])))
        self.publish_message(topic="sensors/{}/state".format(sensor.id), payload=json.dumps(readings))
      time.sleep(self.config['update_period'])


  def homeassistant_registration(self):
    for sensor in self.sensors:
      self.info("Publishing Home Assistant discovery information for sensor {}".format(sensor.id))
           
      device_info = {}
      device_info['identifiers']  = [ sensor.id ]
      device_info['manufacturer'] = sensor.manufacturer
      device_info['model']        = sensor.model
      if self.config['host_device'] is not None:
        device_info['via_device']   = self.config['host_device']
      device_info['name']         = "{} Environmental Sensor".format(sensor.model)

      for measurement in sensor.supported_measurements:
        uid = "{}-{}".format(sensor.id, measurement['name'])
        config_topic = "{}/sensor/{}/{}/config".format(self.config['mqtt']['ha_prefix'], sensor.id, uid)
        config_data = {}
        config_data['unique_id']              = uid
        config_data['state_topic']            = "sensors/{}/state".format(sensor.id)
        config_data['availability_topic']     = "sensors/{}/status".format(sensor.id)
        config_data['json_attributes_topic']  = "sensors/{}/attributes".format(sensor.id)
        config_data['device']                 = device_info
        config_data['device_class']           = self.ha_sensor_class_map[measurement['name']]
        config_data['unit_of_measurement']    = measurement['units']
        if self.config['sensor_name'] is not None:
          if type(self.config['sensor_name']) is dict and sensor.id in self.config['sensor_name']:
            sensor_name = str(self.config['sensor_name'][sensor.id])
          else:
            sensor_name = str(self.config['sensor_name'])
        else:
          sensor_name = "{} ({})".format(sensor.model, sensor.id)
        config_data['name']                 = "{} {}".format(sensor_name, measurement['name'].title())
        if measurement['name'] in self.config['precision']['ha']:
          round_filter = " | round({})".format(self.config['precision']['ha'][measurement['name']])
        else:
          round_filter = ''
        config_data['value_template']       = "{{{{ value_json.{}{} }}}}".format(measurement['name'], round_filter)
        config_data['force_update']         = True
        config_data['expire_after']         = int(self.config['update_period'])*2
        self.publish_message(topic=config_topic, payload=json.dumps(config_data, indent=2), qos=1, retain=True)

  def start(self):
    self.worker = Thread(target=self.update)
    self.worker.setDaemon(True)
    self.worker.start()
    self.mqtt_connect()
    