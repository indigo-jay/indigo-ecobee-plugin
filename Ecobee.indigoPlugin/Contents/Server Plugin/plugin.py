#! /usr/bin/env python
# -*- coding: utf-8 -*-

import pyecobee
import sys
import json
import indigo
from ecobee_devices import *
import temperature_scale
import logging
from indigo_logging_handler import IndigoLoggingHandler

logging.getLogger("requests").setLevel(logging.WARNING)

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


class Plugin(indigo.PluginBase):

	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = DEBUG

		self.active_remote_sensors = []
		self.active_thermostats = []
		self.active_smart_thermostats = []

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
		self.update_logging(bool(valuesDict['debuggingEnabled'] and "y" == valuesDict['debuggingEnabled']))
		return True

	def _setTemperatureScale(self, value):
		self.log.debug(u'setting temperature scale to %s' % value)
		EcobeeBase.temperatureFormatter = TEMP_FORMATTERS.get(value)

	def update_logging(self, is_debug):
		if is_debug:
			self.debug = True
			self.log.setLevel(logging.DEBUG)
			logging.getLogger("indigo.ecobee.plugin").setLevel(logging.DEBUG)
			self.log.debug("debug logging enabled")
		else:
			self.log.debug("debug logging disabled")
			self.debug=False
			self.log.setLevel(logging.INFO)
			logging.getLogger("indigo.ecobee.plugin").setLevel(logging.INFO)


	def startup(self):
		self.debugLog(u"startup called")

	def shutdown(self):
		self.debugLog(u"shutdown called")

	def request_pin(self, valuesDict = None):

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
		return get_thermostats(self.ecobee)

	def get_remote_sensors(self, filter="", valuesDict=None, typeId="", targetId=0):
		return get_remote_sensors(self.ecobee)

	def _get_keys_from_ecobee(self, valuesDict):
		valuesDict[ACCESS_TOKEN_PLUGIN_PREF] = self.ecobee.access_token
		valuesDict[AUTHORIZATION_CODE_PLUGIN_PREF] = self.ecobee.authorization_code
		valuesDict[REFRESH_TOKEN_PLUGIN_PREF] = self.ecobee.refresh_token
		return valuesDict

	def deviceStartComm(self, dev):
		dev.stateListOrDisplayStateIdChanged() # in case any states added/removed after plugin upgrade

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
			newProps["NumTemperatureInputs"] = 2
			# SHENANIGANS: the following property has to be set in order for us to report
			#   whether the thermostat is presently heating, cooling, etc.
			#   This was difficult to find.
			newProps["ShowCoolHeatEquipmentStateUI"] = True
			dev.replacePluginPropsOnServer(newProps)
			newDevice = EcobeeThermostat(dev.pluginProps["address"], dev, self.ecobee)
			self.active_thermostats.append(newDevice)
			indigo.server.log("added thermostat %s" % dev.pluginProps["address"])

		elif dev.model == 'Ecobee Smart Thermostat':
			# Add support for the thermostat's humidity sensor
			newProps = dev.pluginProps
			newProps["NumHumidityInputs"] = 1
			# SHENANIGANS: the following property has to be set in order for us to report
			#   whether the thermostat is presently heating, cooling, etc.
			#   This was difficult to find.
			newProps["ShowCoolHeatEquipmentStateUI"] = True
			dev.replacePluginPropsOnServer(newProps)
			newDevice = EcobeeSmartThermostat(dev.pluginProps["address"], dev, self.ecobee)
			self.active_smart_thermostats.append(newDevice)
			indigo.server.log("added smart thermostat %s" % dev.pluginProps["address"])

		# TODO: try to set initial name for new devices, as other plugins do.
		# However, this doesn't work yet. Sad clown.
		self.debugLog('device name: %s  ecobee name: %s' % (dev.name, newDevice.name))
		if dev.name == 'new device' and newDevice.name:
			dev.name = newDevice.name
			dev.replaceOnServer()
			self.debugLog('device name set to %s' % dev.name)

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
		elif dev.model == 'Ecobee Smart Thermostat':
			self.active_smart_thermostats = [
				st for st in self.active_smart_thermostats
					if st.address != dev.pluginProps["address"]
			]

	def updateAllDevices(self):
		for ers in self.active_remote_sensors:
			ers.updateServer()
		for t in self.active_thermostats:
			t.updateServer()
		for st in self.active_smart_thermostats:
			st.updateServer()

	########################################
	# Thermostat Action callback
	######################
	# Main thermostat action bottleneck called by Indigo Server.
	def actionControlThermostat(self, action, dev):
		###### SET HVAC MODE ######
		if action.thermostatAction == indigo.kThermostatAction.SetHvacMode:
			self._handleChangeHvacModeAction(dev, action.actionMode)

		###### SET FAN MODE ######
		#elif action.thermostatAction == indigo.kThermostatAction.SetFanMode:
			# self._handleChangeFanModeAction(dev, action.actionMode)

		###### SET COOL SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.SetCoolSetpoint:
			newSetpoint = action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"change cool setpoint", u"setpointCool")

		###### SET HEAT SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint:
			newSetpoint = action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"change heat setpoint", u"setpointHeat")

		###### DECREASE/INCREASE COOL SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseCoolSetpoint:
			newSetpoint = dev.coolSetpoint - action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"decrease cool setpoint", u"setpointCool")

		elif action.thermostatAction == indigo.kThermostatAction.IncreaseCoolSetpoint:
			newSetpoint = dev.coolSetpoint + action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"increase cool setpoint", u"setpointCool")

		###### DECREASE/INCREASE HEAT SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseHeatSetpoint:
			newSetpoint = dev.heatSetpoint - action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"decrease heat setpoint", u"setpointHeat")

		elif action.thermostatAction == indigo.kThermostatAction.IncreaseHeatSetpoint:
			newSetpoint = dev.heatSetpoint + action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"increase heat setpoint", u"setpointHeat")

		###### REQUEST STATE UPDATES ######
		#elif action.thermostatAction in [indigo.kThermostatAction.RequestStatusAll, indigo.kThermostatAction.RequestMode,
		# indigo.kThermostatAction.RequestEquipmentState, indigo.kThermostatAction.RequestTemperatures, indigo.kThermostatAction.RequestHumidities,
		# indigo.kThermostatAction.RequestDeadbands, indigo.kThermostatAction.RequestSetpoints]:
		#	self._refreshStatesFromHardware(dev, True, False)

	########################################
	# Resume Program callback
	######################
	def actionResumeProgram(self, action, dev):
		###### RESUME PROGRAM ######
                resume_all = "false"
                if action.props.get("resume_all"):
                        resume_all = "true"
                self._resumeProgram(dev, resume_all)

        def _resumeProgram(self, dev, resume_all):
                sendSuccess = False
                if self.ecobee.resume_program_id(dev.pluginProps["address"], resume_all) :
                        sendSuccess = True;
                if sendSuccess:
                        indigo.server.log(u"sent resume_program to %s" % dev.address)
                else:
                        indigo.server.log(u"Failed to send resume_program to %s" % dev.address, isError=true)

        ######################
	# Process action request from Indigo Server to change main thermostat's main mode.
	def _handleChangeHvacModeAction(self, dev, newHvacMode):
		hvac_mode = kHvacModeEnumToStrMap.get(newHvacMode, u"unknown")
		indigo.server.log(u"mode: %s --> set to: %s" % (newHvacMode, kHvacModeEnumToStrMap.get(newHvacMode)))
 		indigo.server.log(u"address: %s set to: %s" % (int(dev.address), kHvacModeEnumToStrMap.get(newHvacMode)))
		
		sendSuccess = False
		
		if self.ecobee.set_hvac_mode_id(dev.pluginProps["address"], hvac_mode):
			sendSuccess = True
			
		if sendSuccess:
			indigo.server.log(u"sent \"%s\" mode change to %s" % (dev.name, hvac_mode))
			if "hvacOperationMode" in dev.states:
				dev.updateStateOnServer("hvacOperationMode", newHvacMode)
		else:
			indigo.server.log(u"send \"%s\" mode change to %s failed" % (dev.name, hvac_mode), isError=True)

	######################
	# Process action request from Indigo Server to change a cool/heat setpoint.
	def _handleChangeSetpointAction(self, dev, newSetpoint, logActionName, stateKey):
		if newSetpoint < 40.0:
			newSetpoint = 40.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
		elif newSetpoint > 95.0:
			newSetpoint = 95.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.

		sendSuccess = False

		if stateKey == u"setpointCool":
			indigo.server.log(u"set cool to: %s and leave heat at: %s" % (newSetpoint, dev.heatSetpoint))
			if self.ecobee.set_hold_temp_id(dev.address, newSetpoint, dev.heatSetpoint):
				sendSuccess = True
		
		elif stateKey == u"setpointHeat":
			indigo.server.log(u"set heat to: %s and leave cool at: %s" % (newSetpoint, dev.coolSetpoint))
 			if self.ecobee.set_hold_temp_id(dev.address, dev.coolSetpoint, newSetpoint):
				sendSuccess = True		# Set to False if it failed.

		if sendSuccess:
			indigo.server.log(u"sent \"%s\" %s to %.1f°" % (dev.name, logActionName, newSetpoint))
			# And then tell the Indigo Server to update the state.
			if stateKey in dev.states:
				dev.updateStateOnServer(stateKey, newSetpoint, uiValue="%.1f °F" % (newSetpoint))
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" %s to %.1f° failed" % (dev.name, logActionName, newSetpoint), isError=True)

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
					# We need to also re-save the authentication credentials now, since self.ecobee.update() may change them
					self.pluginPrefs[ACCESS_TOKEN_PLUGIN_PREF] = self.ecobee.access_token
					self.pluginPrefs[AUTHORIZATION_CODE_PLUGIN_PREF] = self.ecobee.authorization_code
					self.pluginPrefs[REFRESH_TOKEN_PLUGIN_PREF] = self.ecobee.refresh_token
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.
