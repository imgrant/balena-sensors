from typing import Optional
from datetime import datetime
try:
    from smbus import SMBus
except ImportError:
    from smbus2 import SMBus
import bme280 as pimoroni_bme280
from .measurements import Measurement, MeasurementError


def enumerate_sensors():
  sensors = []
  bus = SMBus(1)
  for i2c_address in [pimoroni_bme280.I2C_ADDRESS_GND, pimoroni_bme280.I2C_ADDRESS_VCC]:
    try:
      sensor = bme280(i2c_addr=i2c_address, i2c_dev=bus)
    except RuntimeError as error:
      # If no BME280 is found, a RuntimeError is raised
      pass
    else:
      print("Found BME280 sensor with ID {} at I2C address {:#x}".format(sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


class bme280(pimoroni_bme280.BME280):

  manufacturer = 'Bosch'
  model = 'BME280'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.PRESSURE,
                            Measurement.HUMIDITY]

  def __init__(self,
               i2c_addr:  Optional[int]     = pimoroni_bme280.I2C_ADDRESS_GND,
               i2c_dev:   Optional[object]  = None):
    super().__init__(i2c_addr=i2c_addr, i2c_dev=i2c_dev)
    # Attempt to set up the sensor in "forced" mode
    # In this mode `update_sensor` will trigger
    # a new reading and wait for the result.
    # The chip will return to sleep mode when finished.
    self.setup(mode='forced')
    # Read device unique ID directly and store it in the class object
    # See: https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/Unique-IDs-in-Bosch-Sensors/m-p/6020/highlight/true#M62
    i = i2c_dev.read_i2c_block_data(i2c_addr,0x83,4)
    self.id = f'{(((i[3] + (i[2] << 8)) & 0x7fff) << 16) + (i[1] << 8) + i[0]:08x}'

  def update_sensor(self):
    try:
      super().update_sensor()
    except RuntimeError as error:
      raise MeasurementError(repr(error))
  
  @property
  def timestamp(self):
    return datetime.now().isoformat(timespec='seconds')