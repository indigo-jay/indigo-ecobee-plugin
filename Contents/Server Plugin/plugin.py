import pyecobee
import sys
import json
import indigo
from ecobee_devices import EcobeeBase, EcobeeThermostat, EcobeeRemoteSensor
import temperature_scale
import logging


DEBUG=False
ACCESS_TOKEN_PLUGIN_PREF='accessToken'
AUTHORIZATION_CODE_PLUGIN_PREF='authorizationCode'
REFRESH_TOKEN_PLUGIN_PREF='refreshToken'
TEMPERATURE_SCALE_PLUGIN_PREF='temperatureScale'

TEMP_FORMATTERS = {
	'F': temperature_scale.Fahrenheit(),
	'C': temperature_scale.Celsius(),
	'K': temperature_scale.Kelvin(),
	'R': temperature_scale.Rankine()
}

class IndigoLoggingHandler(logging.Handler):
	def __init__(self, p):
		 logging.Handler.__init__(self)
		 self.plugin = p

	def emit(self, record):
		if record.levelno < 20:
			self.plugin.debugLog(record.getMessage())
		elif record.levelno < 40:
			indigo.server.log(record.getMessage())
		else:
			self.plugin.errorLog(record.getMessage())

class Plugin(indigo.PluginBase):

	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = DEBUG

		self.active_remote_sensors = []
		self.active_thermostats = []

		logHandler = IndigoLoggingHandler(self)

		pyecobeeLogger = logging.getLogger('pyecobee')
		pyecobeeLogger.addHandler(logHandler)
		self.log = logging.getLogger('indigo.ecobee.plugin')
		self.log.addHandler(logHandler)

		if DEBUG:
			pyecobeeLogger.setLevel(logging.DEBUG)
			self.log.setLevel(logging.DEBUG)
		else:
			pyecobeeLogger.setLevel(logging.ERROR)
			self.log.setLevel(logging.WARNING)

		if TEMPERATURE_SCALE_PLUGIN_PREF in pluginPrefs:
			self._setTemperatureScale(pluginPrefs[TEMPERATURE_SCALE_PLUGIN_PREF][0])
		else:
			self._setTemperatureScale('F')

		tmpconfig = {'API_KEY': "qyy0od74EpMz2P8X1fmAfyoxKod4t1Fo"}
		if ACCESS_TOKEN_PLUGIN_PREF in pluginPrefs:
			tmpconfig['ACCESS_TOKEN'] = pluginPrefs[ACCESS_TOKEN_PLUGIN_PREF]
		if AUTHORIZATION_CODE_PLUGIN_PREF in pluginPrefs:
			tmpconfig['AUTHORIZATION_CODE'] = pluginPrefs[AUTHORIZATION_CODE_PLUGIN_PREF]
		if REFRESH_TOKEN_PLUGIN_PREF in pluginPrefs:
			tmpconfig['REFRESH_TOKEN'] = pluginPrefs[REFRESH_TOKEN_PLUGIN_PREF]
		self.debugLog(u"constructed pyecobee config: %s" % json.dumps(tmpconfig))

		# Create an ecobee object with the config dictionary
		self.ecobee = pyecobee.Ecobee(config = tmpconfig)

		self.pluginPrefs["pin"] = self.ecobee.pin
		if self.ecobee.authenticated:
			self.pluginPrefs
			self.pluginPrefs[ACCESS_TOKEN_PLUGIN_PREF] = self.ecobee.access_token
			self.pluginPrefs[AUTHORIZATION_CODE_PLUGIN_PREF] = self.ecobee.authorization_code
			self.pluginPrefs[REFRESH_TOKEN_PLUGIN_PREF] = self.ecobee.refresh_token
		else:
			self.pluginPrefs[ACCESS_TOKEN_PLUGIN_PREF] = ''
			self.pluginPrefs[AUTHORIZATION_CODE_PLUGIN_PREF] = ''
			self.pluginPrefs[REFRESH_TOKEN_PLUGIN_PREF] = ''
			self.errorLog('Ecobee device requires authentication; open plugin configuration page for info')


	def __del__(self):
		indigo.PluginBase.__del__(self)

	def validatePrefsConfigUi(self, valuesDict):
		scaleInfo = valuesDict[TEMPERATURE_SCALE_PLUGIN_PREF]
		self._setTemperatureScale(scaleInfo[0])
		return True

	def _setTemperatureScale(self, value):
		self.log.debug(u'setting temperature scale to %s' % value)
		EcobeeBase.temperatureFormatter = TEMP_FORMATTERS.get(value)

	def startup(self):
		self.debugLog(u"startup called")

	def shutdown(self):
		self.debugLog(u"shutdown called")

	def request_pin(self, valuesDict = None):
		indigo.server.log(u"requesting pin")

		valuesDict[ACCESS_TOKEN_PLUGIN_PREF] = ''
		valuesDict[AUTHORIZATION_CODE_PLUGIN_PREF] = ''
		valuesDict[REFRESH_TOKEN_PLUGIN_PREF] = ''

		self.ecobee.request_pin()
		self.debugLog(u"received pin: %s" % self.ecobee.pin)
		valuesDict['pin'] = self.ecobee.pin
		return valuesDict

	def open_browser_to_ecobee(self, valuesDict = None):
		self.browserOpen("http://www.ecobee.com")

	def refresh_credentials(self, valuesDict = None):
		self.ecobee.request_tokens()
		self._get_keys_from_ecobee(valuesDict)
		if self.ecobee.authenticated:
			self.updateAllDevices()
		return valuesDict

	def get_thermostats(self, filter="", valuesDict=None, typeId="", targetId=0):
		self.ecobee.update()

		# list of remote sensors contains the thermostat sensor, too
		return [
			(rs.get('id'), rs.get('name'))
			for rs in self.ecobee.get_remote_sensors(0)
				if 'thermostat' == rs.get('type')
		]

	def get_remote_sensors(self, filter="", valuesDict=None, typeId="", targetId=0):
		self.ecobee.update()

		# filter out the 'remote sensor' that's actually the Ecobee thermostat
		return [
			(rs.get('code'), rs.get('name'))
			for rs in self.ecobee.get_remote_sensors(0)
				if 'ecobee3_remote_sensor' == rs.get('type')
		]

	def get_orphan_remote_sensors(self, filter="", valuesDict=None, typeId="", targetId=0):
		return self._filter_for_orphans(
					self.get_remote_sensors(filter, valuesDict, typeId, targetId),
					self.active_remote_sensors
				)

	def get_orphan_thermostats(self, filter="", valuesDict=None, typeId="", targetId=0):
		return self._filter_for_orphans(
					self.get_thermostats(filter, valuesDict, typeId, targetId),
					self.active_thermostats
				)

	def _filter_for_orphans(self, tuples, actives):
		return [
			t for t in tuples
				if not [ a for a in actives if a.address == t[0] ]
		]


	def _get_keys_from_ecobee(self, valuesDict):
		valuesDict[ACCESS_TOKEN_PLUGIN_PREF] = self.ecobee.access_token
		valuesDict[AUTHORIZATION_CODE_PLUGIN_PREF] = self.ecobee.authorization_code
		valuesDict[REFRESH_TOKEN_PLUGIN_PREF] = self.ecobee.refresh_token
		return valuesDict

	def deviceStartComm(self, dev):
#		self.debugLog('deviceStartComm: %s' % dev)
		if dev.model == 'Ecobee Remote Sensor':
			self.debugLog("deviceStartComm: creating EcobeeRemoteSensor")
			newDevice = EcobeeRemoteSensor(dev.pluginProps["address"], dev, self.ecobee)
			self.active_remote_sensors.append(newDevice)
			
			# set icon to 'temperature sensor'
			dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)

			indigo.server.log("added remote sensor %s" % dev.pluginProps["address"])

		elif dev.model == 'Ecobee Thermostat':
			# Add support for the thermostat's humidity sensor
			newProps = dev.pluginProps
			newProps["NumHumidityInputs"] = 1
			# SHENANIGANS: the following property has to be set in order for us to report
			#   whether the thermostat is presently heating, cooling, etc.
			#   This was difficult to find.
			newProps["ShowCoolHeatEquipmentStateUI"] = True
			dev.replacePluginPropsOnServer(newProps)
			newDevice = EcobeeThermostat(dev.pluginProps["address"], dev, self.ecobee)
			self.active_thermostats.append(newDevice)
			indigo.server.log("added thermostat %s" % dev.pluginProps["address"])

		# TODO: try to set initial name for new devices, as other plugins do.
		# However, this doesn't work yet. Sad clown.
		self.debugLog('device name: %s  ecobee name: %s' % (dev.name, newDevice.name))
		if dev.name == 'new device' and newDevice.name:
			dev.name = newDevice.name
			dev.replaceOnServer()
			self.debugLog('device name set to %s' % dev.name)

#		indigo.server.log(u"device added; plugin props: %s" % dev.pluginProps)
#		indigo.server.log(u"device added: %s" % dev)

	def deviceStopComm(self, dev):
		if dev.model == 'Ecobee Remote Sensor':
			self.active_remote_sensors = [
				rs for rs in self.active_remote_sensors
					if rs.address != dev.pluginProps["address"]
			]
		elif dev.model == 'Ecobee Thermostat':
			self.active_thermostats = [
				t for t in self.active_thermostats
					if t.address != dev.pluginProps["address"]
			]

	def updateAllDevices(self):
		for ers in self.active_remote_sensors:
			ers.updateServer()
		for t in self.active_thermostats:
			t.updateServer()

	def runConcurrentThread(self):
		try:
			while True:
					# Plugins that need to poll out the status from the thermostat
					# could do so here, then broadcast back the new values to the
					# Indigo Server.
					# self._refreshStatesFromHardware(dev, False, False)
				self.updateAllDevices()

				self.sleep(15)
				if self.ecobee.authenticated:
					self.ecobee.update()
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.
