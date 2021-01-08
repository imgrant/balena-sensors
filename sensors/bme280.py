import sys
from typing import Optional
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
from bme280 import BME280
from .measurements import Measurement

I2C_ADDR_PRIMARY = 0x76
I2C_ADDR_SECONDARY = 0x77


def enumerate_sensors():
  sensors = []
  bus = SMBus(1)
  for i2c_address in [I2C_ADDR_PRIMARY, I2C_ADDR_SECONDARY]:
    try:
      sensor = bme280(i2c_addr=i2c_address, i2c_dev=bus)
      print("Found BME280 sensor with ID {} at I2C address {:#x}".format(sensor.id, i2c_address))
      sensors.append(sensor)
    except (RuntimeError) as error:
      # If no BME280 is found, a RuntimeError is raised
      pass
  return sensors


class bme280(BME280):

  manufacturer = 'Bosch'
  model = 'BME280'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.PRESSURE,
                            Measurement.HUMIDITY]

  def __init__(self,
               i2c_addr:  Optional[int]     = I2C_ADDR_PRIMARY,
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
