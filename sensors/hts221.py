from typing import Optional
from datetime import datetime
from waiting import wait, TimeoutExpired
from zlib import crc32
from busio import I2C
from board import SCL, SDA
import adafruit_hts221
from .measurements import Measurement, MeasurementError

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  try:
    sensor = hts221(i2c_dev=bus, i2c_addr=adafruit_hts221._HTS221_DEFAULT_ADDRESS)
  except (OSError, ValueError, RuntimeError) as error:
    # If no device is found, a ValueError is raised; RuntimeError can also be raised
    # if the device is not an HTS221 or on, e.g. CRC mismatch (faulty sensor or wiring?)
    print("Error initialising HTS221 sensor at I2C address {:#x}: {}".format(adafruit_hts221._HTS221_DEFAULT_ADDRESS, str(error)))
  else:
    print("Found HTS221 sensor with ID {:x} at I2C address {:#x}".format(sensor.serial_number, sensor.i2c_address))
    sensors.append(sensor)
  return sensors


class hts221(adafruit_hts221.HTS221):

  manufacturer = 'STMicroelectronics'
  model = 'HTS221'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.HUMIDITY]

  def __init__(self, i2c_dev=None,
               i2c_addr: Optional[int] = adafruit_hts221._HTS221_DEFAULT_ADDRESS):
    super().__init__(i2c_bus=i2c_dev)
    self.i2c_address = i2c_addr
    self.data_rate = adafruit_hts221.Rate.ONE_SHOT

  def update_sensor(self, timeout=3, interval=0.1):
    try:
      self.take_measurements()
      wait(lambda: self.temperature_data_ready is True, timeout_seconds=3, sleep_seconds=0.1)
      self._temperature = super().temperature
      wait(lambda: self.humidity_data_ready is True, timeout_seconds=3, sleep_seconds=0.1)
      self._humidity = super().relative_humidity
    except (TimeoutExpired, IOError, ValueError) as error:
      raise MeasurementError(str(error))
    else:
      self.timestamp = datetime.now().isoformat(timespec='seconds')

  # Override super class properties
  # (otherwise there's a name clash for self.temperature)
  @property
  def temperature(self):
    return self._temperature

  @property
  def humidity(self):
    return self._humidity

  @property
  def id(self):
    """A unique identifier for the device."""
    return f'{self.model:s}--{self.serial_number:08x}'.lower()

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    # Doesn't look like the device supports reading a unique
    # identifier, this cobbles something together from the
    # sensor type and I2C address
    unique_string = ''.join("{}{}{:#x}".format(self.manufacturer, self.model, self.i2c_address).lower().split())
    return crc32(unique_string.encode())
