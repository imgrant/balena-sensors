from typing import Optional
from datetime import datetime
from sensirion_i2c_driver import I2cConnection
from sensirion_i2c_sht.sht3x import Sht3xI2cDevice
from sensirion_i2c_driver.linux_i2c_transceiver import LinuxI2cTransceiver
from sensirion_i2c_driver.errors import I2cTransceiveError
from .measurements import Measurement, MeasurementError

I2C_ADDR_PRIMARY = 0x44
I2C_ADDR_SECONDARY = 0x45


def enumerate_sensors():
  sensors = []
  for i2c_address in [I2C_ADDR_PRIMARY, I2C_ADDR_SECONDARY]:
    try:
      sensor = sht3x(connection=I2cConnection(LinuxI2cTransceiver('/dev/i2c-1')), i2c_addr=i2c_address)
    except I2cTransceiveError as error:
      # If no SHT device is found, an I2cTransceiveError is raised
      pass
    else:
      print("Found SHT3x sensor with ID {} at I2C address {:#x}".format(sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


class sht3x(Sht3xI2cDevice):

  manufacturer = 'Sensirion'
  model = 'SHT-3x'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.HUMIDITY]

  def __init__(self, connection=None,
               i2c_addr: Optional[int] = I2C_ADDR_PRIMARY):
    super().__init__(connection=connection, slave_address=i2c_addr)
    self.id = str(self.read_serial_number())

  def update_sensor(self):
    try:
      temperature, humidity = self.single_shot_measurement()
    except I2cTransceiveError as error:
      raise MeasurementError(repr(error))
    else:
      self.timestamp = datetime.now().isoformat()
      self.temperature = temperature.degrees_celsius
      self.humidity = humidity.percent_rh
