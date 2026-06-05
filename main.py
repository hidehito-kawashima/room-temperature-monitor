from flask import Flask, render_template,jsonify, Response
import signal
import json
import queue
import argparse
import sys
import threading
import webbrowser
import time
import humidity
import watcher
import lcd

try:
	import monitor
except Exception:
	monitor = None
	
app = Flask(__name__)

_client_queues = []
_client_lock = threading.Lock()

_monitor_instance = None
_args = None
def display_str(v):
	if v is None:
		return "--.-"
	try:
		return f"{round(float(v),1):.1f}"
	except Exception:
		return "--.-"
		
@app.route('/', methods = ['GET'])
def index():
	temp_val,hum_val = humidity.get_temp_hum()
	
	temp_disp = display_str(temp_val)
	hum_disp = display_str(hum_val)
	return render_template('index.html', temp=temp_disp, hum=hum_disp,data=None,jikoku=None)
	
@app.route('/api',methods=['GET'])
def api():
	temp,hum = humidity.get_temp_hum()
	temp_disp = display_str(temp)
	hum_disp = display_str(hum)
	return jsonify({
	"temp": temp_disp,
	"hum": hum_disp
	})

@app.route('/stream')
def stream():
	def gen(q):
		try:
			while True:
				try:
					payload = q.get(timeout=1)
				except queue.Empty:
					yield ':\n\n'
					continue
				yield f"data: {payload}\n\n"
		except GeneratorExit:
			pass
			
	q = queue.Queue()
	with _client_lock:
		_client_queues.append(q)
	try:
		return Response(gen(q), mimetype='text/event-stream')
	finally:
		with _client_lock:
			try:
				_client_queues.remove(q)
			except ValueError:
				pass
				
def _broadcast_to_clients(temp, hum):
	data = json.dumps({"temp": None if temp is None else round(temp,1),"hum": None if hum is None else round(hum, 1)})
	with _client_lock:
		for q in list(_client_queues):
			try:
				q.put_nowait(data)
			except Exception:
				pass
				
				
def _on_sensor_change(temp,hum):
	try:
		if _monitor_instance is not None:
			_monitor_instance.update_display(temp, hum)
	except Exception as e:
		print("monitor update error:", e)
		
	if _args and _args.lcd:
		try:
			lcd.update_lcd(temp, hum)
		except Exception as e:
			print("lcd update error:", e)
		
		try:
			_broadcast_to_clients(temp, hum)
		except Exception as e:
			print("broadcast error:", e)
				
def _cleanup_and_exit(signum = None, frame = None):
	print('Received signal {}, cleaning up...'.format(signum))
	try:
		watcher.stop()
	except Exception as e:
		print('watcher.stop error:', e)
	try:
		if _monitor_instance is not None:
			_monitor_instance.stop()
	except Exception as e:
		print('monitor.stop error:', e)
	try:
		humidity.stop()
	except Exception as e:
		print('humidity.stop error:', e)
	try:
		lcd.close()
	except Exception as e:
		print('lcd.close error:', e)
	print('Cleanup done, exiting.')
	time.sleep(0.1)
	sys.exit(0)
	
signal.signal(signal.SIGINT, _cleanup_and_exit)
signal.signal(signal.SIGTERM, _cleanup_and_exit)

def _run_flask_thread(host = '0.0.0.0', port=5000, debug=False):
	app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--lcd', action='store_true', help='Enable LCD updates')
	parser.add_argument('--browser', action='store_true', help='Open browser on start')
	parser.add_argument('--no-monitor', action='store_true', help='Do not show Tk monitor')
	parser.add_argument('--port', type=int , default=5000,help='Flask port')
	parser.add_argument('--debug', action='store_true',help='Flask debug')
	args = parser.parse_args()
	_args=args
	
	if args.lcd:
		try:
			lcd.init_lcd_if_available()
		except Exception as e:
			print("init_lcd_if_available failed:", e)
		
	try:
		if not getattr(humidity, '_started_by_main', False):
			humidity.start(poll_interval=5)
			try:
				setattr(humidity, '_started_by_main', True)
			except Exception:
				pass
	except Exception as e:
		print('warning: humidity.start() failed:', e)
			
	flask_thread = threading.Thread(target=_run_flask_thread, kwargs={'host':'0.0.0.0','port':args.port,'debug':args.debug},daemon = True)
	flask_thread.start()
	time.sleep(0.2)
	if args.browser:
		try:
			webbrowser.open(f'http://127.0.0.1:{args.port}')
		except Exception:
			pass
	
	watcher.register_callback(_on_sensor_change)
	watcher.start(poll_interval=1.0)
	
	if not args.no_monitor:
		if monitor is not None and hasattr(monitor, 'LargeMonitor'):
			try:
				_monitor_instance = monitor.LargeMonitor()
				_monitor_instance.run()
			except Exception as e:
				print('monitor failed to start or crashed:', e)
				print('Flask is still runnning - open http://127.0.0.1:5000 in your browser')
				try:
					while True:
						time.sleep(1)
				except KeyboardInterrupt:
					_cleanup_and_exit(signal.SIGINT, None)
		else:
			print('monitor module not available; running Flask only.')
			try:
				while True:
					time.sleep(1)
			except KeyboardInterrupt:
				_cleanup_and_exit(signal.SIGINT, None)
	else:
		try:
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			_cleanup_and_exit(signal.SIGINT, None)
							
