from typing import Optional
from w1thermsensor import W1ThermSensor, Sensor
from .measurements import Measurement

def enumerate_sensors():
  sensors = []
  for sensor in W1ThermSensor.get_available_sensors([Sensor.DS18B20]):
    print("Found DS18B20 sensor with ID {}".format(sensor.id))
    sensors.append(ds18b20(sensor.id))
  return sensors


class ds18b20(W1ThermSensor):

  manufacturer = 'MAXIM'
  model = 'DS18B20'
  supported_measurements = [Measurement.TEMPERATURE]

  def __init__(self, sensor_id: Optional[str] = None):
    super().__init__(Sensor.DS18B20, sensor_id)
    self.temperature = None

  def update_sensor(self):
    self.temperature = self.get_temperature()
    