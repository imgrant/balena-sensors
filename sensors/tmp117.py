from typing import Optional
from datetime import datetime
from zlib import crc32
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
    except (OSError, AttributeError, ValueError) as error:
      # If no TMP117 device is found, an AttributeError is raised (possibly ValueError if no device at address?)
      # OSError is raised on I2C I/O error
      print("Error initialising TMP117 sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found TMP117 sensor with ID {:x} at I2C address {:#x}".format(sensor.serial_number, i2c_address))
      sensors.append(sensor)
  return sensors


def _convert_to_integer(bytes_to_convert):
    """Use bitwise operators to convert the bytes into integers."""
    integer = None
    for chunk in bytes_to_convert:
        if not integer:
            integer = chunk
        else:
            integer = integer << 8
            integer = integer | chunk
    return integer


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
    """A unique identifier for the device."""
    return f'{self.model:s}--{self.serial_number:08x}'.lower()

  @property
  def serial_number(self):
    """
    48-bit factory-set unique ID
    See: https://e2e.ti.com/support/sensors/f/1023/t/815716?TMP117-Reading-Serial-Number-from-EEPROM
    """
    eeprom1_data = bytearray(2)
    eeprom2_data = bytearray(2)
    eeprom3_data = bytearray(2)
    # Fetch EEPROM registers
    with self.i2c_device as i2c:
        i2c.write_then_readinto(bytearray([adafruit_tmp117._EEPROM1]), eeprom1_data)
        i2c.write_then_readinto(bytearray([adafruit_tmp117._EEPROM2]), eeprom2_data)
        i2c.write_then_readinto(bytearray([adafruit_tmp117._EEPROM3]), eeprom3_data)
    # Combine the 2-byte portions
    combined_id = bytearray(
        [
            eeprom1_data[0],
            eeprom1_data[1],
            eeprom2_data[0],
            eeprom2_data[1],
            eeprom3_data[0],
            eeprom3_data[1],
        ]
    )
    # Convert to an integer
    return _convert_to_integer(combined_id)
