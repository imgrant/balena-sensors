from datetime import datetime
from retrying import retry
from busio import I2C
from board import SCL, SDA
import adafruit_si7021
from .measurements import Measurement, MeasurementError

I2C_ADDRESS = 0x40

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in [ I2C_ADDRESS ]:
    try:
      sensor = probe_sensor(bus, i2c_address)
    except (ValueError, RuntimeError) as error:
      # If no Si70xx device is found, ValueError is raised; RuntimeError is raised upon failed initialisation
      print("Error initialising Si70xx sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found {} sensor with ID {} at I2C address {:#x}".format(sensor.model, sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


def retry_if_runtime_error(exception):
  """Return True if the exception is a RuntimeError (indicating failed initialisation), False otherwise."""
  return isinstance(exception, RuntimeError)


@retry(stop_max_attempt_number=3, wait_fixed=1000, retry_on_exception=retry_if_runtime_error)
def probe_sensor(i2c_bus, i2c_address):
  """
  If no device is found, ValueError is raise; but if RuntimeError is raised,
  it can indicate failed initialisation ("bad USER1 register"), worth retrying?
  """
  sensor = si7021(i2c_dev=i2c_bus, i2c_addr=i2c_address)
  return sensor


class si7021(adafruit_si7021.SI7021):

  manufacturer = 'Silicon Labs'
  model = 'Si70xx'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.HUMIDITY]

  def __init__(self, i2c_dev, i2c_addr=I2C_ADDRESS):
    super().__init__(i2c_bus=i2c_dev, address=i2c_addr)
    self._temperature = None

  def update_sensor(self):
    try:
      self._temperature = super().temperature
      self.humidity = super().relative_humidity
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

  @property
  def model(self):
    """The device type (model)."""
    return self.device_identifier
