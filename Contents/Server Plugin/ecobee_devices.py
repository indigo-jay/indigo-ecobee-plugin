from pyecobee import Ecobee
import sys
import json
import indigo

class EcobeeRemoteSensor:
	def __init__(self, address, dev, ecobee):
		self.address = address
		self.dev = dev
		self.ecobee = ecobee
		self.updateServer()

	def _matching_sensor(self):
		# should be exactly one; if not, then ... panic
#		indigo.server.log('finding matching sensor for %s' % self.address)
		return [rs for rs in self.ecobee.get_remote_sensors(0) if self.address == rs.get('code')][0]

	def updateServer(self):
#		indigo.server.log("updating remote sensor from server")
		if not self.dev.configured:
			indigo.server.log('remote sensor %s not fully configured yet; not updating state' % self.address)
			return
		if not self.ecobee.authenticated:
			indigo.server.log('not authenticated to ecobee yet; not initilizing state of remote sensor %s' % self.address)
			return
		if None == self.ecobee.get_thermostats():
			indigo.server.log('no thermostats found; authenticated?')
			return
		matchedSensor = self._matching_sensor()

		# should be exactly one; if not, then ... panic
		tempCapability = [c for c in matchedSensor.get('capability') if 'temperature' == c.get('type')][0]
		temperature = float(tempCapability.get('value')) / 10;

		# ditto
		occupancyCapability = [c for c in matchedSensor.get('capability') if 'occupancy' == c.get('type')][0]
		if 'true' == occupancyCapability.get('value'):
			occupied = True
			occupiedString = "occupied"
		else:
			occupied = False
			occupiedString = "unoccupied"

		combinedState = "%s/%s" % (temperature, occupiedString)

		self.dev.updateStateOnServer(key=u"temperature", value=temperature)
		self.dev.updateStateOnServer(key=u"occupied", value=occupied)
		self.dev.updateStateOnServer(key=u"combinedState", value=combinedState)

		indigo.server.log('remote sensor %s updated: %s' % (self.address, combinedState))


class EcobeeThermostat:
	def __init__(self, address):
		self.address = address
