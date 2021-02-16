class Measurement():

  TEMPERATURE         = { 'name': 'temperature',     'units': '°C',     'precision': 3,  'ha_device_class': 'temperature',  'ha_title': 'Temperature'     }
  PRESSURE            = { 'name': 'pressure',        'units': 'hPa',    'precision': 2,  'ha_device_class': 'pressure',     'ha_title': 'Pressure'        }
  HUMIDITY            = { 'name': 'humidity',        'units': '%rh',    'precision': 2,  'ha_device_class': 'humidity',     'ha_title': 'Humidity'        }
  PROXIMITY           = { 'name': 'proximity',       'units': 'count',  'precision': 0,  'ha_device_class': None,           'ha_title': 'Proximity'       }
  LIGHT               = { 'name': 'light',           'units': 'lx',     'precision': 5,  'ha_device_class': 'illuminance',  'ha_title': 'Light'           }
  AIR_QUALITY         = { 'name': 'iaq',             'units': 'IAQ',    'precision': 2,  'ha_device_class': None,           'ha_title': 'Air Quality'     }
  IAQ_ACCURACY        = { 'name': 'iaq_accuracy',    'units': None,     'precision': 0,  'ha_device_class': None,           'ha_title': 'IAQ Accuracy'    }
  STATIC_AIR_QUALITY  = { 'name': 's_iaq',           'units': 'IAQ',    'precision': 2,  'ha_device_class': None,           'ha_title': 'Static IAQ'      }
  S_IAQ_ACCURACY      = { 'name': 's_iaq_accuracy',  'units': None,     'precision': 0,  'ha_device_class': None,           'ha_title': 'S-IAQ Accuracy'  }
  #
  # Accuracy signal is an integer, 0-3, representing the following states:
  #
  #  | State            | Value |  Accuracy description                                     |
  #  |------------------|-------|-----------------------------------------------------------|
  #  | UNRELIABLE       |   0   | Stabilization / run-in ongoing                            |
  #  | LOW_ACCURACY     |   1   | Low accuracy,to reach high accuracy(3),please expose      |
  #  |                  |       |  sensor once to good air (e.g. outdoor air) and bad air   |
  #  |                  |       |  (e.g. box with exhaled breath) for auto-trimming         |
  #  | MEDIUM_ACCURACY  |   2   | Medium accuracy: auto-trimming ongoing                    |
  #  | HIGH_ACCURACY    |   3   | High accuracy                                             |
  #
  CO2_EQUIV           = { 'name': 'co2_equivalents',         'units': 'ppm',  'precision': 2,  'ha_device_class': None, 'ha_title': 'CO2'   }
  BVOC_EQUIV          = { 'name': 'breath_voc_equivalents',  'units': 'ppm',  'precision': 2,  'ha_device_class': None, 'ha_title': 'VOC'   }
  GAS                 = { 'name': 'gas_resistance',          'units': 'Ω',    'precision': 3,  'ha_device_class': None, 'ha_title': 'Gas'   }
  GAS_PERCENT         = { 'name': 'gas_percentage',          'units': '%',    'precision': 2,  'ha_device_class': None, 'ha_title': 'Gas %' }
  #  
  # Gas percentage is an alternative indicator for air pollution [%], which rates 
  # the raw gas sensor resistance value based on the individual sensor history:
  #  0% = "lowest air pollution ever measured"
  #  100% = "highest air pollution ever measured"


class MeasurementError(Exception):
  def __init__(self, message="Unable to read measurement data from sensor"):
        self.message = message
        super().__init__(self.message)
