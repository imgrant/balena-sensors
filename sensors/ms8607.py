from datetime import datetime
from zlib import crc32
from busio import I2C
from board import SCL, SDA
import adafruit_ms8607
from .measurements import Measurement, MeasurementError

I2C_ADDRESSES = [ 0x40, 0x76 ]

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  # The MS8607 is a two-in-one device, occupying fixed I2C addresses 0x40 and 0x76
  try:
    sensor = ms8607(i2c_dev=bus)
  except (OSError, ValueError, RuntimeError, AttributeError) as error:
    # If no device is found, ValueError is raised
    # RuntimeError is also raised if self-calibration during initialisation fails
    print("Error initialising MS8607 sensor: {}".format(str(error)))
  else:
    print("Found MS8607 sensor with ID {:x} at I2C addresses {}".format(sensor.serial_number, ','.join(["{:#x}".format(i) for i in I2C_ADDRESSES])))
    sensors.append(sensor)
  return sensors


class ms8607(adafruit_ms8607.MS8607):

  manufacturer = 'TE Connectivity'
  model = 'MS8607'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.PRESSURE,
                            Measurement.HUMIDITY]

  def __init__(self, i2c_dev):
    super().__init__(i2c_bus=i2c_dev)
    self.i2c_address = sum(I2C_ADDRESSES)
    self._t = None
    self._p = None
    self._h = None

  def update_sensor(self):
    try:
      self._t, self._p = self.pressure_and_temperature
      self._h = self.relative_humidity
    except (ValueError, RuntimeError) as error:
      raise MeasurementError(str(error))
    else:
      self.timestamp = datetime.now().isoformat(timespec='seconds')

  @property
  def temperature(self):
    return self._t

  @property
  def pressure(self):
    return self._p

  @property
  def humidity(self):
    return self._h

  @property
  def id(self):
    """A unique identifier for the device."""
    return "{model:s}--{serial:08x}".format(model=self.model.replace('-',''), serial=self.serial_number).lower()

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    # Doesn't look like the device supports reading a unique
    # identifier, this cobbles something together from the
    # sensor type and I2C address
    unique_string = ''.join("{}{}{:#x}".format(self.manufacturer, self.model, self.i2c_address).lower().split())
    return crc32(unique_string.encode())
