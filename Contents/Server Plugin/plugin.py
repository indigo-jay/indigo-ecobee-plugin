from pyecobee import Ecobee, config_from_file
import sys
import json
import indigo

DEBUG=False

class IndigoLogger:
	def write(self, text):
		indigo.server.log(text)

class Plugin(indigo.PluginBase):

	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = DEBUG

		# redirect stdout to Indigo log
		sys.stdout = IndigoLogger()

		tmpconfig = {'API_KEY': "qyy0od74EpMz2P8X1fmAfyoxKod4t1Fo"}
		if 'ACCESS_TOKEN' in pluginPrefs:
			tmpconfig['ACCESS_TOKEN'] = pluginPrefs['ACCESS_TOKEN']
		if 'AUTHORIZATION_CODE' in pluginPrefs:
			tmpconfig['AUTHORIZATION_CODE'] = pluginPrefs['AUTHORIZATION_CODE']
		if 'REFRESH_TOKEN' in pluginPrefs:
			tmpconfig['REFRESH_TOKEN'] = pluginPrefs['REFRESH_TOKEN']
		indigo.server.log(u"constructed config: %s" % json.dumps(tmpconfig))

		# Create an ecobee object with the config dictionary
		indigo.server.log(u"initializing ecobee module")
		self.ecobee = Ecobee(config = tmpconfig)
		indigo.server.log(u"ecobee module initialized")


	def __del__(self):
		indigo.PluginBase.__del__(self)


	def startup(self):
		indigo.server.log(u"startup called")

	def shutdown(self):
		indigo.server.log(u"shutdown called")

	def request_pin(self, valuesDict = None):
		indigo.server.log(u"requesting pin")
		self.ecobee.request_pin()
		indigo.server.log(self.ecobee.pin)
		valuesDict['pin'] = self.ecobee.pin
		return valuesDict

	def runConcurrentThread(self):
		try:
			while True:
				for dev in indigo.devices.iter("self"):
					if not dev.enabled:
						continue

					# Plugins that need to poll out the status from the thermostat
					# could do so here, then broadcast back the new values to the
					# Indigo Server.
					# self._refreshStatesFromHardware(dev, False, False)

				self.sleep(3)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.
