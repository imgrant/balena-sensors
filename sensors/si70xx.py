from datetime import datetime
from busio import I2C
from board import SCL, SDA
from .extlib.chrisbalmer_si7021.si7021 import Si7021, CRCError
from .measurements import Measurement, MeasurementError

I2C_ADDRESS = 0x40

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in [ I2C_ADDRESS ]:
    try:
      sensor = si70xx(i2c_dev=bus, i2c_addr=i2c_address)
    except ValueError as error:
      # If no Si70xx device is found, ValueError is raised (TODO: confirm)
      pass
    else:
      print("Found {} sensor with ID {} at I2C address {:#x}".format(sensor.model, sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


class si70xx(Si7021):

  manufacturer = 'Silicon Labs'
  model = 'Si70xx'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.HUMIDITY]

  def __init__(self, i2c_dev, i2c_addr=I2C_ADDRESS):
    super().__init__(i2c=i2c_dev, address=i2c_addr)
    self.id = self.serial
    self.model = self.identifier
    self._temperature = None
    self._humidity = None

  def update_sensor(self):
    try:
      self.temperature = super().temperature
      self.humidity = super().relative_humidity
    except (IOError, CRCError) as error:
      raise MeasurementError(repr(error))

  # Override super class properties because
  # we're using the same name for temperature
  @property
  def temperature(self):
    return self._temperature

  @temperature.setter
  def temperature(self, value):
    self._temperature = value
  
  @property
  def humidity(self):
    return self._humidity

  @humidity.setter
  def humidity(self, value):
    self._humidity = value

  @property
  def timestamp(self):
    return datetime.now().isoformat(timespec='seconds')