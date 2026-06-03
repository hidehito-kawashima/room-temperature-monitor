import threading
import time
import humidity
from typing import Callable, List
import traceback

_callbacks = []
_callbacks_lock = threading.Lock()

_thread = None
_stop_event = threading.Event()

_last_temp = None
_last_hum = None

def register_callback(cb: Callable[[float, float], None]):
	with _callbacks_lock:
		_callbacks.append(cb)
	return cb
	
def unregister_callback(cb):
	with _callbacks_lock:
		try:
			_callbacks.remove(cb)
		except ValueError:
			pass
			
def _notify_all(temp,hum):
	with _callbacks_lock:
		cbs = list(_callbacks)
	for cb in cbs:
		try:
			cb(temp, hum)
		except Exception:
			traceback.print_exc()
		
def _round_val(v):
	try:
		if v is None:
			return None
		return round(float(v),1)
	except Exception:
		return None

def _worker(poll_interval):
	global _last_temp, _last_hum
	try:
		t, h = humidity.get_temp_hum()
		_last_temp = _round_val(t)
		_last_hum = _round_val(h)
	except Exception:
		_last_temp = None
		_last_hum = None
		
	while not _stop_event.wait(poll_interval):
		try:
			res = humidity.get_temp_hum()
			t_val = None
			h_val = None
			if isinstance(res, tuple):
				if len(res) >= 2:
					t_val, h_val = res[0], res[1]
			else:
				try:
					t_val = float(res)
				except Exception:
					t_val = None
					h_val = None
			
			new_t = _round_val(t_val)
			new_h = _round_val(h_val)
			
			temp_changed = (new_t is not None and new_t != _last_temp) or (new_t is None and _last_temp is not None)
			hum_changed = (new_h is not None and new_h != _last_hum) or (new_h is None and _last_hum is not None)
			
			if temp_changed or hum_changed:
				_last_temp = new_t
				_last_hum = new_h
				_notify_all(new_t, new_h)
		except Exception:
			traceback.print_exc()
			time.sleep(max(0.2,poll_interval))
			
def start(poll_interval = 1.0):
	global _thread, _stop_event
	if _thread is not None and _thread.is_alive():
		return 
	_stop_event.clear()
	_thread = threading.Thread(target = _worker, args = (poll_interval,), daemon = True)
	_thread.start()
	
def stop():
	global _thread, _astio_event
	_stop_event.set()
	if _thread is not None:
		_thread.join(timeout = 1.0)
		_thread = None
