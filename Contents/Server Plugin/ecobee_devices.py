import sys
import json
import indigo
import temperature_scale

def _get_capability(obj, cname):
	ret = [c for c in obj.get('capability') if cname == c.get('type')][0]
	return ret

class EcobeeBase:
	temperatureFormatter = temperature_scale.Fahrenheit()

	def __init__(self, address, dev, pyecobee):
		self.address = address
		self.dev = dev
		self.pyecobee = pyecobee
		self.name = address # temporary name until we get the real one from the server
		matchedSensor = self.updateServer()
		self.name = matchedSensor.get('name')

#		indigo.server.log(u"ecobee object initialized; matched sensor info: %s" % matchedSensor)
#		indigo.server.log(u"ecobee object %s initialized; indigo's name is %s, ecobee's name is %s" % (self.address, dev.name, self.name))

#		if matchedSensor:
#			self.name = matchedSensor.name
#		else:
#			self.name = ''

	def updatable(self):
		if not self.dev.configured:
			indigo.server.log('device %s not fully configured yet; not updating state' % self.address)
			return False
		if not self.pyecobee.authenticated:
			indigo.server.log('not authenticated to pyecobee yet; not initializing state of device %s' % self.address)
			return False
		if None == self.pyecobee.get_thermostats():
			indigo.server.log('no thermostats found; authenticated?')
			return False

		return True

	def _update_server_temperature(self, matchedSensor, stateKey):
		tempCapability = _get_capability(matchedSensor, 'temperature') # [c for c in matchedSensor.get('capability') if 'temperature' == c.get('type')][0]
		temperature = EcobeeBase.temperatureFormatter.format(tempCapability.get('value'));
		self.dev.updateStateOnServer(key=stateKey, value=temperature)
		return temperature

	def _update_server_occupancy(self, matchedSensor):
		occupancyCapability = [c for c in matchedSensor.get('capability') if 'occupancy' == c.get('type')][0]
		if 'true' == occupancyCapability.get('value'):
			occupied = True
			occupiedString = "occupied"
		else:
			occupied = False
			occupiedString = "unoccupied"

		self.dev.updateStateOnServer(key=u"occupied", value=occupied)
		return occupiedString


class EcobeeThermostat(EcobeeBase):
	def __init__(self, address, dev, pyecobee):
		EcobeeBase.__init__(self, address, dev, pyecobee)

	def updateServer(self):
#		indigo.server.log("updating thermostat from server")
		if not self.updatable():
			return

		matchedSensor = [rs for rs in self.pyecobee.get_remote_sensors(0) if 'thermostat' == rs.get('type')][0]

		temperature = self._update_server_temperature(matchedSensor, u'temperatureInput1')
		occupiedString = self._update_server_occupancy(matchedSensor)

		# humidity
		humidityCapability = _get_capability(matchedSensor, 'humidity')
		humidity = float(humidityCapability.get('value'));
		self.dev.updateStateOnServer(key="humidityInput1", value=humidity)


		combinedState = "%s/%s/%s" % (temperature, humidity, occupiedString)
		self.dev.updateStateOnServer(key=u"combinedState", value=combinedState)

		indigo.server.log("thermostat '%s' (%s) updated: %s" % (self.name, self.address, combinedState))

		return matchedSensor



class EcobeeRemoteSensor(EcobeeBase):
	def __init__(self, address, dev, pyecobee):
		EcobeeBase.__init__(self, address, dev, pyecobee)

	def _matching_sensor(self):
		# should be exactly one; if not, then ... panic
#		indigo.server.log('finding matching sensor for %s' % self.address)
		return [rs for rs in self.pyecobee.get_remote_sensors(0) if self.address == rs.get('code')][0]

	def updateServer(self):
#		indigo.server.log("updating remote sensor from server")
		if not self.updatable():
			return

		matchedSensor = self._matching_sensor()

		temperature = self._update_server_temperature(matchedSensor, u'temperature')
		occupiedString = self._update_server_occupancy(matchedSensor)

		combinedState = "%s/%s" % (temperature, occupiedString)
		self.dev.updateStateOnServer(key=u"combinedState", value=combinedState)

		indigo.server.log("remote sensor '%s' (%s) updated: %s" % (self.name, self.address, combinedState))

		return matchedSensor
