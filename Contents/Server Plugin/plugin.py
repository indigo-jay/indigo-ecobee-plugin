from pyecobee import Ecobee
import sys
import json
import indigo
from ecobee_devices import EcobeeThermostat, EcobeeRemoteSensor


DEBUG=False
ACCESS_TOKEN_PLUGIN_PREF='accessToken'
AUTHORIZATION_CODE_PLUGIN_PREF='authorizationCode'
REFRESH_TOKEN_PLUGIN_PREF='refreshToken'

class IndigoLogger:
	def write(self, text):
		indigo.server.log(text)

class Plugin(indigo.PluginBase):

	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = DEBUG

		self.active_remote_sensors = []
		self.active_thermostats = []

		# redirect stdout to Indigo log
		sys.stdout = IndigoLogger()

		tmpconfig = {'API_KEY': "qyy0od74EpMz2P8X1fmAfyoxKod4t1Fo"}
		if ACCESS_TOKEN_PLUGIN_PREF in pluginPrefs:
			tmpconfig['ACCESS_TOKEN'] = pluginPrefs[ACCESS_TOKEN_PLUGIN_PREF]
		if AUTHORIZATION_CODE_PLUGIN_PREF in pluginPrefs:
			tmpconfig['AUTHORIZATION_CODE'] = pluginPrefs[AUTHORIZATION_CODE_PLUGIN_PREF]
		if REFRESH_TOKEN_PLUGIN_PREF in pluginPrefs:
			tmpconfig['REFRESH_TOKEN'] = pluginPrefs[REFRESH_TOKEN_PLUGIN_PREF]
		indigo.server.log(u"constructed config: %s" % json.dumps(tmpconfig))

		# Create an ecobee object with the config dictionary
#		indigo.server.log(u"initializing ecobee module")
		self.ecobee = Ecobee(config = tmpconfig)
#		indigo.server.log(u"ecobee module initialized")

		self.pluginPrefs["pin"] = self.ecobee.pin
		self.pluginPrefs["authorizationCode"] = self.ecobee.authorization_code


	def __del__(self):
		indigo.PluginBase.__del__(self)

	def startup(self):
		indigo.server.log(u"startup called")
#		self.ecobee.update()

	def shutdown(self):
		indigo.server.log(u"shutdown called")

	def request_pin(self, valuesDict = None):
		indigo.server.log(u"requesting pin")

		valuesDict[ACCESS_TOKEN_PLUGIN_PREF] = ''
		valuesDict[AUTHORIZATION_CODE_PLUGIN_PREF] = ''
		valuesDict[REFRESH_TOKEN_PLUGIN_PREF] = ''

		self.ecobee.request_pin()
		indigo.server.log(u"received pin: %s" % self.ecobee.pin)
		valuesDict['pin'] = self.ecobee.pin
		return valuesDict

	def open_browser_to_ecobee(self, valuesDict = None):
		self.browserOpen("http://www.ecobee.com")

	def refresh_credentials(self, valuesDict = None):
		self.ecobee.request_tokens()
		self._get_keys_from_ecobee(valuesDict)
		#self.ecobee.update()
		#indigo.server.log(json.dumps(self.ecobee.thermostats))
		return valuesDict

	def get_remote_sensors(self, filter="", valuesDict=None, typeId="", targetId=0):
		self.ecobee.update()

		# filter out the 'remote sensor' that's actually the Ecobee thermostat
		return [
			(rs.get('code'), rs.get('name'))
			for rs in self.ecobee.get_remote_sensors(0)
				if 'ecobee3_remote_sensor' == rs.get('type')
		]


	def _get_keys_from_ecobee(self, valuesDict):
		valuesDict[ACCESS_TOKEN_PLUGIN_PREF] = self.ecobee.access_token
		valuesDict[AUTHORIZATION_CODE_PLUGIN_PREF] = self.ecobee.authorization_code
		valuesDict[REFRESH_TOKEN_PLUGIN_PREF] = self.ecobee.refresh_token
		return valuesDict

	def deviceStartComm(self, dev):
#		indigo.server.log('deviceStartComm: %s' % dev)
		if dev.model == 'Ecobee Remote Sensor':
#			indigo.server.log("deviceStartComm: creating EcobeeRemoteSensor")
			self.active_remote_sensors.append(EcobeeRemoteSensor(dev.pluginProps["address"], dev, self.ecobee))
			indigo.server.log("added remote sensor %s" % dev.pluginProps["address"])

		elif dev.model == 'Ecobee Thermostat':
			self.active_thermostats.append(EcobeeThermostat("foo"))

#		indigo.server.log(u"device added; plugin props: %s" % dev.pluginProps)
#		indigo.server.log(u"device added: %s" % dev)

	def _objectForDevice(self, dev):
		if dev.model == 'Ecobee Remote Sensor':
			matches = [rs for rs in active_remote_sensors if rs.address == dev.address]
			return matches[0]

	def runConcurrentThread(self):
		try:
			while True:
				for ers in self.active_remote_sensors:
					ers.updateServer()
#				for dev in indigo.devices.iter("self"):
#					indigo.server.log('dev: %s' % dev)
#					if not dev.enabled:
#						continue
#					if dev.model == 'Ecobee Remote Sensor':
#						indigo.server.log("concurrent thread found active remote sensor %s" % dev.address)
					# Plugins that need to poll out the status from the thermostat
					# could do so here, then broadcast back the new values to the
					# Indigo Server.
					# self._refreshStatesFromHardware(dev, False, False)

				self.sleep(15)
				if self.ecobee.authenticated:
					self.ecobee.update()
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.
