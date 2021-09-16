from typing import Optional
from datetime import datetime
from zlib import crc32
try:
    from smbus import SMBus
except ImportError:
    from smbus2 import SMBus
import ltr559 as pimoroni_ltr559
from .measurements import Measurement, MeasurementError

I2C_ADDRESSES = [ 0x23 ]

def enumerate_sensors():
  sensors = []
  bus = SMBus(1)
  for i2c_address in I2C_ADDRESSES:
    try:
      sensor = ltr559(i2c_addr=i2c_address, i2c_dev=bus)
    except (OSError, ValueError, RuntimeError) as error:
      # If no device is found, a ValueError is raised;
      # if the chip ID doesn't match (i.e. it's not an LTR-559), RuntimeError is raised
      print("Error initialising LTR-559 sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found LTR-559 sensor with ID {:x} at I2C address {:#x}".format(sensor.serial_number, i2c_address))
      sensors.append(sensor)
  return sensors


class ltr559(pimoroni_ltr559.LTR559):

  manufacturer = 'LITE-ON'
  model = 'LTR-559'
  supported_measurements = [Measurement.LIGHT,
                            Measurement.PROXIMITY]

  def __init__(self,
               i2c_addr:  Optional[int]     = I2C_ADDRESSES[0],
               i2c_dev:   Optional[object]  = None):
    super().__init__(i2c_dev=i2c_dev)
    self.i2c_address = i2c_addr

  def update_sensor(self):
    try:
      super().update_sensor()
    except ValueError as error:
      raise MeasurementError(str(error))
    else:
      self.timestamp = datetime.now().isoformat(timespec='seconds')

  @property
  def light(self):
    return self.get_lux(passive=True)

  @property
  def proximity(self):
    return self.get_proximity(passive=True)

  @property
  def id(self):
    """A unique identifier for the device."""
    return "{model:s}--{serial:08x}".format(model=self.model.replace('-',''), serial=self.serial_number).lower()

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    # Doesn't look like the device supports reading a unique
    # identifier, this cobbles something together from the
    # sensor type (part ID, hardware revision) and I2C address
    unique_string = ''.join("{}{}{}{:#x}".format(self.manufacturer.replace('-',''), self.get_part_id(), self.get_revision(), self.i2c_address).lower().split())
    return crc32(unique_string.encode())
