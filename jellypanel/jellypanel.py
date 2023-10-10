from ast import literal_eval
from sys import argv

import socket
import tkinter 
import threading
import time

BODY = 'Body'
METHOD = 'Target'

#HEARTBEAT = 'Heartbeat'
PERIOD = 'Period'
OWNED = 'Owned'

#MEET = 'Meet'
NAME = 'Name'
THIS = 'I am'
ABOUT = 'About'
ADDRESS = 'Address'

#DISCOVER = 'Discover'
CONTACTS = 'Contacts'

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

	def __init__ (self, ip, port, name = None):
				
		self.addr = ip,port
		self.name = name
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # udp 
		self.sock.bind(self.addr)
		print('\n\t',repr(self.name),'@',self.addr)

	def add_contact (self, address, name = None):

		self.contacts_sem.acquire()
		
		if (not address in self.contacts) or (name != None and self.contacts[address] != name):
			if name == None:
				c = len(self.contacts)
				a = len(self.contacts_addr)			
				s = len(self.contacts_status)

				while True:
					name = f'unnamed host {s}{a}{c}'				
					if not name in self.contacts_addr:
						break

					a -= 1
					c += 1

			self.contacts[address] = name
			self.contacts_addr[address] = self.contacts_addr[name] = address					

			print('Added',name,address)

		self.contacts_sem.release()

	def start (self):	
		self.looping = True

	def stop (self):	
		self.looping = False

	def exit (self):
		self.stop()

	def mainloop (self):	
		threading.Thread(target=self.heartbeat_loop, daemon=True).start()


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
			self.contacts_sem.release()

			if i > 0:
				time.sleep(i)
		print('Stop heartbeat\t',self.looping,self.heartbeat_looping)

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

	def send (self, body, to, method):
		if self.delay_interval > 0:
			time.sleep(self.delay_interval)
		self.sock.sendto(repr({
			METHOD:method.__name__, 
			BODY:body
		}).encode(), to)

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
