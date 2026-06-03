import time
try:
	import smbus2
except Exception:
	smbus2 = None

LCD_I2C_ADDR = 0x3e
I2C_BUS = 1

_lcd = None


class LCDAQM:
	def __init__(self,addr,bus):
		if smbus2 is None:
			raise RuntimeError("smbus2 not available for LCD")
		self.i2c_addr = addr
		self.busnum = bus
		self.bus = smbus2.SMBus(self.busnum)
		self.count = 0
		self.line = 1
		

	def send_command(self,cmd):
		self.bus.write_byte_data(self.i2c_addr,0x00,cmd)
	
	def send_data(self,data):
		self.bus.write_byte_data(self.i2c_addr,0x40,data)
		time.sleep(0.001)
	
	def init_display(self):
		self.send_command(0x38)
		time.sleep(0.05)
		self.send_command(0x39)
		time.sleep(0.05)
		self.send_command(0x14)
		time.sleep(0.05)
		self.send_command(0x70)
		time.sleep(0.05)
		self.send_command(0x56)
		time.sleep(0.05)
		self.send_command(0x6C)
		time.sleep(0.2)
		self.send_command(0x38)
		time.sleep(0.05)
		self.send_command(0x0C)
		time.sleep(0.05)
		self.send_command(0x01)
		time.sleep(0.05)
		
		self.count = 0
		self.lne = 1
		
	def set_line1(self):
		self.send_command(0x80)
		
	def set_line2(self):
		self.send_command(0xC0)
		
	
	def clear(self):
		self.send_command(0x01)
		time.sleep(0.002)
	
		
	def display_message(self,msg):
		parts = msg.split("\n",1)
		line1 = parts[0][:8]
		if len(parts) > 1:
			line2 = parts[1][:8] 
		else:
			line2 = parts[0][8:]
		
		self.clear()
		
		self.set_line1()
		for ch in line1:
			self.send_data(ord(ch))
			
		self.set_line2()
		for ch in line2:
			self.send_data(ord(ch))
		
	def close(self):
		try:
			try:
				self.clear()
			except Exception:
				pass
			if hasattr(self, 'bus') and self.bus is not None:
				try:
					if hasattr(self.bus, 'close'):
						self.bus.close()
				except Exception:
					pass
		except Exception:
			pass
					
def init_lcd_if_available():
	global _lcd
	if _lcd is not None:
		return _lcd
	try:
		_lcd = LCDAQM(addr = LCD_I2C_ADDR, bus=I2C_BUS)
		_lcd.init_display()
		return _lcd
	except Exception:
		_lcd = None
		return None
		
def update_lcd(temp, hum):
	global _lcd
	
	def _normalize(v):
		if v is None:
			return None
		if isinstance(v,(int,float)):
			try:
				return float(v)
			except Exception:
				return None
		
		if isinstance(v,str):
			s = v.strip()
			if s in('','--','--.-','-','N/A','nan'):
				return None
			s_num = s.replace('℃','').replace('C','').replace('c','').replace('％','').replace('%','').replace(',','.')
			try:
				return float(s_num)
			except Exception:
				return None
		return None
		
	t_val = _normalize(temp)
	h_val = _normalize(hum)
				
	if _lcd is None:
		try:
			init_lcd_if_available()
		except Exception:
			return
	if _lcd is None:
		return
	try:
		_lcd.clear()
		t = '--.-' if t_val is None else f"{temp:.1f}"
		h = '--.-' if h_val is None else f"{hum:.1f}"
		_lcd.display_message(f"T:{t}C\nH:{h}%")
	except Exception:
		pass
		
def clear():
	global _lcd
	try:
		if _lcd is not None:
			_lcd.clear()
	except Exception:
		pass
	
def close():
	global _lcd
	try:
		if _lcd is not None:
			_lcd.close()
	except Exception:
		pass

