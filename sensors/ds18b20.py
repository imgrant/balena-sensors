from typing import Optional
from datetime import datetime
from w1thermsensor import W1ThermSensor, Sensor
from w1thermsensor import NoSensorFoundError, SensorNotReadyError, ResetValueError
from .measurements import Measurement, MeasurementError

def enumerate_sensors():
  sensors = []
  for available_sensor in W1ThermSensor.get_available_sensors([Sensor.DS18B20]):
    try:
      sensor = ds18b20(available_sensor.id)
    except Exception as error:
      print("Error initialising DS18B20 sensor with ID {}: {}".format(available_sensor.id, str(error)))
    else:
      print("Found DS18B20 sensor with ID {:012x}".format(sensor.serial_number))
      sensors.append(sensor)
  return sensors


class ds18b20():

  manufacturer = 'MAXIM'
  model = 'DS18B20'
  supported_measurements = [Measurement.TEMPERATURE]

  def __init__(self, sensor_id: Optional[str] = None):
    self._w1therm = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id=sensor_id)
    self._id = sensor_id
    self.temperature = None

  def update_sensor(self):
    try:
      self.temperature = self._w1therm.get_temperature()
    except (NoSensorFoundError, SensorNotReadyError, ResetValueError) as error:
      raise MeasurementError(str(error))
    else:
      self.timestamp = datetime.now().isoformat(timespec='seconds')

  @property
  def id(self):
    """A unique identifier for the device."""
    return f'{self.model:s}--{self.serial_number:012x}'.lower()

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    serial = int(self._id, 16)
    return serial
