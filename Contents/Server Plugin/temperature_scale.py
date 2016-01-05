FORMAT_STRING = "{0:.1f}"

def _format(f):
	return float(FORMAT_STRING.format(f))

class Fahrenheit:
	def format(self, reading):
		return _format(float(reading) / 10)

class Celsius:
	def format(self, reading):
		# 5/9*((F/10)-32)
		return _format(((float(reading) / 10) - 32) * 5 / 9)

class Kelvin:
	def format(self, reading):
		return _format((((float(reading) / 10) - 32) * 5 / 9) + 273.15)

class Rankine:
	def format(self, reading):
		return _format((float(reading) / 10) + 459.67)
