#! /usr/bin/env python
# -*- coding: utf-8 -*-

FORMAT_STRING = "{0:.1f}"

class TemperatureScale:

	def report(self, dev, stateKey, reading):
		txt = self.format(reading)
		dev.updateStateOnServer(key=stateKey, value=self.convert(reading), decimalPlaces=1, uiValue=txt)
		return txt

	def format(self, reading):
		return u"%s%s" % (FORMAT_STRING.format(self.convert(reading)), self.suffix())

class Fahrenheit(TemperatureScale):
	def convert(self, reading):
		return float(reading) / 10
	def suffix(self):
		return u"°F"

class Celsius(TemperatureScale):
	def convert(self, reading):
		return ((float(reading) / 10) - 32) * 5 / 9
	def suffix(self):
		return u"°C"

class Kelvin(TemperatureScale):
	def convert(self, reading):
		return (((float(reading) / 10) - 32) * 5 / 9) + 273.15
	def suffix(self):
		return u"K"

class Rankine(TemperatureScale):
	def convert(self, reading):
		return (float(reading) / 10) + 459.67
	def suffix(self):
		return u"°Ra"
