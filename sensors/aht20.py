from datetime import datetime
import uuid
from busio import I2C
from board import SCL, SDA
import adafruit_ahtx0
from .measurements import Measurement, MeasurementError


def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in [ adafruit_ahtx0.AHTX0_I2CADDR_DEFAULT ]:
    try:
      sensor = aht20(i2c_dev=bus, i2c_addr=i2c_address)
    except (ValueError, RuntimeError) as error:
      # If no AHTx0 device is found, ValueError is raised
      # RuntimeError is also raised if self-calibration during initialisation fails
      print("Error initialising AHT sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found AHT20 sensor with ID {} at I2C address {:#x}".format(sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


class aht20(adafruit_ahtx0.AHTx0):

  manufacturer = 'ASAIR'
  model = 'AHT20'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.HUMIDITY]

  def __init__(self, i2c_dev, i2c_addr=adafruit_ahtx0.AHTX0_I2CADDR_DEFAULT):
    super().__init__(i2c_bus=i2c_dev, address=i2c_addr)
    self._temperature = None

  def update_sensor(self):
    try:
      self._readdata() # Sets self._temp, self._humidity
    except ValueError as error:
      raise MeasurementError(str(error))
    else:
      self.timestamp = datetime.now().isoformat(timespec='seconds')

  @property
  def temperature(self):
    return self._temp

  @property
  def humidity(self):
    return self._humidity

  @property
  def id(self):
    """A unique identifier (serial number) for the device."""
    # Doesn't look like the AHT20 supports reading a unique
    # identifier, this leverages the MAC and AHT20 I2C address
    # to come up with something semi-usable for this.
    uid = uuid.getnode()
    return f'{adafruit_ahtx0.AHTX0_I2CADDR_DEFAULT + uid:08x}'