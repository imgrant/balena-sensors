from typing import Optional
from datetime import datetime
from busio import I2C
from board import SCL, SDA
import adafruit_tmp117
from .measurements import Measurement, MeasurementError

I2C_DEFAULT_ADDRESS = 0x48
I2C_SECONDARY_ADDRESS = 0x49

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in [ I2C_DEFAULT_ADDRESS, I2C_SECONDARY_ADDRESS ]:
    try:
      sensor = tmp117(i2c_dev=bus, i2c_addr=i2c_address)
    except (AttributeError, ValueError) as error:
      # If no TMP117 device is found, an AttributeError is raised (possibly ValueError if no device at address?)
      print("Error initialising TMP117 sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found TMP117 sensor with ID {} at I2C address {:#x}".format(sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


class tmp117(adafruit_tmp117.TMP117):

  manufacturer = 'Texas Instruments'
  model = 'TMP117'
  supported_measurements = [Measurement.TEMPERATURE]

  def __init__(self, i2c_dev=None,
               i2c_addr: Optional[int] = I2C_DEFAULT_ADDRESS):
    super().__init__(i2c_bus=i2c_dev, address=i2c_addr)

  def update_sensor(self):
    try:
      self._temperature = super().temperature
    except ValueError as error:
      raise MeasurementError(str(error))
    else:
      self.timestamp = datetime.now().isoformat(timespec='seconds')

  # Override super class property for temperature
  # because otherwise there's a name clash
  @property
  def temperature(self):
    return self._temperature

  @property
  def id(self):
    """A unique identifier (serial number) for the device."""
    return f'{self.serial_number:08x}'
