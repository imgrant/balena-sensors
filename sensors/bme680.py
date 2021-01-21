from typing import Optional
from datetime import datetime
try:
    from smbus import SMBus
except ImportError:
    from smbus2 import SMBus
import subprocess, io, json, time
from threading import Thread
# Use the Pimoroni BME680 library to ease handling of probing the 
# chip ID, etc., even though we'll use the Bosch BSEC library later 
# to get access to the IAQ score output directly from the chip.
import bme680 as pimoroni_bme680
from .measurements import Measurement, MeasurementError


def enumerate_sensors():
  sensors = []
  bus = SMBus(1)
  for i2c_address in [pimoroni_bme680.constants.I2C_ADDR_PRIMARY, pimoroni_bme680.constants.I2C_ADDR_SECONDARY]:
    try:
      sensor = bme680(i2c_addr=i2c_address, i2c_dev=bus)
    except (IOError, RuntimeError) as error:
      # If no device is found, an IOError is raised;
      # if the chip ID doesn't match (i.e. it's not a BME680), RuntimeError is raised
      pass
    else:
      print("Found BME680 sensor with ID {} at I2C address {:#x}".format(sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


class bme680(pimoroni_bme680.BME680):

  manufacturer = 'Bosch'
  model = 'BME680'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.PRESSURE,
                            Measurement.HUMIDITY,
                            Measurement.AIR_QUALITY,
                            Measurement.IAQ_ACCURACY,
                            Measurement.STATIC_AIR_QUALITY,
                            Measurement.S_IAQ_ACCURACY,
                            Measurement.CO2_EQUIV,
                            Measurement.BVOC_EQUIV,
                            Measurement.GAS,
                            Measurement.GAS_PERCENT]

  bsec_command = [ '/opt/bsec/bsec_bme680' ]
  bsec_process = None
  bsec_data = {}

  def __init__(self,
               i2c_addr:  Optional[int]     = pimoroni_bme680.constants.I2C_ADDR_PRIMARY,
               i2c_dev:   Optional[object]  = None):
    # Call the Pimoroni BME680 class init() — if the sensor at the I2C address
    # is not a BME680, an error will be raised.
    super().__init__(i2c_addr=i2c_addr, i2c_device=i2c_dev)

    if i2c_addr == pimoroni_bme680.constants.I2C_ADDR_PRIMARY:
      self.bsec_command.extend( [ "primary" ] )
    elif i2c_addr == pimoroni_bme680.constants.I2C_ADDR_SECONDARY:
      self.bsec_command.extend( [ "secondary" ] )

    # Read device unique ID directly and store it in the class object
    # See: https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/Unique-IDs-in-Bosch-Sensors/m-p/6020/highlight/true#M62
    i = i2c_dev.read_i2c_block_data(i2c_addr,0x83,4)
    self.id = f'{(((i[3] + (i[2] << 8)) & 0x7fff) << 16) + (i[1] << 8) + i[0]:08x}'
    
    # Start the BSEC library process
    self.bsec_process = Thread(target=self.bsec_capture)
    self.bsec_process.start()


  def update_sensor(self):
    try:
      assert type(self.bsec_data) is dict, "Incorrect type: bsec_data is not a dictionary"
      for m in self.supported_measurements:
        assert m['name'] in self.bsec_data, "Reading not found: {} is not in bsec_data"
        assert type(self.bsec_data[m['name']]) is str, "Invalid JSON: bsec_data.{} is not a string".format(m['name'])
    except AssertionError as error:
      raise MeasurementError(repr(error))
    else:
      for key,value in self.bsec_data.items():
        setattr(self, key, float(value))

  @property
  def timestamp(self):
    return datetime.now().isoformat(timespec='seconds')

  def bsec_capture(self):
    bsec = subprocess.Popen(self.bsec_command, stdout=subprocess.PIPE)
    for line in io.TextIOWrapper(bsec.stdout, encoding="utf-8"):
      self.bsec_data = json.loads(line.strip())
    rc = bsec.poll()
    time.sleep(2)
    return rc
