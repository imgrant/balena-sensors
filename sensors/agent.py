#!/usr/bin/env python3
import sys, socket, traceback
import json, time, importlib
from typing import List, Optional
import paho.mqtt.client as mqtt
from threading import Thread
from sensors.measurements import Measurement, MeasurementError


class SensorAgent:
  mqtt_client           = None
  mqtt_connected        = False
  ha_registered         = False
  attributes_published  = False
  worker                = None

  default_config = {
    'update_period':    30,
    'verbose':          True,
    'host_device':      None,
    'sensor_types':     [],    # Must be overriden with at least one sensor type module
    'sensor_location':  None,  # Can be a string, or dict with per-sensor entries, id->location
    'mqtt_broker':      None,  # Must be overridden
    'mqtt_port':        1883,
    'mqtt_username':    None,
    'mqtt_password':    None,
    'mqtt_ha_prefix':   'homeassistant',
    'precision_temperature':            1,
    'precision_pressure':               1,
    'precision_humidity':               1,
    'precision_proximity':              0,
    'precision_light':                  5,
    'precision_iaq':                    0,
    'precision_iaq_accuracy':           0,
    'precision_s_iaq':                  0,
    'precision_s_iaq_accuracy':         0,
    'precision_co2_equivalents':        0,
    'precision_breath_voc_equivalents': 0,
    'precision_gas_resistance':         0,
    'precision_gas_percentage':         1
  }


  def __init__(self, user_config):
    self.sensors = []
    self.sensor_types = {}
    # Merge user config with base config parameters;
    # user_config _must_ override 'mqtt.broker' and 'sensor_types'!
    self.config = { **self.default_config, **user_config }
    # Enumerate available sensors
    if self.config['sensor_types'] is None or len(self.config['sensor_types']) == 0:
      self.error("No sensor types were specified")
    else:
      for sensor_type in self.config['sensor_types']:
        self.sensor_types[sensor_type] = importlib.import_module("sensors.{}".format(sensor_type))
        self.sensors.extend(self.sensor_types[sensor_type].enumerate_sensors())
    if len(self.sensors) == 0:
      self.error("No sensors found")

  def info(self, message):
    if self.config['verbose'] == True:
      print("INFO: {}".format(message))

  def error(self, message):
    sys.exit("ERROR: {}".format(message))

  def mqtt_connect(self):
    broker = "{}:{}".format(self.config['mqtt_broker'], str(self.config['mqtt_port']))
    if self.mqtt_broker_reachable():
      self.info("Connecting to MQTT broker at {} ...".format(broker))
      self.mqtt_client = mqtt.Client()
      if self.config['mqtt_username'] is not None and self.config['mqtt_password'] is not None:
        self.mqtt_client.username_pw_set(self.config['mqtt_username'], self.config['mqtt_password'])
      self.mqtt_client.on_connect = self.mqtt_on_connect
      self.mqtt_client.on_disconnect = self.mqtt_on_disconnect
      try:
        self.mqtt_client.connect(self.config['mqtt_broker'], int(self.config['mqtt_port']), 30)
        self.mqtt_client.loop_forever()
      except:
        self.info(traceback.format_exc())
        self.mqtt_client = None
    else:
      self.error("Unable to reach MQTT broker at {}".format(broker))

  def mqtt_on_connect(self, mqtt_client, userdata, flags, rc):
    self.mqtt_connected = True
    self.info('MQTT broker connected!')
    if self.ha_registered is False:
      for sensor in self.sensors:
        self.publish_ha_discovery(sensor)
      self.ha_registered = True
    if self.attributes_published is False:
      for sensor in self.sensors:
        self.publish_attributes(sensor)
      self.attributes_published = True

  def mqtt_on_disconnect(self, mqtt_client, userdata, rc):
    self.mqtt_connected = False
    self.info('MQTT broker disconnected! Will reconnect ...')
    if rc == 0:
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
      s.connect((self.config['mqtt_broker'], int(self.config['mqtt_port'])))
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
        status_topic = "sensors/{}/status".format(sensor.id)
        try:
          sensor.update_sensor()
        except MeasurementError as error:
          self.publish_message(topic=status_topic, payload="offline")
          self.info("Failed to update measurements for sensor {} ({}). Sensor status will be set to offline.".format(sensor.id, str(error)))
        else:
          self.publish_message(topic=status_topic, payload="online")
          readings = {}
          readings['timestamp'] = str(getattr(sensor, 'timestamp'))
          for measurement in sensor.supported_measurements:
            # Round and format value to string for MQTT message
            value = getattr(sensor, measurement['name'])
            if value is not None:
              readings[measurement['name']] = round(value, measurement['precision'] if measurement['precision']>0 else None)
          self.info("Publishing readings for sensor {}: {}".format(sensor.id, ", ".join(['{0}={1}'.format(k, v) for k,v in readings.items()])))
          self.publish_message(topic="sensors/{}/state".format(sensor.id), payload=json.dumps(readings))
      time.sleep(self.config['update_period'])


  def publish_attributes(self, sensor):
    self.info("Publishing attributes for sensor {}".format(sensor.id))
    attr_data = {}
    attr_data['serial_number']  = sensor.id
    attr_data['type']           = sensor.model
    if self.config['sensor_location'] is not None:
      if type(self.config['sensor_location']) is dict:
        if sensor.id in self.config['sensor_location']:
          attr_data['location'] = str(self.config['sensor_location'][sensor.id])
      else:
        attr_data['location'] = str(self.config['sensor_location'])
    self.publish_message(topic="sensors/{}/attributes".format(sensor.id), payload=json.dumps(attr_data, indent=2), qos=1, retain=True)
  

  def publish_ha_discovery(self, sensor):
    self.info("Publishing Home Assistant discovery information for sensor {}:".format(sensor.id))
    device_info = {}
    device_info['identifiers']  = [ sensor.id ]
    device_info['manufacturer'] = sensor.manufacturer
    device_info['model']        = sensor.model
    if self.config['host_device'] is not None:
      device_info['via_device']   = self.config['host_device']
    device_info['name']         = "{} Environmental Sensor".format(sensor.model)

    for measurement in sensor.supported_measurements:
      self.info(" ... registering {} measurement".format(measurement['name']))
      uid = "{}-{}".format(sensor.id, measurement['name'])
      config_topic = "{}/sensor/{}/{}/config".format(self.config['mqtt_ha_prefix'], sensor.id, uid)
      config_data = {}
      config_data['unique_id']              = uid
      config_data['state_topic']            = "sensors/{}/state".format(sensor.id)
      config_data['availability_topic']     = "sensors/{}/status".format(sensor.id)
      config_data['json_attributes_topic']  = "sensors/{}/attributes".format(sensor.id) # See publish_attributes() above
      config_data['device']                 = device_info
      if measurement['ha_device_class'] is not None:
        config_data['device_class']           = measurement['ha_device_class']
      if measurement['units'] is not None:
        config_data['unit_of_measurement']    = measurement['units']
      config_data['name']                   = "{} ({}) {}".format(sensor.model, sensor.id, measurement['ha_title'])
      config_data['value_template']         = "{{{{ value_json.{} | round({}) }}}}".format(measurement['name'], self.config["precision_{}".format(measurement['name'])])
      config_data['force_update']           = True
      config_data['expire_after']           = int(self.config['update_period'])*2
      self.publish_message(topic=config_topic, payload=json.dumps(config_data, indent=2), qos=1, retain=True)


  def start(self):
    self.worker = Thread(target=self.update)
    self.worker.setDaemon(True)
    self.worker.start()
    self.mqtt_connect()
    