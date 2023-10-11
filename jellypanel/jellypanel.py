from ast import literal_eval
from sys import argv

import socket
import tkinter 
import threading
import time

ID = 'Id'
BODY = 'Body'
METHOD = 'Target'
ATTEMPTS = 'Tries'
ACTIVE = 'Active'
REPLIED = 'Replied'

PERIOD = 'Period'
OWNED = 'Owned'

NAME = 'Name'
THIS = 'I am'
ABOUT = 'About'
ADDRESS = 'Address'

def msg_id (n, f, a, t = None):
	if t is None:
		t = time.time()

	return time.localtime(t)[:6] + (n, f.__name__) + a	

class traffic_ship:
	 
	looping = False
	heartbeat_looping = False

	contacts = {}
	contacts_addr = {}
	contacts_status = {}
	contacts_sem = threading.Semaphore()
	
	heartbeat_sem = threading.Semaphore()
	heartbeat_paused = False
	heartbeat_interval = 5

	delay_interval = 0.1
	reliable_interval = 0.2
	reliable_timeout = 3

				
	reliable_inbox = {}
	reliable_inbox_sem = threading.Semaphore()

	def __init__ (self, ip, port, name = None, password = None):
		self.password = None		
		self.addr = ip,port
		self.name = name
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # udp 
		self.sock.bind(self.addr)
		print('\n\t',repr(self.name),'@',self.addr)

	def add_contact (self, address, name = None):

		self.contacts_sem.acquire()
		
		if address not in self.contacts or (name != None and self.contacts[address] != name):
			if name is None:
				c = len(self.contacts)
				a = len(self.contacts_addr)			
				s = len(self.contacts_status)

				while True:
					name = f'unnamed host {s}{a}{c}'				
					if name not in self.contacts_addr:
						break

					a -= 1
					c += 1

			self.contacts[address] = name
			self.contacts_addr[address] = address					

			print('Added',name,address)

		self.contacts_sem.release()	

	def start (self):	
		self.looping = True

	def stop (self):	
		self.looping = False

	def exit (self, password = None, reply_to = None):
		if reply_to:
			print('Remote exit call from',reply_to)
			if self.password != password:
				print('Denied!')
				return 
			self.reliable_send(0,reply_to,self.remote_exit_sender)
		self.stop()

	def remote_exit (self, host, password = None):
		if len(host) > 2:
			if password is None:
				password = host[2]
			host = host[:2]

		self.reliable_send(password, host, self.exit)

	def remote_exit_sender (self, response, reply_to):	
		print('Remote exit call to',reply_to,'responded',response)

	def mainloop (self):	
		threading.Thread(target=self.heartbeat_loop, daemon=True).start()

		threading.Thread(target=self.sock_loop, daemon=True).start()

	def sock_loop (self):
		print('Start socket recovery')
		while self.looping:			 
			try:
				threading.Thread(target=self.redirect, args=self.sock.recvfrom(1024)).start()
			except ConnectionAbortedError:	
				print('Connection aborted')
			except ConnectionResetError:	
				print('Connection reset')				
			
		print('Stop socket recovery')	

	def heartbeat_loop (self):	 	
		
		self.heartbeat_start()
		print('Start heartbeat\t',self.looping,self.heartbeat_looping)

		while self.looping and self.heartbeat_looping:
			self.heartbeat_sem.acquire() # pause 
			self.heartbeat_sem.release()

			i = self.heartbeat_interval
			beat = {
				PERIOD: i,				
				OWNED: {

				}
			}
			

			self.contacts_sem.acquire()
			for c in self.contacts:
				print('Heartbeat to',self.contacts[c],c)				
				self.send(beat,c,self.get_heartbeat)
			self.contacts_sem.release()

			if i > 0:
				time.sleep(i)
		print('Stop heartbeat\t',self.looping,self.heartbeat_looping)

	def get_heartbeat (self, body, reply_to):
		print(reply_to,body)
		self.contacts_sem.acquire()
		self.contacts_status[reply_to] = time.time(), body[PERIOD]		
		self.contacts_sem.release()

		if reply_to not in self.contacts_addr:
			self.send_meet(reply_to)

	def heartbeat_start (self):
		self.heartbeat_looping = True

	def heartbeat_stop (self):	
		self.heartbeat_looping = False

	def heartbeat_pause (self):	
		if self.heartbeat_paused:
			print('Heartbeat already paused')
		else:	
			self.heartbeat_paused = self.heartbeat_sem.acquire()
			print('Heartbeat paused',self.heartbeat_paused)

	def heartbeat_play (self):		
		if self.heartbeat_paused:
			self.heartbeat_paused = False
			self.heartbeat_sem.release()
			print('Heartbeat resumed')
		else:	
			print('Hearbeat already playing')

	def meet (self, meeting, reply_to):
		address = meeting[ADDRESS]
		if address != self.addr: # it != talking to itself 
			self.add_contact(address, meeting[NAME])

		if meeting[THIS]: # it is the unknown host or an alias
			about = meeting[ABOUT]
			if about != address:
				self.contacts_sem.acquire()	
				self.contacts_addr[about] = address
				if about in self.contacts: # moved
					self.contacts.pop(about)
				self.contacts_sem.release()
			return 	

		meeting[ADDRESS] = self.addr
		meeting[NAME] = self.name
		meeting[THIS] = True
		return self.reliable_send(meeting, reply_to, self.meet)

	def send_meet (self, unknown):
		return self.reliable_send({
				THIS: False, 
				ABOUT: unknown, 
				ADDRESS: self.addr, 
				NAME:self.name
			}, unknown, self.meet)
	
	def discover (self, contacts, reply_to = None):	
		added = 0
		for c in contacts:
			if c not in self.contacts_addr:# and type(c) == tuple:
				added += 1				

				self.contacts_sem.acquire()
				self.contacts_addr[c] = c
				self.contacts_sem.release()

				self.send_meet(c)
		print('Added',added,'contact' + ('s' * (added != 1)))		

		if reply_to != None and not added:		
			self.contacts_sem.acquire()
			for c in self.contacts_addr:
				if c not in contacts:
					added = True
					break						
			else:	
				print('0 new contacts to introduce')
			self.contacts_sem.release()	

		if added:
			for c in (self.contacts):
				self.send_discover(c)
				
				
	def send_discover (self, to, contacts = None):			 
		return self.reliable_send(list(self.contacts_addr if contacts is None else contacts), to, self.discover)

	def reliable_send (self, body, to, method, callback = None):				

		self.reliable_inbox_sem.acquire()
		id = msg_id(len(self.reliable_inbox), self.reliable_send, self.addr)	
		sem = threading.Semaphore()
		msg = {
			BODY:body, METHOD:method.__name__, 
			ATTEMPTS:True, REPLIED: False, ID:id
		}		
		self.reliable_inbox[id] = msg, sem
		self.reliable_inbox_sem.release()

		sem.acquire()
		msg[ACTIVE] = self.reliable_timeout
		t = time.time() + self.reliable_timeout
		while time.time() <= t:
			self.send(msg, to, self.reliable_redirect)

			if self.reliable_interval > 0:
				time.sleep(self.reliable_interval)

			if sem.acquire(blocking=False):
				sem.release()
				msg[REPLIED] = True
				break

			msg[ATTEMPTS] += 1
		msg[ACTIVE] = t	

		if callback != None:
			callback(msg)
		return msg	

	def reliable_redirect (self, data, reply_to):	

		id = data[ID]
		first = False
		self.reliable_inbox_sem.acquire()
		if id not in self.reliable_inbox:
			self.reliable_inbox[id] = data
			data[ACTIVE] += time.time()
			first = True
		elif type(self.reliable_inbox[id]) == tuple:				
			sem = self.reliable_inbox[id][1]
			first = not sem.acquire(blocking=False)								
			sem.release()			
		self.reliable_inbox_sem.release()

		if first:
			threading.Thread(target=self.redirect, args=(data, reply_to)).start()
		
		self.send(id, reply_to, self.reliable_sender)	

	def reliable_sender (self, id, reply_to):	
		self.reliable_inbox_sem.acquire()
		sem = self.reliable_inbox[id][1]
		self.reliable_inbox_sem.release()

		sem.acquire(blocking=False)
		sem.release()
		
		
		
		

	def error (self, error, reply_to):
		print('ERROR @',reply_to,'\n\t',error)

	def send (self, body, to, method):
		if self.delay_interval > 0:
			time.sleep(self.delay_interval)
		self.sock.sendto(repr({
			METHOD:method.__name__, 
			BODY:body
		}).encode(), to)

	def redirect (self, data, reply_to):	
		try:
			if type(data) == bytes:
				data = data.decode()

			if type(data) == str:	
				data = literal_eval(data)				

			if type(data) == dict:			
				if METHOD in data and BODY in data:
					self.__getattribute__(data[METHOD])(data[BODY], reply_to=reply_to)	
					return 	
			for d in data:
				self.redirect(d,reply_to)

		except Exception as ex:
			err = f'{type(ex).__name__}:\t{ex}'		
		else:	
			err = f'Malformed package body'			
				
		err = f'{err}\nFrom:\t{reply_to}\n\t{repr(data)}'	

		print(err)		
		self.send(err,reply_to,self.error) 								

a = traffic_ship('localhost',65432)		
a.start()
a.mainloop()


b = traffic_ship('localhost',65431)
b.start()
b.mainloop()

b.add_contact(('localhost',65432))

input('\n\n\n')

class Shape:
	def __init__(self, canvas, shape_type, x, y, size=50, color="blue"):
		self.canvas = canvas
		self.shape_type = shape_type
		self.size = size
		self.color = color

		if self.shape_type == "square":
			self.draw_square(x, y)
		elif self.shape_type == "triangle":
			self.draw_triangle(x, y)

		self.canvas.tag_bind(self.shape, '<ButtonPress-1>', self.on_click)
		self.canvas.tag_bind(self.shape, '<B1-Motion>', self.on_drag)
		self.is_dragging = False

	def draw_square(self, x, y):
		self.shape = self.canvas.create_rectangle(
			x, y, x + self.size, y + self.size, fill=self.color)

	def draw_triangle(self, x, y):
		x1, y1 = x, y
		x2, y2 = x + self.size, y
		x3, y3 = x + self.size // 2, y - self.size
		self.shape = self.canvas.create_polygon(
			x1, y1, x2, y2, x3, y3, fill=self.color)

	def on_click(self, event):
		print('block')
		return
		self.is_dragging = True
		self.start_x = event.x
		self.start_y = event.y

	def on_drag(self, event):
		print(self.is_dragging, event)
		if self.is_dragging:
			dx = event.x - self.start_x
			dy = event.y - self.start_y
			self.canvas.move(self.shape, dx, dy)
			self.start_x = event.x
			self.start_y = event.y

	def stop_dragging(self):
		print('Stop')
		self.is_dragging = False

def create_shape(event):
	x = event.x
	y = event.y

	# Check if the click occurred on an existing shape
	overlapping_shapes = canvas.find_overlapping(x, y, x, y)
	if not overlapping_shapes:
		color = entry_color.get()
		shape_type = shape_var.get()
		
		if shape_type == "Square":
			shape = Shape(canvas, "square", x, y, color=color)
		elif shape_type == "Triangle":
			shape = Shape(canvas, "triangle", x, y, color=color)

def clear_canvas():
	canvas.delete("all")

root = tkinter.Tk()
root.title("Shapes on Canvas")

canvas = tkinter.Canvas(root, width=400, height=400, bg="white")
canvas.pack()

frame = tkinter.Frame(root)
frame.pack(pady=10)

label_color = tkinter.Label(frame, text="Color:")
label_color.grid(row=0, column=0)
entry_color = tkinter.Entry(frame)
entry_color.grid(row=0, column=1)

shape_var = tkinter.StringVar(value="Square")
shape_label = tkinter.Label(frame, text="Shape:")
shape_label.grid(row=1, column=0)
shape_option = tkinter.OptionMenu(frame, shape_var, "Square", "Triangle")
shape_option.grid(row=1, column=1)

create_button = tkinter.Button(frame, text="Create Shape")
create_button.grid(row=2, columnspan=2)
canvas.bind("<Button-1>", create_shape)

clear_button = tkinter.Button(frame, text="Clear Canvas", command=clear_canvas)
clear_button.grid(row=3, columnspan=2)

root.mainloop()
