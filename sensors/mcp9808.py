from typing import Optional
from zlib import crc32
from datetime import datetime
from busio import I2C
from board import SCL, SDA
import adafruit_mcp9808
from .measurements import Measurement, MeasurementError

I2C_ADDRESSES = [ 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F ]

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in I2C_ADDRESSES:
    try:
      sensor = mcp9808(i2c_dev=bus, i2c_addr=i2c_address)
    except (OSError, AttributeError, ValueError) as error:
      # If no device is found, an AttributeError is raised (possibly ValueError if no device at address?)
      print("Error initialising MCP9808 sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found MCP9808 sensor with ID {:x} at I2C address {:#x}".format(sensor.serial_number, i2c_address))
      sensors.append(sensor)
  return sensors


class mcp9808(adafruit_mcp9808.MCP9808):

  manufacturer = 'Microchip Technology'
  model = 'MCP9808'
  supported_measurements = [Measurement.TEMPERATURE]

  def __init__(self, i2c_dev=None,
               i2c_addr: Optional[int] = I2C_ADDRESSES[0]):
    self.i2c_address = i2c_addr
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
    """A unique identifier for the device."""
    return f'{self.model.replace('-',''):s}--{self.serial_number:08x}'.lower()

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    # Doesn't look like the device supports reading a unique
    # identifier, this cobbles something together from the
    # sensor type and I2C address
    unique_string = ''.join("{}{}{:#x}".format(self.manufacturer, self.model, self.i2c_address).lower().split())
    return crc32(unique_string.encode())
