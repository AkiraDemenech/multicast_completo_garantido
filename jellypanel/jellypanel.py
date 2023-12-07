from ast import literal_eval
from sys import argv

import socket
import tkinter 
import threading
import traceback
import time
import random

ID = 'Id'
BODY = 'Body'
METHOD = 'Target'
RECIPIENT = 'To'
REPLIED = 'Replied'


NAME = 'Name'
ADDRESS = 'Address'

def dummy (*a, **k):
	pass
	

debug = dummy
#debug = print


debug_meet = debug

debug_send = debug
debug_send_loop = debug
debug_receive_loop = debug
debug_reliable_receiver = debug
debug_reliable_sender = debug
debug_reliable_send = debug

debug_activity_loop = print
debug_heartbeat_loop = debug

debug_toplevel = debug
debug_rect_release = debug
debug_rect_click = debug
debug_rect_drag = debug
debug_rect_move = debug

#debug_reliable_receiver = debug_reliable_sender = print

class rect:

	is_dragging = False

	def __init__(self, id, jellypanel, x, y, width, height, color):
		self.x = x 
		self.y = y
		self.id = id
		self.jellypanel = jellypanel
		self.canvas = jellypanel.canvas				
		self.rect = self.canvas.create_rectangle(x, y, x + width, y + height, fill=color)

		self.canvas.tag_bind(self.rect, '<ButtonRelease-1>', self.release)
		self.canvas.tag_bind(self.rect, '<ButtonPress-1>', self.click)
		self.canvas.tag_bind(self.rect, '<B1-Motion>', self.drag)			
		

	def click (self, event):
		debug_rect_click('Clicar')
		# pedir exclusividade do objeto para o servidor
		self.jellypanel.mutex(self.id)
		#self.is_dragging = True
		self.x_clicked = self.x - event.x
		self.y_clicked = self.y - event.y		

	def drag (self, event):
		debug_rect_drag('Arrastar',self.is_dragging)
		if self.is_dragging:			
			# enviar nova posição para o servidor
			self.jellypanel.move(self, event.x + self.x_clicked, event.y + self.y_clicked)

	def move (self, x, y):		
		debug_rect_move(x,y)
		self.canvas.move(self.rect, x - self.x, y - self.y)
		self.x = x
		self.y = y

	def release	(self, event):
		debug_rect_release('Soltar')
		self.jellypanel.mutex(self.id, False) # ceder a exclusividade do objeto
		self.is_dragging = self.x_clicked = self.y_clicked = False
		
		
		

class traffic_surf:
	 
	server_sem = threading.Semaphore() 
	white_sem = threading.Semaphore()

	
	server = {}	# quadros gerenciados
	white = {}	# quadros participando
	known = {}	# quadros conhecidos
	display_known = {} # botões dos quadros conhecidos
	display_current_white = {} # retângulos do quadro atual 

	current = None # quadro atual

				
	inbox = {}	# mensagens recebidas 
	outbox = []	# mensagens enviadas
	outbox_len = threading.Semaphore(0) # quantidade de mensagens esperando 
	outbox_sem = threading.Semaphore() 

	reliable_inbox = {} 
	reliable_inbox_sem = threading.Semaphore()

	contacts = {} # nomes dos contatos ativos
	contacts_addr = {} # endereços dos contatos
	contacts_activity = {} # situação dos contatos 
	contacts_sem = threading.Semaphore()

	root = tkinter.Tk()

	looping = True
	delay = 0.05
	reliable_timeout = 2
	reliable_interval = 0.1
	heartbeat_interval = 5
	max_size = 1024

	def __init__ (self, ip, port, name = None, password = None):
		self.password = password		
		self.start = time.time()
		self.num = random.randint(0,1<<24)
		self.addr = ip,port
		self.name = f'{ip} {port} {self.num}' if name == None else name
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP 
		self.sock.bind(self.addr)
		print('\n\t',repr(self.name),'@',self.addr)
	
		self.root.title(self.name)
		self.canvas = tkinter.Canvas(self.root, width=400, height=400, bg='beige')
		self.canvas.pack()

		self.canvas.bind('<Button-1>', self.create_rect)

		
		self.root.frame = tkinter.Frame(self.root)
		self.root.frame.pack(pady=10)

		
		self.entry_color = tkinter.Entry(self.root.frame)
		self.entry_color.insert(0, '#' + hex(self.num)[2:].zfill(6))
		self.entry_color.grid(row=0, column=0)

		self.numeric = self.root.frame.register(lambda s: (s.isdigit() or not len(s)))

		self.entry_height = tkinter.Entry(self.root.frame, validate=tkinter.ALL, validatecommand=(self.numeric, '%P'))
		self.entry_height.insert(0, str(random.randint(40,50)))
		self.entry_height.grid(row=0, column=1)

		self.entry_width = tkinter.Entry(self.root.frame, validate=tkinter.ALL, validatecommand=(self.numeric, '%P'))
		self.entry_width.insert(0, str(random.randint(30,60)))
		self.entry_width.grid(row=0, column=2)

		self.create_button = tkinter.Button(self.root.frame, text='Criar quadro em branco', command=self.create)
		self.create_button.grid(row=2, column=1)

		self.find_button = tkinter.Button(self.root.frame, text='Localizar quadros', command=self.find)
		self.find_button.grid(row=2, column=2)
		self.find_frame = tkinter.Frame(self.root.frame, bg='beige')
		self.find_frame.grid(row=3, columnspan=2)

		self.canvas_list = tkinter.Toplevel()
		self.canvas_list.title('Jellypanels conhecidos')

		self.canvas_list.scroll_frame = tkinter.Frame(self.canvas_list)
		self.canvas_list.scroll_frame.pack(fill=tkinter.BOTH, expand=True)

		self.canvas_list.canvas = tkinter.Canvas(self.canvas_list.scroll_frame)
		self.canvas_list.canvas.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)

		self.canvas_list.scrollbar = tkinter.Scrollbar(self.canvas_list.scroll_frame, orient=tkinter.VERTICAL, command=self.canvas_list.canvas.yview)
		self.canvas_list.scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
		self.canvas_list.canvas.configure(yscrollcommand=self.canvas_list.scrollbar.set)
		self.canvas_list.canvas.refresh = lambda event=None: debug_toplevel(event,self.canvas_list.canvas.update_idletasks(),self.canvas_list.canvas.config(scrollregion=self.canvas_list.canvas.bbox(tkinter.ALL)))
		self.canvas_list.bind('<Configure>', self.canvas_list.canvas.refresh)

		self.canvas_list.button_frame = tkinter.Frame(self.canvas_list.canvas)
		self.canvas_list.canvas.create_window((0, 0), window=self.canvas_list.button_frame, anchor=tkinter.NW)

		self.canvas_list.canvas.refresh()

	def mutex (self, rect_id, start=True):
		print('Exclusividade para',rect_id)

		self.white_sem.acquire()
		address = self.known[rect_id[1]]
		self.white_sem.release()

		threading.Thread(target=self.reliable_send, args=[self.msg(rect_id, address, self.mutex_request if start else self.mutex_release)]).start()

	def move (self, rect, x, y):
		rect.move(x,y)
		self.white_sem.acquire()
		address = self.known[rect.id[1]]
		self.white_sem.release()

		self.send(self.msg((rect.id, x, y), address, self.move_request))		

	def find (self):
		print('Localizar quadros')
		threading.Thread(target=self.reliable_send, args=[self.msg(self.known, c, self.find_request) for c in self.contacts]).start()
		self.update_known()
	
	def join (self, id):
		if self.current != id:			 
			self.current = id
			print('Ingressar em quadro',id)		
			self.canvas.delete(tkinter.ALL)
			self.canvas.configure(bg='white')

			self.white_sem.acquire()
			self.display_current_white.clear()				

			if id in self.white:
				for r in self.white[id]:
					last = self.white[id][r]
				#	print(r, last)
					threading.Thread(target=self.move_rect, args=[(r,last[1],last)]).start() # carregar última posição dos retângulos
			else:	
				self.white[id] = {}
				
		else:		
			self.white_sem.acquire()
		address = self.known[id]
		self.white_sem.release()	

		

		# solicitar participação para o servidor
		threading.Thread(target=self.reliable_send, args=[self.msg(id, address, self.join_request)]).start()		
		
		

	
	def create (self):
		print('Criar novo quadro em branco')
		t = time.localtime()[:6]		
		
		self.server_sem.acquire()
		c = 0
		while True:
			n = f'{c}{len(self.server)}{len(self.white)}{len(self.known)}'
			for m in self.server:
				if m[0] == n:	
					break
			else:		
				break
			c += 1	
		
		n = (n,) + self.addr + t
		self.server[n] = {}, set()
		self.server_sem.release()

		self.white_sem.acquire()
		self.known[n] = self.addr
		self.white_sem.release()
		
		self.join(n)	
		self.update_known()

	def create_rect (self, event):
		if self.current == None:
			return 

			

		if self.canvas.find_overlapping(event.x, event.y, event.x, event.y):
			return 
		
		# enviar informações do novo retângulo para o servidor do quadro atual

		self.white_sem.acquire()
		threading.Thread(target=self.reliable_send, args=[self.msg((self.current, (event.x, event.y, int(self.entry_width.get()), int(self.entry_height.get()), self.entry_color.get())), self.known[self.current], self.create_rect_request)]).start()
		self.white_sem.release()

		print('Criando retângulo')
				

	def move_rect (self, data, server = None):
		rect_id, rect_data, last = data
		id = rect_id[1]
		t = last[0]

		self.white_sem.acquire()
		if not id in self.known:
			threading.Thread(target=self.find).start()

		if not id in self.white:
			self.white[id] = {}	
			print('Adicionado quadro',id)

		if rect_id in self.white[id]:	
			l = self.white[id][rect_id]			
			if l[0] < t:
				l[0] = t
				last = l
			else:	
				rect_data = l[1]
		else:	
			print('Criado retângulo',*rect_id)
			self.white[id][rect_id] = last = last[:2]
		last[1] = rect_data
		
		if self.current == id:	 
			if rect_id in self.display_current_white:	
				self.display_current_white[rect_id].move(*rect_data[:2])	
			else:
				print('Mostrando retângulo')
				self.display_current_white[rect_id] = rect(rect_id, self, *rect_data)			
		self.white_sem.release()
		
	def move_request (self, pos, client):	
		rect_id, x, y = pos

		self.server_sem.acquire()		
		r, l = self.server[rect_id[1]][0][rect_id]
		data = rect_id, r, l
		l[0] = time.time()
		r[0] = x
		r[1] = y						
		if random.random() <= 0.3:
			self.send(*[self.msg(data, c, self.move_rect) for c in self.server[rect_id[1]][1] if c != client])
		self.server_sem.release()

		print(rect_id,'\t',x,y)


	def create_rect_request (self, rect, client):	
		id, rect = rect
		print('Quadro',id,'\t',rect)

		self.server_sem.acquire()
		t = time.time()
		last = [t, None]
		s, l = self.server[id]
		rect_id = (f'{len(self.server)}{len(s)}',) + client + time.localtime()[:6], id		
		s[rect_id] = list(rect), last#, threading.Semaphore()
		data = rect_id, rect, last
		transmission = [self.msg(data, c, self.move_rect) for c in l]
		self.server_sem.release()

		print('Enviando retângulo',*rect_id,'\t',*rect)
		self.reliable_send(*transmission)	


	

	def join_request (self, id, client):	
		print(client,'pediu para participar de',id)

		self.server_sem.acquire()
		self.server[id][-1].add(client)
		

			
		# envio seguro de todas as formas atualmente no quadro
		self.reliable_send(*[self.msg((r,) + self.server[id][0][r][:2], client, self.move_rect) for r in self.server[id][0]])
		self.server_sem.release()

	def find_request (self, known, client):
		print(client,'quer conhecer mais quadros')
		self.reliable_send(self.msg(self.known, client, self.find_response))	
		self.find_response(known, client)
		
	def find_response (self, known, client):
		self.white_sem.acquire()
		self.known.update(known)
		print('Quadros conhecidos:\t',self.known)
		self.white_sem.release()
		self.update_known()

	def mutex_request (self, rect_id, client):
		print(client,'solicitando exclusividade para',rect_id)
		self.contacts_sem.acquire()
		if client in self.contacts_addr:
			client = self.contacts_addr[client]
		self.contacts_sem.release()		

		self.server_sem.acquire()
		r,l = self.server[rect_id[1]][0][rect_id]
		r = True

		if l[1] == None:
			l[1] = client
			
		elif l[1] != client:	
			r = False
		self.server_sem.release()

		if r:
			self.reliable_send(self.msg(rect_id, client, self.mutex_response))
			print(client, 'autorizado!')

	def mutex_response (self, rect_id, server):				

		self.white_sem.acquire()
		self.display_current_white[rect_id].is_dragging = True
		self.white_sem.release()

		print('Exclusividade autorizada para', rect_id)

	def mutex_release (self, rect_id, client):
		print(client,'encerra a exclusividade de',rect_id)

		self.contacts_sem.acquire()
		if client in self.contacts_addr:
			client = self.contacts_addr[client]
		self.contacts_sem.release()	

		self.server_sem.acquire()		
		self.server[rect_id[1]][0][rect_id][1][1] = None		
		data = (rect_id,) + self.server[rect_id[1]][0][rect_id]
		transmission = [self.msg(data, c, self.move_rect) for c in self.server[rect_id[1]][1] if c != client]		
		self.server_sem.release()

		self.reliable_send(*transmission)

	def update_known (self):
		self.white_sem.acquire()			

		for k in self.known:
			if not k in self.display_known:
				b = tkinter.Button(self.canvas_list.button_frame, text=k[:3], command=lambda q=k:self.join(q))
				b.pack()
				self.display_known[k] = b
				print('Botão',k,'adicionado')
				
		self.white_sem.release()	

		
	#	self.canvas_list.update()		
		self.canvas_list.canvas.refresh()
		self.canvas_list.canvas.yview_moveto(0)
	#	self.canvas_list.canvas.update_idletasks()
	#	print('Botões de quadros conhecidos atualizados')

	 

	def print (self, a, reply_to=None, print_f = print):
		print_f(reply_to, '\n', a)

	def meet (self, contact, address = None):
		debug_meet('Conhecendo', contact, address)				
		
		if address != None:
			if contact[ADDRESS] == self.addr:	
				return 

			self.contacts_sem.acquire()
			self.contacts_addr[address] = self.contacts_addr[contact[ADDRESS]] = contact[ADDRESS]
			self.contacts[contact[ADDRESS]] = contact[NAME]
			for c in contact[BODY]:
				if not c in self.contacts:
					threading.Thread(target=self.meet, args=[c]).start()					
			self.contacts_sem.release()


			if contact[REPLIED]:
				return 
			contact = address	

		self.reliable_send(self.msg({
			NAME: self.name,
			ADDRESS: self.addr,
			REPLIED: address,			
			BODY: list(self.contacts)
		}, contact, self.meet))		




	def heartbeat_listener (self, interval, address):
		t = time.time()
		
		expected = t + interval
		
		self.contacts_sem.acquire()
		if address in self.contacts_activity:
			dt = max(interval, t - self.contacts_activity[address][1])
		else:	




	
			dt = interval
			threading.Thread(target=self.meet, args=[address]).start()

		self.contacts_activity[address] = dt, t, expected, expected + dt # dt[0] t[1] timeout[-1]	
		self.contacts_sem.release()

	def heartbeat_loop (self):

		while self.looping:
			debug_heartbeat_loop('Coração batendo')

				
				
			self.send(*[self.msg(self.heartbeat_interval, a, self.heartbeat_listener) for a in self.contacts])
			
			time.sleep(self.heartbeat_interval)

	def activity_loop (self):
		while self.looping:
			self.contacts_sem.acquire()
			for address in list(self.contacts_activity):
				if time.time() >= self.contacts_activity[address][-1]:
					debug_activity_loop(address,'caiu')
					self.contacts_activity.pop(address)
					
					address = self.contacts_addr[address]
					if address in self.contacts:
						self.contacts.pop(address)

						

			self.contacts_sem.release()	

			time.sleep(self.heartbeat_interval)

	def mainloop (self): 
		threading.Thread(target=self.send_loop,daemon=True).start()
		threading.Thread(target=self.receive_loop,daemon=True).start()
		threading.Thread(target=self.activity_loop,daemon=True).start()
		threading.Thread(target=self.heartbeat_loop,daemon=True).start()
		self.root.mainloop()
	

	def receive_loop (self):
		while self.looping:
			debug_receive_loop('Aguardando recebimentos')

			try:
				pack, addr = self.sock.recvfrom(self.max_size)				

				data = None
				data = literal_eval(pack.decode())
				
				body, method = self.redirect(data)
			except ConnectionResetError as conn_reset:
				debug_receive_loop(conn_reset)
				continue
			except:	
				debug_receive_loop('Erro de decodificação dos dados\t',pack,'\n',repr(data))
				continue

			debug_receive_loop(addr, '\t', method, '\n', body)
			threading.Thread(args=(body, addr), target=method).start()		

		
			

	def send_loop (self): # consumidor de mensagens 		

		
		
		
		
		while self.looping:
			debug_send_loop('Aguardando mensagens')
			self.outbox_len.acquire()
			debug_send_loop('Aguardando para enviar')
			self.outbox_sem.acquire()
			debug_send_loop('Enviando....')






				
			t = time.time()

			c = self.outbox_len._value
			while c >= 0:
				if self.outbox[c][0] <= t:
					debug_send_loop(c,'\t',self.outbox[c][1])
					m = self.outbox.pop(c)[1]
					self.sock.sendto(repr(m).encode(), m[RECIPIENT]) # tempo, destinatário, mensagem										
				c -= 1	

			d = len(self.outbox) - self.outbox_len._value  
			while d < 0: # se o contador estiver maior do que deveria
				d += 1
				if not self.outbox_len.acquire(blocking=False):
					break 
			else:
				if d > 0: # se o contador estiver menor do que deveria
					self.outbox_len.release(d)	


			self.outbox_sem.release()
	
	def send (self, *msgs):
		if not len(msgs):
			return 				 

		t = time.time() + self.delay 		
		debug_send('Aguardando fila')
		self.outbox_sem.acquire()
		debug_send('Adicionando mensagens para envio....')
		for msg in msgs:
			self.outbox.append((t,msg))
		self.outbox_len.release(len(msgs))			
		self.outbox_sem.release()	

	def reliable_send (self, *msgs):
		

		meta_msgs = []		
		self.reliable_inbox_sem.acquire()
		for m in msgs:
			msg_id = m[ID] = self.msg_id(len(self.reliable_inbox), self.reliable_receiver, m[RECIPIENT])			
			m = self.reliable_inbox[msg_id] = self.msg(m, m[RECIPIENT], self.reliable_receiver)									
			meta_msgs.append(m)			
			m[REPLIED] = False			
		self.reliable_inbox_sem.release()	


		timeout = time.time() + self.reliable_timeout

		while time.time() <= timeout:
			self.send(*meta_msgs)	
			time.sleep(self.reliable_interval)

			if sum(m[REPLIED] for m in meta_msgs) == len(meta_msgs):
				debug_reliable_send('Sucesso!')
				return True		
		return False


	def reliable_sender (self, msg_id, receiver):



		self.reliable_inbox_sem.acquire()				
		if msg_id in self.reliable_inbox:
			self.reliable_inbox[msg_id][REPLIED] = True
		debug_reliable_sender(msg_id,'\t',receiver)	
		self.reliable_inbox_sem.release()

	def reliable_receiver (self, body, sender):			
		self.print(body, sender, debug_reliable_receiver)
		
		msg_id = body[ID]
		self.reliable_inbox_sem.acquire()
		if (not msg_id in self.reliable_inbox) or (not ID in self.reliable_inbox[msg_id]):
			body[REPLIED] = True
			self.reliable_inbox[msg_id] = body							
			body, method = self.redirect(body)			
			threading.Thread(target=method, args=(body, sender)).start()
		self.reliable_inbox_sem.release()

		self.send(self.msg(msg_id, sender, self.reliable_sender))
		

	def redirect (self, msg): 

		method = self.__getattribute__(msg[METHOD])
		body = msg[BODY]

		return body, method

	def msg (self, body, to, method):
		return {BODY: body, METHOD: method.__name__, RECIPIENT: to}

	def msg_id (self, n, f, a, t = None):
		if t is None:
			t = time.time()

		return time.localtime(t)[:6] + (n, f.__name__) + a

	def election (self, host, address = None): 	
		if address == None:
			# verifica se é necessária eleição para o host
			self.white_sem.acquire()
			for k in self.white:
				if self.known[k] == host:
					print('Nova eleição para quadro',k)
					threading.Thread(args=[self.msg({
						ID: k,
						BODY: len(self.server),
						ADDRESS: self.addr						 
					}, c, self.election) for c in self.contacts], target=self.reliable_send).start()
			self.white_sem.release()
			return 

		if len(self.server) < host[BODY]: 
			host[BODY] = len(self.server)
			host[ADDRESS] = self.addr
			self.reliable_send(*[self.msg(host, c, self.election) for c in self.contacts])

			
if __name__ == '__main__':
	jellypanel = traffic_surf(argv[1], int(argv[2]))
	contacts = []
	for f in argv[3:]:
		h = None
		for g in open(f,'r').read().split():
			if h == None:
				h = g
			else:
				print(h,g)
				contacts.append((h,int(g)))	
				h = None
	
	def add ():
		time.sleep(8)
		for c in contacts:
			print(c)
			jellypanel.meet(c)	

	threading.Thread(target=add, daemon=True).start()

	jellypanel.mainloop()
