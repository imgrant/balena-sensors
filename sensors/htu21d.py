from datetime import datetime
from zlib import crc32
from busio import I2C
from board import SCL, SDA
import adafruit_htu21d
from .measurements import Measurement, MeasurementError

I2C_ADDRESS = 0x40
_ID1_CMD = bytearray([0xFA, 0x0F])
_ID2_CMD = bytearray([0xFC, 0xC9])

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in [ I2C_ADDRESS ]:
    try:
      sensor = htu21d(i2c_dev=bus, i2c_addr=i2c_address)
    except (OSError, ValueError, RuntimeError) as error:
      # If no HTU21D-F device is found, ValueError is raised;
      # RuntimeError is probably *not* raised upon failed initialisation,
      # since the Adafruit HTU21-D library doesn't compare the chip ID.
      print("Error initialising HTU21D-F sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found HTU21D-F sensor with ID {:x} at I2C address {:#x}".format(sensor.serial_number, i2c_address))
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


class htu21d(adafruit_htu21d.HTU21D):

  manufacturer = 'Measurement Specialities'
  model = 'HTU21D'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.HUMIDITY]

  def __init__(self, i2c_dev, i2c_addr=I2C_ADDRESS):
    super().__init__(i2c_bus=i2c_dev, address=i2c_addr)
    self._temperature = None
    self._humidity = None

  def update_sensor(self):
    try:
      self._temperature = super().temperature
      self._humidity = super().relative_humidity
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
  def humidity(self):
    return self._humidity

  @property
  def id(self):
    """A unique identifier for the device."""
    return "{model:s}--{serial:08x}".format(model=self.model.replace('-',''), serial=self.serial_number).lower()

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    # The registers and format of the serial number is the same as for Si7021
    # See also: getSerialNumber() from https://www.espruino.com/modules/HTU21D.js
    # Serial 1st half
    data = _ID1_CMD
    id1 = bytearray(8)
    with self.i2c_device as i2c:
        i2c.write_then_readinto(data, id1)
    # Serial 2nd half
    data = _ID2_CMD
    id2 = bytearray(6)
    with self.i2c_device as i2c:
        i2c.write_then_readinto(data, id2)
    # Common/fixed bytes for all HTU21D sensors
    if id2[3] != 0x48 or id2[4] != 0x54 or id1[0] != 0x00 or id2[0] != 0x32:
      raise RuntimeError("Invalid serial number")
    # The unique serial number part is formed from the remaining bytes
    serial = (id1[2] << 24) | (id1[4] << 16) | (id1[6] << 8) | id2[1]
    return serial
