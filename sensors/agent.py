#!/usr/bin/env python3
import os, sys, socket, traceback
import json, time
import paho.mqtt.client as mqtt
from threading import Thread
from sensors import ds18b20, bme280, sht3x
from sensors.measurements import Measurement


class SensorAgent:
  mqtt_client     = None
  mqtt_connected  = False
  worker          = None

  ha_sensor_class_map = {
    'temperature':  'temperature',
    'humidity':     'humidity',
    'light':        'illuminance',
    'pressure':     'pressure',
    'proximity':    None
  }

  def __init__(self, config):
    self.sensors = []
    self.config = config

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
      
      if sensor.id in self.config['sensor_names']:
        friendly_name = self.config['sensor_names'][sensor.id]
      else:
        friendly_name = "Sensor {}".format(sensor.id)
      
      device_info = {}
      device_info['identifiers']  = [ sensor.id ]
      device_info['manufacturer'] = sensor.manufacturer
      device_info['model']        = sensor.model
      device_info['via_device']   = os.environ.get('BALENA_DEVICE_NAME_AT_INIT')
      device_info['name']         = "{} Environmental Sensor".format(friendly_name)

      for measurement in sensor.supported_measurements:
        uid = "{}--{}".format(sensor.id, measurement['name'])
        config_topic = "{}/sensor/{}/{}/config".format(self.config['mqtt']['ha_prefix'], sensor.id, uid)
        config_data = {}
        config_data['unique_id']            = uid
        config_data['state_topic']          = "sensors/{}/state".format(sensor.id)
        config_data['availability_topic']   = "sensors/{}/status".format(sensor.id)
        config_data['device']               = device_info
        config_data['device_class']         = self.ha_sensor_class_map[measurement['name']]
        config_data['unit_of_measurement']  = measurement['units']
        config_data['name']                 = "{} {}".format(friendly_name, measurement['name'].title())
        if measurement['name'] in self.config['precision']['ha']:
          round_filter = " | round({})".format(self.config['precision']['ha'][measurement['name']])
        else:
          round_filter = ''
        config_data['value_template']       = "{{{{ value_json.{}{} }}}}".format(measurement['name'], round_filter)
        config_data['force_update']         = True
        config_data['expire_after']         = int(self.config['update_period'])*2
        self.publish_message(topic=config_topic, payload=json.dumps(config_data, indent=2), qos=1, retain=True)


  def setup(self):
    for lib in self.config['sensor_types']:
      self.sensors.extend(globals()[lib].enumerate_sensors())

  def start(self):
    self.setup()
    self.worker = Thread(target=self.update)
    self.worker.setDaemon(True)
    self.worker.start()
    self.mqtt_connect()
    