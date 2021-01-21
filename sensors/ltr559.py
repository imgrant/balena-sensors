import sys
from time import sleep
try:
    from smbus import SMBus
except ImportError:
    from smbus2 import SMBus
from ltr559 import LTR559

try:
    # Initialise the LTR559
    bus = SMBus(1)
    sensor = LTR559(i2c_dev=bus)
    # Sensor seems to need a short pause after initialisation,
    # otherwise the readings come out as zero
    sleep(0.1)

    # Not really a unique ID, but something to start with
    device_uuid = "ltr559-{}-{}".format(sensor.get_part_id(), sensor.get_revision())

    # Read sensor data and store for retrieval
    sensor.update_sensor()

    print("sensors,sensor_id={} lux={:.5f},proximity={:04d}".format(
            device_uuid,
            sensor.get_lux(passive=True),
            sensor.get_proximity(passive=True)))

except (RuntimeError, OSError) as error:
    # If no LTR559 is found, a RuntimeError or OSError is raised
    print(error, file=sys.stderr)