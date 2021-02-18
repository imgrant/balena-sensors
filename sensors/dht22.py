from datetime import datetime
from zlib import crc32
from retrying import retry
import re
import board
import adafruit_dht
from .measurements import Measurement, MeasurementError

# All the generally available GPIO pins on a Raspberry Pi
GPIO_PINS = [
  board.D17,
  board.D27,
  board.D22,
  board.D23,
  board.D24,
  board.D25,
  board.D5,
  board.D6,
  board.D12,
  board.D13,
  board.D16,
  board.D26
]


def enumerate_sensors():
  sensors = []
  for gpio in GPIO_PINS:
    try:
      sensor = dht22(pin=gpio)
      # To see if there is a DHT device on the GPIO pin, try taking a measurement
      try_measurement(sensor)
    except RuntimeError as error:
      print("Error initialising DHT sensor on GPIO pin {}: {}".format(gpio.id, str(error)))
    else:
      print("Found DHT22 sensor with ID {:x} on GPIO pin {}".format(sensor.serial_number, sensor.pin.id))
      sensors.append(sensor)
  return sensors


def retry_if_try_again(error):
  """Return True if the error string is recommending to try again, False otherwise (likely a true failure)."""
  if "Try again" in str(error):
    print("DHT Error: {} => retrying...".format(str(error)))
    try_again = True
  else:
    try_again = False
  return try_again


@retry(stop_max_attempt_number=3, wait_fixed=2000, retry_on_exception=retry_if_try_again)
def try_measurement(sensor):
  """
  If no DHT device is found, RuntimeError ("DHT sensor not found, check wiring") is raised.
  But RuntimeError will contain the string "Try again" for other errors such as full buffer
  not returned, CRC error, etc. In this case, it can be useful to do as told and try again.
  """
  sensor.measure()
  return True


class dht22(adafruit_dht.DHT22):

  manufacturer = 'ASAIR'
  model = 'DHT22'
  supported_measurements = [Measurement.TEMPERATURE,
                            Measurement.HUMIDITY]

  def __init__(self, pin=board.D24):
    self.pin = pin
    super().__init__(pin=self.pin, use_pulseio=False)

  def update_sensor(self):
    try:
      try_measurement(self) # Sets self._temperature, self._humidity, retry on error
    except RuntimeError as error:
      raise MeasurementError(str(error))
    else:
      self.timestamp = datetime.now().isoformat(timespec='seconds')

  @property
  def temperature(self):
    return self._temperature

  @property
  def humidity(self):
    return self._humidity

  @property
  def id(self):
    """A unique identifier for the device."""
    return f'{self.model.replace('-',''):s}--{self.serial_number:08x}'.lower()

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    # Doesn't look like the device supports reading a unique
    # identifier, this cobbles something together from the
    # sensor type and GPIO pin
    unique_string = ''.join("{}{}{:#x}".format(self.manufacturer, self.model, self.pin.id).lower().split())
    return crc32(unique_string.encode())
