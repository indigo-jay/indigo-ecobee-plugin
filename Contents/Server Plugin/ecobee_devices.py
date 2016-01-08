#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import indigo
import temperature_scale
import logging

HVAC_MODE_MAP = {
	'heat'        : indigo.kHvacMode.Heat,
	'cool'        : indigo.kHvacMode.Cool,
	'auto'        : indigo.kHvacMode.HeatCool,
	'auxHeatOnly' : indigo.kHvacMode.Heat, # TODO: is this right?
	'off'         : indigo.kHvacMode.Off
}

FAN_MODE_MAP = {
	'auto': indigo.kFanMode.Auto,
	'on'  : indigo.kFanMode.AlwaysOn
}

def _get_capability(obj, cname):
	ret = [c for c in obj.get('capability') if cname == c.get('type')][0]
	return ret

class EcobeeBase:
	temperatureFormatter = temperature_scale.Fahrenheit()

	def __init__(self, address, dev, pyecobee):
		self.log = logging.getLogger('indigo.ecobee.plugin')
		self.address = address
		self.dev = dev
		self.pyecobee = pyecobee
		self.name = address # temporary name until we get the real one from the server
		matchedSensor = self.updateServer()

	def updatable(self):
		if not self.dev.configured:
			self.log.debug('device %s not fully configured yet; not updating state' % self.address)
			return False
		if not self.pyecobee.authenticated:
			self.log.info('not authenticated to pyecobee yet; not initializing state of device %s' % self.address)
			return False
		ts = self.pyecobee.get_thermostats()
		if None == ts:
			self.log.warning('no thermostats found; authenticated?')
			return False
#		else:
#			indigo.server.log('thermostat data:')
#			indigo.server.log(json.dumps(ts, sort_keys=True, indent=4, separators=(',', ': ')))

		return True

	def _update_server_temperature(self, matchedSensor, stateKey):
		tempCapability = _get_capability(matchedSensor, 'temperature')
		return EcobeeBase.temperatureFormatter.report(self.dev, stateKey, tempCapability.get('value'))
		return temperature

	def _update_server_occupancy(self, matchedSensor):
		occupancyCapability = [c for c in matchedSensor.get('capability') if 'occupancy' == c.get('type')][0]
		occupied = ( 'true' == occupancyCapability.get('value') )
		self.dev.updateStateOnServer(key=u"occupied", value=occupied)
		return occupied


class EcobeeThermostat(EcobeeBase):
	def __init__(self, address, dev, pyecobee):
		EcobeeBase.__init__(self, address, dev, pyecobee)

	def updateServer(self):
		self.log.debug("updating thermostat from server")
		if not self.updatable():
			return

		thermostat = self.pyecobee.get_thermostat(0)
		runtime = thermostat.get('runtime')
		hsp = runtime.get('desiredHeat')
		csp = runtime.get('desiredCool')
		climate = thermostat.get('program').get('currentClimateRef')

		settings = thermostat.get('settings')
		hvacMode = settings.get('hvacMode')
		fanMode = runtime.get('desiredFanMode')

		status = thermostat.get('equipmentStatus')

		self.log.info('heat setpoint: %s, cool setpoint: %s, hvac mode: %s, fan mode: %s, climate: %s, status %s' % (hsp, csp, hvacMode, fanMode, climate, status))

		matchedSensor = [rs for rs in self.pyecobee.get_remote_sensors(0) if 'thermostat' == rs.get('type')][0]

		self.name = matchedSensor.get('name')

		self._update_server_temperature(matchedSensor, u'temperatureInput1')
		self._update_server_occupancy(matchedSensor)

		# humidity
		humidityCapability = _get_capability(matchedSensor, 'humidity')
		self.dev.updateStateOnServer(key="humidityInput1", value=float(humidityCapability.get('value')))

		EcobeeBase.temperatureFormatter.report(self.dev, "setpointHeat", hsp)
		EcobeeBase.temperatureFormatter.report(self.dev, "setpointCool", csp)
		self.dev.updateStateOnServer(key="hvacOperationMode", value=HVAC_MODE_MAP[hvacMode])
		self.dev.updateStateOnServer(key="hvacFanMode", value=FAN_MODE_MAP[fanMode])
		self.dev.updateStateOnServer(key="climate", value=climate)

		self.dev.updateStateOnServer(key="hvacHeaterIsOn", value=bool(status and ('heatPump' in status or 'auxHeat' in status)))
		self.dev.updateStateOnServer(key="hvacCoolerIsOn", value=bool(status and ('compCool' in status)))
		self.dev.updateStateOnServer(key="hvacFanIsOn", value=bool(status and ('fan' in status or 'ventilator' in status)))

		return matchedSensor



class EcobeeRemoteSensor(EcobeeBase):
	def __init__(self, address, dev, pyecobee):
		EcobeeBase.__init__(self, address, dev, pyecobee)

	def _matching_sensor(self):
		# should be exactly one; if not, then ... panic
		self.log.debug('finding matching sensor for %s' % self.address)
		return [rs for rs in self.pyecobee.get_remote_sensors(0) if self.address == rs.get('code')][0]

	def updateServer(self):
		if not self.updatable():
			return

		matchedSensor = self._matching_sensor()

		self.name = matchedSensor.get('name')

		self._update_server_temperature(matchedSensor, u'temperature')

		# if occupancy was detected, set the icon to show a 'tripped' motion sensor;
		# otherwise, just show the thermometer for the temperature sensor
		if self._update_server_occupancy(matchedSensor):
			self.dev.updateStateImageOnServer(indigo.kStateImageSel.MotionSensorTripped)
		else:
			self.dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)


		return matchedSensor
