from ast import literal_eval
from sys import argv

import socket
import random
import threading
import time
import math

ID = 'Id'
TO = 'To'
FROM = 'From'
RETRANS = 'Retransmissions'
RESPONSE = 'Return'

METHOD = 'Target'
BODY = 'Body'

POSITION = 'Index'
NAME = 'Name'
DISCOVER = 'Meet'
HEARTBEAT = 'Heartbeat'
HEARTBEAT_INTERVAL = 0.9
DELAY_INTERVAL = 0.4

RELIABLE_INTERVAL = 0.1
RELIABLE_TIMEOUT = 3

DISCOVER_PROBABILITY = 1/12

ROWS = 'Rows'
REDUND = 'Redundancy'
MAX_ROWS = 1#3
REDUNDANCY = 1#2

MAX_SIZE = 1280
CONTACTS = {}
HOST = IP_PORT = None

if __name__ == '__main__':
	b = ''	
	for c in range(1,len(argv)):
		a = argv[c]
		print('\n',repr(a))					

		if b.startswith('-'):
			b = b.strip('-').upper()

			if b.startswith('DELAY') or b == 'INTERVAL':
				DELAY_INTERVAL = float(a)

			elif b.startswith('DISCOVER'):	
				DISCOVER_PROBABILITY = float(a)

			elif b.startswith('HEART') or b.startswith('BEAT'):
				HEARTBEAT_INTERVAL = float(a)				

			elif b == 'RELIABLE_TIMEOUT' or b.startswith('TIMEOUT'):	
				RELIABLE_TIMEOUT = float(a)		
				
			elif b.startswith('RELIABLE') or b.startswith('RETRANS'):	
				RELIABLE_INTERVAL = float(a)	
				
			elif b == 'REDUNDANCY':
				REDUNDANCY = int(a)
				
			elif 'ROWS' in b:
				MAX_ROWS = int(a)

			elif 'SIZE' in b:			
				MAX_SIZE = int(a)

			elif b.startswith('IP') or b == 'ADDRESS': # required
				if IP_PORT:
					print('Redefining address')

				IP_PORT = a.strip()					
			elif b.startswith('HOST') or b == 'NAME':
				HOST = a

			else:	
				print('\tOption',repr(b),'unknown')
		
		elif a in CONTACTS:
			print('\talready read')
		else:	
			try:
				with open(a,'r',encoding='utf8') as addresses:
					added = CONTACTS[a] = [ln.strip().split(maxsplit=1) for ln in addresses if len(ln) and not ln.isspace()]
					print('\t',len(added),'new contact' + ('s' * (len(added) != 1)))		
			except FileNotFoundError:		
				b = a.strip() 
			else:
				b = ''
		

else:
	CONTACTS = None



def nothing (*a, **k):
	pass

def package_id (num, address, name = '', method = nothing):
	return tuple(time.localtime()) + (num, method.__name__, name) + address

def ip_port (address):
	c = len(address)
	for k in range(len(address)):
		if address[k] == ':':
			c = k	 		
	return address[:c], int(address[c+1:])


def schedule (delay, target, *args, **kwargs):

	time.sleep(delay)

	return target(*args,**kwargs)


class multicast:

	contacts = {}
	contacts_addr = {}
	contacts_status = {}
	contacts_sem = threading.Semaphore()

	inbox = {}
	inbox_sem = threading.Semaphore()

	reliable_inbox = {}
	reliable_inbox_sem = threading.Semaphore()

	reliable_timeout = RELIABLE_TIMEOUT
	#reliable_timeout_sem = threading.Semaphore()

	reliable_interval = RELIABLE_INTERVAL
	#reliable_interval_sem = threading.Semaphore()

	heartbeat_interval = HEARTBEAT_INTERVAL
	#heartbeat_interval_sem = threading.Semaphore()
	heartbeat_pause_sem = threading.Semaphore()	
	heartbeat_paused = False
	looping = False
	discover = False

	discover_probability = DISCOVER_PROBABILITY

	
	delay_interval = DELAY_INTERVAL

	max_size = MAX_SIZE
	max_rows = MAX_ROWS
	redundancy = REDUNDANCY

	def __init__ (self, ip, port, name = None, password = None):
		self.password = password

		self.addr = ip, port
		self.name = name
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # udp 
		self.sock.bind(self.addr)
		print('\n',repr(self.name),'@',self.addr)

		self.direct = self.direct_multicast
		self.row = self.multicast = self.row_multicast

		self.rename = self.set_name
		self.heart = self.beat = self.heartbeat = self.set_heartbeat
		self.pause = self.heartbeat_pause
		self.play = self.resume = self.heartbeat_play

		self.delay = self.set_delay = self.set_delay_interval
		self.set_meeting_probability = self.set_discover_probability

		self.add = self.add_contact
		self.commands = [
			self.direct,
			self.row,

			self.add,
			self.rename,

			self.delay,

			self.heart,
			self.pause,
			self.resume,			
			self.help,
			self.exit,
			self.status,

			self.set_max_size,
			self.set_max_rows,
			self.set_redundancy,
			self.set_reliable_timeout,
			self.set_reliable_interval,
			self.set_discover_probability
		]

	def help (self):
		'''To show the docstrings of the commands'''
		attr = [c.__name__ for c in self.commands]
		attr.sort()

		all_attr = dir(self)				

		while len(attr):
			a = attr.pop(0)

			print('\n',repr(a))
			a = self.__getattribute__(a)

			if callable(a):
				doc = a.__doc__
				if doc:
					print('\t',doc)
						
				al = {repr(all_attr.pop(i)) for i in range(len(all_attr)-1,0,-1) if self.__getattribute__(all_attr[i]) == a and a.__name__ != all_attr[i]}		

				if len(al):					
					al = list(al)
					al.sort()	
					
					print(end='\n\tAliases:\t')		
					print(*al,sep=', ')
				print('\n')	

			else:		
				print('\t',repr(a),type(a))

	def status (self, addr = None, now = None):
		'''To analyze the last activity of all known hosts'''
		if now == None:
			now = time.time()
		if addr == None:	
			for a in self.contacts_status:
				print('\n',self.contact_name(a), self.status(a))
			return 	

		self.contacts_sem.acquire()
		if addr in self.contacts_status:
			last,expected = self.contacts_status[addr]	
			
			s = f'last seen {now - last}s ago, expected to '
			if expected <= last:
				s += 'never pulse again (declared heartbeat deactivation)'
			elif expected < now:
				s += f'have pulsed {now - expected}s ago'
			else:	
				s += f'pulse again in {expected - now}s'
		else:				
			s = 'never sent any heartbeats'
		self.contacts_sem.release()
		return s

	def add_contact (self, addr, name = None): # contacts_sem ()
		'''To add a new address.
		Requires the argument to be the tuple (<IP: string>, <Port: int>)

		If there is a third item in the tuple, use it's value as the contact name.
		'''
		if len(addr) > 2: # command line name 
			name = addr[2]
			addr = addr[:2]
		
		self.contacts_sem.acquire()
		if name:
			name = str(name) 			
			if addr in self.contacts and self.contacts[addr] == name:
			#	print(name,'already added')
				self.contacts_sem.release()
				return
				
		else: # '', (), [], {}, set(), 0, False, None				
			if addr in self.contacts:
			#	print(self.contacts[addr],'already known')
				self.contacts_sem.release()
				return	

			c = len(self.contacts)
			a = len(self.contacts_addr)			
			s = len(self.contacts_status)
			while True:
				name = f'unnamed host {s}{a}{c}'				
				if not name in self.contacts_addr:
					break
				c += 1
				a += 1

		if addr != self.addr:			
			self.contacts[addr] = name	
			self.contacts_addr[name] = self.contacts_addr[addr] = addr		
			print('Added',addr,'as',repr(name))
		self.contacts_sem.release()
		
		self.discover = True

	def meet_contacts (self, contacts, reply_to = None): # contacts_sem () contacts_sem ()
		added = False
	#	print('Meet', reply_to, contacts)

		for c in contacts:
			self.contacts_sem.acquire()
			if c != self.addr and not c in self.contacts:
				threading.Thread(target=self.add_contact, args=[c]).start()
				added += 1
			self.contacts_sem.release()

		time.sleep(self.heartbeat_interval)	

		if added and reply_to:
			self.discover = True
			self.contacts_sem.acquire()
			addresses = [c for c in self.contacts if c != reply_to and not c in contacts]
			self.contacts_sem.release()

			self.reliable_send(addresses, reply_to, self.meet_contacts)

	def contact_name (self, addr): # contacts_sem ()	
		name = str(addr)

		#self.contacts_sem.acquire()
		if addr in self.contacts:
			name = f'{self.contacts[addr]} @ {addr}'							
		#self.contacts_sem.release()	

		return name

	def set_name (self, rename):
		'''To change the name of the host
		This change might be received by it's contacts if they get the following heartbeats.'''			
		self.discover = True
		self.name = rename

	def set_discover_probability (self, probability):	
		'''To change the probability that a random heartbeat will ask to meet new contacts'''	
		self.discover_probability = probability
	
	def set_max_size (self, max_size=MAX_SIZE):
		'''To change the package buffer size (in bytes)'''
		self.max_size = max_size

	def set_max_rows (self, max_rows=MAX_ROWS):
		'''To change the number of groups for the row multicast sent by this host'''
		self.max_rows = max_rows

	def set_redundancy (self, redundancy):	
		'''To change the number of hosts per row/group that receives the starting row multicast transmission from this host'''
		self.redundancy = redundancy

	def set_reliable_timeout (self, timeout = RELIABLE_TIMEOUT):
		'''To change the waiting time for failure detection (in seconds)'''
		self.reliable_timeout = timeout

	def set_reliable_interval (self, interval = RELIABLE_INTERVAL):	
		'''To change the time period for retransmission (in seconds)'''
		self.reliable_interval = interval

	def set_delay_interval (self, delay):
		'''To change the time delay for all messages sent (in seconds)'''
		self.delay_interval = delay

	def set_heartbeat (self, interval=HEARTBEAT_INTERVAL):
		'''To change the heartbeat interval (in seconds)'''
		self.discover = True
		if interval < 0:
			interval = 0

		#self.heartbeat_interval_sem.acquire()				
		self.heartbeat_interval = interval
		#self.heartbeat_interval_sem.release()

		print('Set heartbeat interval to',self.heartbeat_interval,'s')

	def get_heartbeat (self, beat, reply_to=None): # contacts_sem ()
		#print(reply_to, '\t', beat)
		t = time.time()	
		if FROM in beat:		
			reply_to = beat[FROM]
		
		self.contacts_sem.acquire()					
		self.contacts_status[reply_to] = t, t + beat[HEARTBEAT] 	
		
		if (not reply_to in self.contacts) or self.contacts[reply_to] != beat[NAME] or DISCOVER in beat:		
			threading.Thread(target=self.reliable_send, args=([c for c in self.contacts if c != reply_to], reply_to, self.meet_contacts)).start()
			threading.Thread(target=self.add_contact, args=(reply_to, beat[NAME])).start()			
		#	print('Contacts')	

		self.contacts_sem.release()							

	def heartbeat_pause (self): # heartbeat_pause_sem (
		'''To pause the heartbeat
		The contacts won't be notified.'''
		if self.heartbeat_paused:
			print('Heartbeat already paused')
		else:	
			self.heartbeat_paused = self.heartbeat_pause_sem.acquire()						
			print('Heartbeat paused')

	def heartbeat_play (self): # heartbeat_pause_sem )	
		'''To resume the heartbeat.'''
		if self.heartbeat_paused:
			self.heartbeat_paused = False	
			self.heartbeat_pause_sem.release()
			print('Heartbeat resumed')
		else:	
			print('Heartbeat is playing')
	
	def heartbeat_loop (self): # heartbeat_pause_sem () contacts_sem ()
		i = True

		while i and self.looping: # heartbeat active 			
			self.heartbeat_pause_sem.acquire() # wait 
			self.heartbeat_pause_sem.release()

			#self.heartbeat_interval_sem.acquire()				
			i = self.heartbeat_interval
			#self.heartbeat_interval_sem.release()	
		#	print('Heartbeat',i)

			beat = {NAME:self.name, HEARTBEAT:i, FROM:self.addr}			
			if self.discover or random.random() <= self.discover_probability:				
				beat[DISCOVER] = self.discover
				self.discover = False

			self.contacts_sem.acquire()				
			for con in self.contacts:
				threading.Thread(target=self.send,args=(beat,con,self.get_heartbeat)).start() # send heartbeat
				# log heartbeat
			#	print('Sending heartbeat to',self.contact_name(con))
			self.contacts_sem.release()	

			time.sleep(i)			
			
		print('Stop heartbeat')		

	def input_loop (self):  
		self.looping += 1 
		while self.looping > 0:

			ln = input().strip()
			if ln:
				com = ln.split(maxsplit=1)

				try:
					m = self.__getattribute__(com[0])
				except AttributeError:	
					print('Unknown method or attribute',repr(com[0]))
					continue

				if not callable(m): 		
					print(com[0],'=',repr(m))
					continue

				try:
					a = [literal_eval(v) for v in com[1:] if len(v)]
				except:	
					print('Invalid argument',*com[1:])
					continue
				
				print(m.__name__, '\t', *a)	

				threading.Thread(target=m, args=a, daemon=True).start()					
				time.sleep(0.1)
		print('Input loop ended',self.looping)

	def mainloop (self):			
		threading.Thread(target=self.input_loop,daemon=False).start()
		threading.Thread(target=self.garbage_loop,daemon=True).start()
		threading.Thread(target=self.sock_loop,daemon=True).start()
		threading.Thread(target=self.heartbeat_loop,daemon=True).start()		

	def sock_loop (self):
		self.sock.settimeout(self.reliable_timeout)
		while self.looping > 0:
			try:
				pack, addr = self.sock.recvfrom(self.max_size)				
			except socket.timeout:	
				#print('No messages yet')
				continue	
			except ConnectionResetError as conn_reset:
				#print(conn_reset)
				continue

			data = literal_eval(pack.decode())

			#print(addr, '\n', data, '\n', pack)

			threading.Thread(target=self.__getattribute__(data[METHOD]), args=[data[BODY]], kwargs={'reply_to':addr}).start()

		print('Main loop ended')

	def garbage_loop (self):		
		while self.looping:
			break # remove old messages from inbox and reliable_inbox

	def remote_exit (self, a):		
		p = a[-1]
		if len(a) > 2:
			a = a[:-1]
		else:	
			a = a[0]

		self.contacts_sem.acquire()		
		if a in self.contacts_addr:	
			to = self.contacts_addr[a]
		else:	
			to = None
		self.contacts_sem.release()

		if to:
			print('Remote exit call to',a,'@',to)
			print(self.reliable_send(p, to, self.exit, print))

	def remote_exit_confirmation (self, looping, reply_to):
		print('\n',reply_to,'fully exited loop',looping)

	def exit (self, password = None, reply_to = None):
		'''To exit the program
		If there are multiple layers, exits just the top one.'''

		if reply_to != None:
			print('Remote exit call from',reply_to)
			
			if password != self.password:
				print('Denied: wrong password',repr(password))
				return 
			
			if self.looping > 1:
				print('This one is not enoght')
			else:
				self.reliable_send(self.looping, reply_to, self.remote_exit_confirmation)

		self.looping -= (self.looping > 0)
		print('Exit')

		

	def send (self, body, to, method):
		if self.delay_interval > 0:
			time.sleep(self.delay_interval)
		self.sock.sendto(repr({METHOD:method.__name__, BODY:body}).encode(), to)


	def reliable_send (self, body, to, method = None, callback = nothing): # reliable_inbox_sem ()		

		self.reliable_inbox_sem.acquire()

		pack_id = package_id(len(self.reliable_inbox), self.addr, self.name, self.reliable_send)
		pack = {ID:pack_id, RETRANS:False, METHOD:method.__name__, BODY:body}
		
		self.reliable_inbox[pack_id] = [pack]
		self.reliable_inbox_sem.release()

		#self.reliable_timeout_sem.acquire()
		timeout = self.reliable_timeout + time.time()
		#self.reliable_timeout_sem.release()

		success = None

		while time.time() <= timeout:

			self.send(pack, to, self.reliable_receiver)	

			time.sleep(self.reliable_interval)

			#self.reliable_inbox_sem.acquire()
			success = len(self.reliable_inbox[pack_id]) > 1
			#self.reliable_inbox_sem.release()

			if success:
			#	print(pack_id,'sent!')
				break

			pack[RETRANS] += 1
		#else:
		#	print(pack_id,'to',to,'timeout')			

		callback((body, to, success, pack[RETRANS]))	
		return success
	
	def reliable_sender (self, pack, reply_to): # reliable_inbox_sem ()
		pack_id = pack[ID]
		self.reliable_inbox_sem.acquire()
		self.reliable_inbox[pack_id].append(pack)
		self.reliable_inbox_sem.release()

	def reliable_receiver (self, msg, reply_to): # reliable_inbox_sem ()	
		pack_id = msg[ID]				
		r = self.__getattribute__(msg[METHOD])(msg[BODY], reply_to=reply_to)

		self.reliable_inbox_sem.acquire()			
		if not pack_id in self.reliable_inbox:			
			self.reliable_inbox[pack_id] = []									
		self.reliable_inbox[pack_id].append(msg)	
		t = len(self.reliable_inbox[pack_id])	
		self.reliable_inbox_sem.release()

		self.send({ID:pack_id, RETRANS:t, RESPONSE:r}, reply_to, self.reliable_sender)					
			
	def direct_multicast_confirmation(self, args): # inbox_sem () 
		pack, receiver, received, retrans = args
		
		self.inbox_sem.acquire()
		m,r,s = self.inbox[pack[ID]]
		if not r[receiver]:
			s.acquire()

		r[receiver] = received, retrans
		self.inbox_sem.release()

		

	def direct_multicast_receiver (self, msg, reply_to): # inbox_sem ()
		reply_to = msg[FROM]
		self.inbox_sem.acquire()
		if not msg[ID] in self.inbox:						
			self.inbox[msg[ID]] = msg
			print('\n',self.contact_name(reply_to), '\n\t', msg[BODY])			
		self.inbox_sem.release()

	def direct_multicast (self, msg): # inbox_sem ( contacts_sem () )
		'''To send the message for all the contacts and wait for each individual confirmation'''
		self.inbox_sem.acquire()
			
		pack_id = package_id(len(self.inbox) + random.random(), self.addr, self.name, self.direct_multicast)
		msg = {ID:pack_id, BODY:msg, FROM:self.addr}
			
		self.contacts_sem.acquire()
		rec = {c: None for c in self.contacts}
		self.contacts_sem.release()

		sem = threading.Semaphore(len(rec))			

		self.inbox[pack_id] = msg, rec, sem
		self.inbox_sem.release()

		for c in rec:
			threading.Thread(target=self.reliable_send, args=(msg, c, self.direct_multicast_receiver, self.direct_multicast_confirmation)).start()

		while len(rec):											

			conf = False 

			for c in tuple(rec):
				if rec[c]:
					received, retrans = rec.pop(c)
					print('\n\t',self.contacts[c],'@',c,'responded' if received else 'didn\'t confirm',*(('after', retrans + 1, 'transmissions') * (retrans > 0)),'\n',self.status(c))			
					conf = True
			
			time.sleep(self.reliable_interval * (not conf))		

		print('\nRetransmission interval:\t',self.reliable_interval,'\nTimeout:\t',self.reliable_timeout)			


	def row_multicast (self, msg): # inbox_sem ( contacts_sem () )
		'''To send the message just for some of the contacts and wait for row confirmations'''
		self.inbox_sem.acquire()

		self.contacts_sem.acquire()		
		rec = list(self.contacts)
		self.contacts_sem.release()

		
		group_size = math.ceil(len(rec) / self.max_rows)
		to = []
		while len(rec):
			to.append(rec[:group_size])
			rec = rec[group_size:]

		pack_id = package_id(len(self.inbox) + random.random(), self.addr, self.name, self.row_multicast)
		msgs = [({ID:pack_id, TO:r, FROM:self.addr, BODY:msg, ROWS:self.max_rows, REDUND:self.redundancy, RESPONSE:{}}, threading.Semaphore()) for r in to if len(r)]					
		
		sem = threading.Semaphore()
		sem.acquire()
		
		self.inbox[pack_id] = msgs, sem		
		self.inbox_sem.release()

		
		
		for m,s in msgs:
			threading.Thread(target=self.row_multicast_send, args=[m,s]).start()
			

		ft = self.reliable_timeout * group_size
		a = sem.acquire(timeout=ft)	# full row timeout 
		print('Full row confirmation timeout' * (not a))

		receivers = []

		
		for m,s in msgs:
			for r in m[RESPONSE]:
				receivers.append((r,'received!' if m[RESPONSE][r] else 'failed (timeout)'))

		for rec in to:
			for r in rec:
				receivers.append((r,'failed'))	
		

		receivers.sort()		
		for r,t in receivers:
			print('\n',self.contact_name(r),t,'\n',self.status(r))

		print('\nRetransmission interval:\t',self.reliable_interval,'\nIndividual timeout:\t',self.reliable_timeout,'\nFull timeout:\t',ft)	

		
	def row_multicast_send (self, msg, s = None, k = 0):
		
		
		a = r = 0		
		if s == None:
			release = acquire = nothing
		else:	
			acquire = s.acquire
			release = s.release

		while r < msg[REDUND]:			
			acquire()
			if k >= len(msg[TO]):
				release()
				break

			msg[POSITION] = k		

			a = bool(self.reliable_send(msg,msg[TO][k],self.row_multicast_receiver,nothing))	
			r += a				

			msg[RESPONSE][msg[TO].pop(k)] = a									
			release()
			
			
		
			
	#	print('Sent to',k,'of',len(msg[TO]),'and',r,'are confirmed')			

		acquire()
		if k >= len(msg[TO]):
			self.reliable_send(msg, msg[FROM], self.row_multicast_sender)	
		#	print('End of transmission')
		release()			

	def row_multicast_sender (self, msg, reply_to):	# inbox_sem () 
	#	print(reply_to, '\t', msg)
	
		
		self.inbox_sem.acquire()
		msgs, sem = self.inbox[msg[ID]]
		self.inbox_sem.release()

	#	print('Sender:',len(msgs),'rows')

		remaining = updated = confirmed = False
		
		for m,s in msgs:
		#	print(updated,confirmed,remaining)
			s.acquire()
			for c in set(m[RESPONSE]):
				if c in msg[RESPONSE] and msg[RESPONSE][c] and not m[RESPONSE][c]:
					m[RESPONSE][c] = True
					updated += 1					

			for c in list(m[TO]):# + list(m[RESPONSE]):
				if c in msg[RESPONSE]:# or c in msg[TO]:						
					m[RESPONSE][c] = msg[RESPONSE][c]
					m[TO].remove(c)				
					confirmed += 1
			remaining += len(m[TO])		
			s.release()

	#	print(updated,'updated and',confirmed,'new confirmed\n',remaining,'remaining.')

	#	print(updated, confirmed, remaining)

		if remaining:
			return
		
	#	print('Sent!')

		sem.acquire(blocking=False)
		sem.release()
			
	
	def row_multicast_receiver (self, msg, reply_to): # inbox_sem ()			

		self.inbox_sem.acquire()

		if msg[ID] in self.inbox:
		#	print('Already received')			 		
			self.inbox_sem.release()
			return
		
		sem = threading.Semaphore()
		self.inbox[msg[ID]] = msg, sem
		print('\n',self.contact_name(msg[FROM]),f'(via {self.contact_name(reply_to)})', '\n\t', msg[BODY])						

		self.inbox_sem.release()		

		a = self.addr
		try:
			i = msg[TO].index(self.addr)			
		except ValueError:
		#	print(self.addr,'not found')  
			i = msg[POSITION]

		if len(msg[TO]) > i:
			a = msg[TO].pop(i)

		msg[RESPONSE][a] = True
		self.row_multicast_send(msg, sem, i)


if CONTACTS != None:
	contacts_names = {}
	contacts_addresses = {}

	if IP_PORT != None:
		IP_PORT = ip_port(IP_PORT)

	for arq in CONTACTS:
		for c in CONTACTS[arq]:
			
			a = ip_port(c[0])			

			if a in contacts_addresses:
				print('Repeated address',a,set(c[1:] + contacts_addresses[a][1:]),{arq,contacts_addresses[a][0]})				
			
			contacts_addresses[a] = [arq] + c[1:]

			if len(c) > 1:
				n = c[1]
				if n in contacts_names:
					print('Repeated name',c[1],*{a,contacts_names[n][1]},{arq,contacts_names[n][0]})
				if a == IP_PORT:	
					if n != HOST:
						if HOST == None:
							HOST = n
							print('Host name:\t',HOST)
						else:	
							print('Host address has different name that the contact',repr(n),'at',repr(arq))
				elif n == HOST:			
					if IP_PORT == None:
						IP_PORT = a
						print('Host address:\t',IP_PORT)
					else:	
						print('Host name has different address that the contact',a,'at',repr(arq))

				contacts_names[n] = [arq, a]


	if IP_PORT == None:
		print('Host address is required.')
		exit(-1)	

	host = multicast(*IP_PORT,HOST)
	host.mainloop()

	for a in contacts_addresses:
		host.add_contact(a,*contacts_addresses[a][1:])

		
	
	