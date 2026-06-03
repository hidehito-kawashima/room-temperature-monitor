import time
import threading

try:
	import smbus2
except Exception:
	smbus2 = None
	
_thread = None
_lock = threading.Lock()
_stop_event = threading.Event()

I2C_BUS = 1

_sensor = None
_last_temp = None
_last_hum = None
		
class BME280I2C:
	def __init__(self,addr=None,bus=1):
		if smbus2 is None:
			raise RuntimeError("smbus2 not available")
		self.addr = addr
		self.busnum = bus
		self.bus = smbus2.SMBus(self.busnum)
		
		
		if self.addr is None:
			for a in (0x76,0x77):
				try:
					chip = self.bus.read_byte_data(a,0xD0)
					if chip in (0x60,0x58):
						self.addr = a
						break
				except Exception:
					pass
			if self.addr is None:
				raise RuntimeError("BME280 not found at 0x76/0x77")
					
		self.T = 0.0
		self.H = 0.0
		self.t_fine = 0.0
		self._read_calibration()
		
		try:
			self.bus.write_byte_data(self.addr,0xF2,0x01)
			self.bus.write_byte_data(self.addr,0xF4,0x27)
			self.bus.write_byte_data(self.addr,0xF5,0xA0)
		except Exception as e:
			raise RuntimeError("Failed to configure BME280: {}".fomat(e))
			
	def _s16(self,val):
		return val - 65536 if val & 0x8000 else val
		
	def _s8(self,val):
		return val - 256 if val & 0x80 else val
		
	def _s12(self,val):
		return val -4096 if val & 0x800 else val
		
		
	def _read_calibration(self):
		calib = self.bus.read_i2c_block_data(self.addr,0x88,24)
		self.dig_T1=calib[0] | (calib[1] << 8)
		self.dig_T2 = self._s16(calib[2] | (calib[3] << 8))
		self.dig_T3 = self._s16(calib[4] | (calib[5] << 8))
		
		self.dig_H1 = self.bus.read_byte_data(self.addr, 0xA1)
		calib_h = self.bus.read_i2c_block_data(self.addr,0xE1,7)
		self.dig_H2 = self._s16(calib_h[0] | (calib_h[1] << 8))
		
		self.dig_H3 = calib_h[2]
		h4_raw = (calib_h[3] << 4) | (calib_h[4] &0x0F)
		self.dig_H4 = self._s12(h4_raw)
		h5_raw = (calib_h[5] <<4) | ((calib_h[4] >> 4)&0x0F)
		self.dig_H5 = self._s12(h5_raw)
		self.dig_H6 = self._s8(calib_h[6])
		
	def meas(self):
		try:
			data = self.bus.read_i2c_block_data(self.addr,0xF7, 8)
			adc_T=(data[3] << 12) | (data[4] << 4)| (data[5] >> 4)
			self.T = self._compensate_T(adc_T)
			adc_H = (data[6] << 8) | data[7]
			self.H = self._compensate_H(adc_H)
			
			return True
		except Exception as e:
			print("BME280 Error;",e)
			return False
			
	def _compensate_T(self,adc_T):
		var1 = (adc_T / 16384.0 - self.dig_T1 / 1024.0) * self.dig_T2
		var2 = ((adc_T / 131072.0 - self.dig_T1 / 8192.0) ** 2) * self.dig_T3
		self.t_fine = var1 + var2
		T = self.t_fine / 5120.0
		return T
		
	def _compensate_H(self,adc_H):
		h = self.t_fine - 76800.0
		if h == 00:
			return 0.0
		h = (adc_H - (self.dig_H4 * 64.0 + (self.dig_H5 / 16384.0)*h)) * (self.dig_H2 / 65536.0 * (1.0 +(self.dig_H6 / 67108864.0)* h * (1.0+(self.dig_H3 / 67108864.0)*h)))
		if h > 100.0:
			h = 100.0
		elif h < 0.0:
			h = 0.0
		return h
		
def _ensure_sensor():
	global _sensor
	if _sensor is not None:
		return True
	try:
		_sensor = BME280I2C(addr=None, bus=I2C_BUS)
		return True
	except Exception as e:
		_sensor = None
		return False

def _read_once():
	global _last_temp, _last_hum
	with _lock:
		updated = False
		if _ensure_sensor():
			try:
				ok = _sensor.meas()
				if ok:
					_last_temp = _sensor.T
					_last_hum = _sensor.H
			except Exception:
				pass
					
def _worker(interval):
	while not _stop_event.wait(interval):
		_read_once()

def start(poll_interval = 1):
	global _thread
	if _thread is not None and _thread.is_alive():
		return
	_read_once()
	_stop_event.clear()
	_thread = threading.Thread(target=_worker, args=(poll_interval,),daemon = True)
	_thread.start()
	
def stop():
	_stop_event.set()
	global _thread
	if _thread is not None:
		_thread.join(timeout=1)
		_thread = None
			
def get_temp_hum():
	global _last_temp, _last_hum
		
	try:
		if _ensure_sensor():
			try:
				ok = _sensor.meas()
				if ok:
					with _lock:
						_last_temp = _sensor.T
						_last_hum = _sensor.H
					return _last_temp, _last_hum
				else:
					return _last_temp, _last_hum
			except Exception:
				return _last_temp, _last_hum
		else:
			return _last_temp, _last_hum
	except Exception:
		return _last_temp, _last_hum
