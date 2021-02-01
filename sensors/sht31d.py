from typing import Optional
from datetime import datetime
from busio import I2C
from board import SCL, SDA
import adafruit_sht31d
from .measurements import Measurement, MeasurementError


def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in [ adafruit_sht31d._SHT31_DEFAULT_ADDRESS, adafruit_sht31d._SHT31_SECONDARY_ADDRESS ]:
    try:
      sensor = sht31d(i2c_dev=bus, i2c_addr=i2c_address)
    except (ValueError, RuntimeError) as error:
      # If no SHT device is found, a ValueError is raised; RuntimeError can be raised on, e.g. CRC mismatch (faulty sensor or wiring?)
      print("Error initialising SHT3x sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found SHT31-D sensor with ID {} at I2C address {:#x}".format(sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


class sht31d(adafruit_sht31d.SHT31D):

  manufacturer = 'Sensirion'
  model = 'SHT31-D'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.HUMIDITY]

  def __init__(self, i2c_dev=None,
               i2c_addr: Optional[int] = adafruit_sht31d._SHT31_DEFAULT_ADDRESS):
    super().__init__(i2c_bus=i2c_dev, address=i2c_addr)

  def update_sensor(self):
    try:
      self._temperature, self.humidity = self._read()
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
