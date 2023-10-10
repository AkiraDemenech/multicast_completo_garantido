import tkinter as tk

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

root = tk.Tk()
root.title("Shapes on Canvas")

canvas = tk.Canvas(root, width=400, height=400, bg="white")
canvas.pack()

frame = tk.Frame(root)
frame.pack(pady=10)

label_color = tk.Label(frame, text="Color:")
label_color.grid(row=0, column=0)
entry_color = tk.Entry(frame)
entry_color.grid(row=0, column=1)

shape_var = tk.StringVar(value="Square")
shape_label = tk.Label(frame, text="Shape:")
shape_label.grid(row=1, column=0)
shape_option = tk.OptionMenu(frame, shape_var, "Square", "Triangle")
shape_option.grid(row=1, column=1)

create_button = tk.Button(frame, text="Create Shape")
create_button.grid(row=2, columnspan=2)
canvas.bind("<Button-1>", create_shape)

clear_button = tk.Button(frame, text="Clear Canvas", command=clear_canvas)
clear_button.grid(row=3, columnspan=2)

root.mainloop()
