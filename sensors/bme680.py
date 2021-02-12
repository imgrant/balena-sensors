from typing import Optional
from datetime import datetime
from busio import I2C
from board import SCL, SDA
# Use the Adafruit BME680 library to ease handling of probing the 
# chip ID, etc., even though we'll use the Bosch BSEC library later 
# to get access to the IAQ score output directly from the chip.
import adafruit_bme680
import subprocess, io, json, time
from threading import Thread
from .measurements import Measurement, MeasurementError

I2C_ADDRESSES = [ 0x76, 0x77 ]

def enumerate_sensors():
  sensors = []
  bus = I2C(SCL, SDA)
  for i2c_address in I2C_ADDRESSES:
    try:
      sensor = bme680(i2c_addr=i2c_address, i2c_dev=bus)
    except (OSError, ValueError, RuntimeError) as error:
      # If no device is found, a ValueError is raised;
      # if the chip ID doesn't match (i.e. it's not a BME680), RuntimeError is raised
      print("Error initialising BME680 sensor at I2C address {:#x}: {}".format(i2c_address, str(error)))
    else:
      print("Found BME680 sensor with ID {} at I2C address {:#x}".format(sensor.id, i2c_address))
      sensors.append(sensor)
  return sensors


class bme680():

  manufacturer = 'Bosch'
  model = 'BME680'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.PRESSURE,
                            Measurement.HUMIDITY,
                            Measurement.AIR_QUALITY,
                            Measurement.IAQ_ACCURACY,
                            Measurement.STATIC_AIR_QUALITY,
                            Measurement.S_IAQ_ACCURACY,
                            Measurement.CO2_EQUIV,
                            Measurement.BVOC_EQUIV,
                            Measurement.GAS,
                            Measurement.GAS_PERCENT]
  bsec_data = None

  def __init__(self,
               i2c_addr:    Optional[int]     = I2C_ADDRESSES[0],
               i2c_dev:     Optional[object]  = None,
               bsec_cmd:    Optional[str]     = '/opt/bsec/bsec_bme680',
               config_file: Optional[str]     = '/data/bsec/bsec_iaq.config',
               state_file:  Optional[str]     = '/data/bsec/bsec_iaq.state',
               temp_offset: Optional[float]   = 0.0 ):
    # Call the Adafruit BME680 class init() — if the sensor at the I2C address
    # is not a BME680, an error will be raised.
    self.bme680_i2c = adafruit_bme680.Adafruit_BME680_I2C(i2c=i2c_dev, address=i2c_addr)
    self.bsec_command = [ bsec_cmd,
                          "--address",  f'{i2c_addr:#x}',
                          "--config",   config_file,
                          "--state",    state_file,
                          "--offset",   str(temp_offset) ]    
    # Start the BSEC library process
    self.bsec_process = Thread(target=self.bsec_capture)
    self.bsec_process.start()

  @property
  def id(self):
    """A unique identifier (serial number) for the device."""
    # See: https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/Unique-IDs-in-Bosch-Sensors/m-p/6020/highlight/true#M62
    i = self.bme680_i2c._read(0x83, 4)
    serial = (((i[3] + (i[2] << 8)) & 0x7fff) << 16) + (i[1] << 8) + i[0]
    return serial

  def update_sensor(self):
    try:
      assert type(self.bsec_data) is dict, "Incorrect type: BSEC data is not a dictionary (sensor not ready?)"
      for m in self.supported_measurements:
        assert m['name'] in self.bsec_data, "Reading not found: '{}' is not in BSEC data".format(m['name'])
    except AssertionError as error:
      raise MeasurementError(str(error))
    else:
      for key,value in self.bsec_data.items():
        try:
          precision = next(filter(lambda m: m['name'] == key, self.supported_measurements))
          if precision == 0:
            setattr(self, key, int(value))
          else:
            setattr(self, key, float(value))
        except StopIteration:
          pass
      self.timestamp = datetime.now().isoformat(timespec='seconds')


  def bsec_capture(self):
    bsec = subprocess.Popen(self.bsec_command, stdout=subprocess.PIPE)
    for line in io.TextIOWrapper(bsec.stdout, encoding="utf-8"):
      self.bsec_data = json.loads(line.strip())
    rc = bsec.poll()
    time.sleep(2)
    return rc
