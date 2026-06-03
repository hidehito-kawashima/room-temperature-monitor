import sys
import signal
import time
import threading
from tkinter import Tk, Label, StringVar, CENTER,BOTH, TOP, Frame, LEFT, RIGHT

class LargeMonitor:
	def __init__(self,time_poll_sec = 1.0):
		if Tk is None:
			raise RuntimeError('tkinter is not available on this system')
			
		self.time_poll_sec = time_poll_sec
		self._stop_event = threading.Event()
		
		self.root = Tk()
		self.root.title("Env monitor")
		self.root.attributes("-fullscreen", True)
		self.root.configure(bg = "#ffffff")
		
		self.temp_var = StringVar(value="--.- ℃")
		self.hum_var = StringVar(value = "--.- %")
		self.date_var = StringVar(value = "----/--/--")
		self.time_var = StringVar(value="--:--:--")
		
		
		self.left_frame = Frame(self.root, bg = "#ffffff")
		self.right_frame = Frame(self.root, bg="#ffffff")
		
		self._last_display_temp = None
		self._last_display_hum = None
		
		self.left_frame.pack(side = LEFT, fill=BOTH, expand=True)
		self.right_frame.pack(side=RIGHT, fill=BOTH, expand=True)
		
		self.temp_label = Label(self.right_frame, textvariable = self.temp_var, fg="#000000", bg="#ffffff", anchor=CENTER)
		self.hum_label = Label(self.right_frame, textvariable = self.hum_var,fg="#000000", bg="#ffffff", anchor=CENTER)
		self.time_label = Label(self.left_frame, textvariable = self.time_var, fg ="#000000", bg = "#ffffff", anchor=CENTER)
		self.date_label = Label(self.left_frame, textvariable = self.date_var,  fg ="#000000", bg = "#ffffff",anchor=CENTER)
		
		self.date_label.pack(side=TOP)
		self.time_label.pack(side=TOP)
		self.temp_label.pack(side=TOP)
		self.hum_label.pack(side=TOP)
		
		signal.signal(signal.SIGINT, self._on_signal)
		signal.signal(signal.SIGTERM, self._on_signal)
		self.root.bind("<Escape>", lambda e: self.stop())
		
		self.root.after(100,self._adjust_fonts)
		
		self._schedule_time_update()
		
	def _adjust_fonts(self):
		w=self.root.winfo_screenwidth()
		h=self.root.winfo_screenheight()
		left_w = max(20, int(w*0.5))
		right_w = max(20,int(w*0.5))
		
		date_size = max(5,int(min(left_w/10, h*0.4)))
		temp_size=max(5, int(min(right_w/10,h*0.4)))
		hum_size=max(5,int(min(right_w/10,h*0.4)))
		time_size=max(5,int(min(left_w/10,h*0.4)))
		try:
			self.temp_label.config(font=("Noto Sans JP", temp_size, "bold"))
			self.hum_label.config(font=("Noto Sans JP", hum_size, "bold"))
			self.time_label.config(font=("Noto Sans JP", time_size, "bold"))
			self.date_label.config(font=("Noto Sans JP", time_size, "bold"))
		except Exception:
			pass
			
	def _schedule_time_update(self):
		if self._stop_event.is_set():
			return
		self._update_time()
		self.root.after(int(self.time_poll_sec * 1000), self._schedule_time_update)
		
	def _update_time(self):
		now = time.localtime()
		self.time_var.set(time.strftime("%H:%M:%S",now))
		self.date_var.set(time.strftime("%Y/%m/%d", now))
		
		
	def update_display(self,temp_val, hum_val):
		def apply_update(t = temp_val, h = hum_val):
			if t is None:
				self.temp_var.set("--.-℃")
			else:
				try:
					self.temp_var.set(f"{float(temp_val):.1f}℃")
				except Exception:
					self.temp_var.set("--.-℃")
			if h is None:
				self.hum_var.set("--.-%")
			else:
				try:
					self.hum_var.set(f"{float(hum_val):.1f}%")
				except Exception:
					self.hum_var.set("--.-%")
			self._last_display_temp = t
			self._last_display_hum = h
			now = time.localtime()
			self.time_var.set(time.strftime("%H:%M:%S", now))
			self.date_var.set(time.strftime("%Y/%m/%d", now))
						
		try:
			self.root.after(0, apply_update)
		except Exception:
			pass
							
		
	def run(self):
		try:
			self.root.mainloop()
		except KeyboardInterrupt:
			self.stop()
			
	def _on_signal(self,signum,frame):
		self.root.after(0, self.stop)
		
	def stop(self):
		if self._stop_event.is_set():
			return
		self._stop_event.set()
		try:
			self.root.destroy()
		except Exception:
			pass
			
			
