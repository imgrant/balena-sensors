from typing import Optional
from datetime import datetime
from busio import I2C
from board import SCL, SDA
import adafruit_bme280
from .measurements import Measurement, MeasurementError

I2C_ADDRESSES = [ 0x76, 0x77 ]

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in I2C_ADDRESSES:
    try:
      sensor = bme280(i2c_addr=i2c_address, i2c_dev=bus)
    except (OSError, ValueError, RuntimeError) as error:
      # If no device is found, a ValueError is raised;
      # if the chip ID doesn't match (i.e. it's not a BME280), RuntimeError is raised
      print("Error initialising BME280 sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found BME280 sensor with ID {:x} at I2C address {:#x}".format(sensor.serial_number, i2c_address))
      sensors.append(sensor)
  return sensors


class bme280(adafruit_bme280.Adafruit_BME280_I2C):

  manufacturer = 'Bosch'
  model = 'BME280'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.PRESSURE,
                            Measurement.HUMIDITY]

  def __init__(self,
               i2c_addr:  Optional[int]     = I2C_ADDRESSES[0],
               i2c_dev:   Optional[object]  = None):
    super().__init__(i2c=i2c_dev, address=i2c_addr)
    self._t = None
    self._p = None
    self._h = None

  def update_sensor(self):
    try:
      self._t = super().temperature
      self._p = super().pressure
      self._h = super().humidity
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
    return f'{self.model:s}--{self.serial_number:08x}'.lower()

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    # See: https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/Unique-IDs-in-Bosch-Sensors/m-p/6020/highlight/true#M62
    i = self._read_register(0x83, 4)
    serial = (((i[3] + (i[2] << 8)) & 0x7fff) << 16) + (i[1] << 8) + i[0]
    return serial
