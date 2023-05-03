import gc
gc.collect()
from picographics import PicoGraphics, DISPLAY_TUFTY_2040, PEN_RGB332
import time, math, random
from pimoroni import Button
from time import sleep, sleep_ms
from PiicoDev_LIS3DH import PiicoDev_LIS3DH
from PiicoDev_Unified import sleep_ms
from machine import Pin, SPI, I2C, ADC

NODETECT = 0
HORIZONTAL = 1
VERTICAL = 2
BOTH = 3

motion = PiicoDev_LIS3DH(0, 1000000, Pin(4), Pin(5), 0x18)
motion.range = 2

gc.collect()
display = PicoGraphics(display=DISPLAY_TUFTY_2040, pen_type=PEN_RGB332)
gc.collect()
WIDTH, HEIGHT = display.get_bounds()

display.set_framebuffer(None) # not sure if this is needed
buffer = bytearray( int(WIDTH * HEIGHT))
display.set_framebuffer(buffer)

def isZero(a, rel_tol=0.0001):
    #print(a)
    return abs(a) <= rel_tol

print(WIDTH, HEIGHT)
WHITE = display.create_pen(255, 255, 255)
RED = display.create_pen(222, 20, 20)
GREEN = display.create_pen(20, 222, 20)
BLUE = display.create_pen(20, 20, 222)
BLACK = display.create_pen(0, 0, 0)

def copyBuffer(buffer):
    newBuffer = bytearray(int(WIDTH / 8) * HEIGHT)
    for idx in range(0, int(WIDTH * HEIGHT)):
        index = int(idx / 8)
        shift = int(7 - idx % 8)
        if buffer[idx] == RED:
            byte = 1 << shift
        else:
            byte = 0
        newBuffer[index] |= byte
    return newBuffer
        
def getPixel(x, y):
    if x >= WIDTH or x < 0 or y >= HEIGHT or y < 0:
        return False
    mazeX = int(x / 8)
    shift = int(7 - x % 8)
    mazeWidth = int(WIDTH / 8)
    return int(mazeBuffer[int(y) * mazeWidth + mazeX]) & (1 << shift) > 0 if True else False

lux_vref_pwr = Pin(27, Pin.OUT)
lux_vref_pwr.value(1)
lux = ADC(26)
vbat_adc = ADC(29)
vref_adc = ADC(28)

class Ball:
    oldX = 0
    oldY = 0
    x = 0
    y = 0
    display = None
    WIDTH = 0
    HEIGHT = 0
    r = 3
    background = bytearray(100)
    def __init__(self, display, buffer, WIDTH, HEIGHT, startX, startY, maze):
        self.x = startX
        self.y = startY
        self.oldX = startX
        self.oldY = startY
        self.display = display
        self.WIDTH = WIDTH
        self.HEIGHT = HEIGHT
        self.maze = maze
        self.buffer = buffer
        self.copyBackground(int(self.oldX - 3), int(self.oldY - 3))
        
    def copyBackground(self, wx, wy):
        def putBackground(x, y, value):
            self.background[int(y * 7 + x)] = value
        
        def getBuffer(x, y):
            return self.buffer[int(y * self.WIDTH + x)]
        
        for idy in range(0, 7):
            for idx in range(0, 7):
                putBackground(idx, idy, getBuffer(wx + idx, wy + idy))
        
    def pasteBackground(self, wx, wy):
        def getBackground(x, y):
            return self.background[int(y * 7 + x)]
        
        def putBuffer(x, y, value):
            self.buffer[int(y * self.WIDTH + x)] = value
            
        for idy in range(0, 7):
            for idx in range(0, 7):
                putBuffer(wx + idx, wy + idy, getBackground(idx, idy))
                
                
    def update(self, sx, sy, sz):
        self.oldX = self.x
        self.oldY = self.y
        self.x += sx * 2
        self.y += sy * 2
        checkResult = self.maze.check(self.x, self.y, self.oldX, self.oldY)
        if checkResult == BOTH:    
            self.x = int(self.oldX)
            self.y = int(self.oldY)
        if checkResult == HORIZONTAL:
            self.x = int(self.oldX)
            self.y = int(self.oldY)
        if checkResult == VERTICAL:    
            self.x = int(self.oldX)
            self.y = int(self.oldY)
        #if checkResult == HORIZONTAL or checkResult == VERTICAL:
        #    checkResult = self.maze.check(self.x, self.y, self.oldX, self.oldY)
        #    if checkResult == BOTH:    
        #        self.x = int(self.oldX)
        #        self.y = int(self.oldY)
        #    if checkResult == HORIZONTAL:    
        #        self.y = int(self.oldY)
        #    if checkResult == VERTICAL:    
        #        self.x = int(self.oldX)
      
        if self.x < self.r:
            self.x = self.r
        if self.y < self.r:
            self.y = self.r
        if self.x > self.WIDTH - self.r - 1:
            self.x = self.WIDTH - self.r - 1
        if self.y > self.HEIGHT - self.r - 1:
            self.y = self.HEIGHT - self.r - 1
            
            
    def isEnd(self):
        return self.x > 306 and self.y > 226
        
 
    def draw(self):
        self.pasteBackground(int(self.oldX - 3), int(self.oldY - 3))
        self.copyBackground(int(self.x - 3), int(self.y - 3))
        self.display.set_pen(WHITE)
        self.display.circle(int(self.x), int(self.y), self.r)


# Create a maze using the depth-first algorithm described at
# https://scipython.com/blog/making-a-maze/
# Christian Hill, April 2017.

class Cell:
    """A cell in the maze.
    A maze "Cell" is a point in the grid which may be surrounded by walls to
    the north, east, south or west.
    """

    # A wall separates a pair of cells in the N-S or W-E directions.
    wall_pairs = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}

    def __init__(self, x, y):
        """Initialize the cell at (x,y). At first it is surrounded by walls."""

        self.x, self.y = x, y
        self.walls = {'N': True, 'S': True, 'E': True, 'W': True}

    def has_all_walls(self):
        """Does this cell still have all its walls?"""

        return all(self.walls.values())

    def knock_down_wall(self, other, wall):
        """Knock down the wall between cells self and other."""

        self.walls[wall] = False
        other.walls[Cell.wall_pairs[wall]] = False


class Maze:
    """A Maze, represented as a grid of cells."""

    def __init__(self, nx, ny, ix=0, iy=0):
        """Initialize the maze grid.
        The maze consists of nx x ny cells and will be constructed starting
        at the cell indexed at (ix, iy).
        """
        self.nx, self.ny = nx, ny
        self.ix, self.iy = ix, iy
        self.maze_map = [[Cell(x, y) for y in range(ny)] for x in range(nx)]

        self.add_begin_end = False
        self.add_treasure = False
        self.treasure_x = random.randint(0, self.nx-1)
        self.treasure_y = random.randint(0, self.ny-1)

        # Give the coordinates of walls that you do *not* wish to be
        # present in the output here.
        self.excluded_walls = [((nx-1, ny), (nx, ny)),
                               ((0, 0), (0, 1))]

    def cell_at(self, x, y):
        """Return the Cell object at (x,y)."""

        return self.maze_map[x][y]


    def __str__(self):
        """Return a (crude) string representation of the maze."""

        maze_rows = ['-' * self.nx * 2]
        for y in range(self.ny):
            maze_row = ['|']
            for x in range(self.nx):
                if self.maze_map[x][y].walls['E']:
                    maze_row.append(' |')
                else:
                    maze_row.append('  ')
            maze_rows.append(''.join(maze_row))
            maze_row = ['|']
            for x in range(self.nx):
                if self.maze_map[x][y].walls['S']:
                    maze_row.append('-+')
                else:
                    maze_row.append(' +')
            maze_rows.append(''.join(maze_row))
        return '\n'.join(maze_rows)


    def write_svg(self, display):
       # """Write an SVG image of the maze to filename."""

        aspect_ratio = self.nx / self.ny
        # Pad the maze all around by this amount.
        padding = 0
        # Height and width of the maze image (excluding padding), in pixels
        height = 239 #500
        width = int(height * aspect_ratio)
        print (width, height)
        # Scaling factors mapping maze coordinates to image coordinates
        scy, scx = height / self.ny, width / self.nx

        def write_wall(display, x1, y1, x2, y2):
            """Write a single wall to the SVG image file handle f."""

            if ((x1, y1), (x2, y2)) in self.excluded_walls:
                return
            sx1, sy1, sx2, sy2 = x1*scx, y1*scy, x2*scx, y2*scy
            display.line(int(sx1), int(sy1), int(sx2), int(sy2))

        display.set_pen(RED)
        for x in range(self.nx):
            for y in range(self.ny):
                if self.cell_at(x, y).walls['S']:
                    x1, y1, x2, y2 = x, y+1, x+1, y+1
                    write_wall(display, x1, y1, x2, y2)
                if self.cell_at(x, y).walls['E']:
                    x1, y1, x2, y2 = x+1, y, x+1, y+1
                    write_wall(display, x1, y1, x2, y2)

            # Draw the North and West maze border, which won't have been drawn
            # by the procedure above.
        for x in range(self.nx):
            write_wall(display, x, 0, x+1, 0)
        for y in range(self.ny):
            write_wall(display, 0, y, 0, y+1)

    def detectWall(self, x, y):
        left = getPixel(int(x - 1), int(y))
        right = getPixel(int(x + 1), int(y))
        up = getPixel(int(x), int(y - 1))
        down = getPixel(int(x), int(y + 1))
        if (left or right) and not up and not down:
            print("HORIZONTAL")
            return HORIZONTAL
        if (up or down) and not left and not right:
            print("VERTICAL")
            return VERTICAL
        print("BOTH")
        return BOTH
        

    def check(self, x, y, oldX, oldY):
        dx = float(x - oldX)
        dy = float(y - oldY)
        a = float((dy + 0.00000001) / (dx + 0.00000001))
        b = y - a * x

        if getPixel(int(x), int(y)):
            return self.detectWall(x, y)
        if  getPixel(int(oldX), int(oldY)):
            print("ERROR")
            return BOTH 
        result = NODETECT
        maxDelta = int(max(dx, dy) * 3) + 10
        for idx in range(0, maxDelta):
            deltaX = dx / maxDelta
            nx = oldX + deltaX * idx
            ny = a * nx + b
            if getPixel(int(nx), int(ny)):
                result |= self.detectWall(nx, ny)
        return result

    def find_valid_neighbours(self, cell):
        """Return a list of unvisited neighbours to cell."""

        delta = [('W', (-1, 0)),
                 ('E', (1, 0)),
                 ('S', (0, 1)),
                 ('N', (0, -1))]
        neighbours = []
        for direction, (dx, dy) in delta:
            x2, y2 = cell.x + dx, cell.y + dy
            if (0 <= x2 < self.nx) and (0 <= y2 < self.ny):
                neighbour = self.cell_at(x2, y2)
                if neighbour.has_all_walls():
                    neighbours.append((direction, neighbour))
        return neighbours


    def make_maze(self):
        # Total number of cells.
        n = self.nx * self.ny
        cell_stack = []
        current_cell = self.cell_at(self.ix, self.iy)
        # Total number of visited cells during maze construction.
        nv = 1

        while nv < n:
            neighbours = self.find_valid_neighbours(current_cell)
            if not neighbours:
                # We've reached a dead end: backtrack.
                current_cell = cell_stack.pop()
                continue
            direction, next_cell = random.choice(neighbours)
            current_cell.knock_down_wall(next_cell, direction)
            cell_stack.append(current_cell)
            current_cell = next_cell
            nv += 1

def start():
    global maze
    global mazeBuffer
    global ball
    global startTime
    startTime = time.time()
    display.set_pen(BLACK)
    display.clear()
    gc.collect()
    maze = Maze(20, 15, 0, 0)
    maze.make_maze()
    gc.collect()
    maze.write_svg(display)
    gc.collect()
    mazeBuffer = copyBuffer(buffer)
    gc.collect()
    print(maze)
    display.set_pen(GREEN)
    display.rectangle(2, 2, 12, 12)
    display.set_pen(BLUE)
    display.rectangle(306, 226, 12, 12)
    gc.collect()
    ball = Ball(display, buffer, WIDTH, HEIGHT, 8, 8, maze)
    gc.collect()

start()

while True:
    x, y, z = motion.acceleration
    x = round(x,2)
    y = round(y,2)
    z = round(z,2)
    
    vdd = 1.24 * (65535 / vref_adc.read_u16())
    vbat = ((vbat_adc.read_u16() / 65535) * 3 * vdd)
    if (vbat / vdd) * 100 < 90:
        display.set_pen(WHITE)
        display.text("LOW BATTERY {:.2f}V".format(vbat), 0, 0, 0, 2)
    ball.update(x, y, z)
    ball.draw()
    
    if ball.isEnd():
        display.set_pen(BLUE)
        display.rectangle(55, 100, 210, 34)
        display.set_pen(WHITE)
        second = time.time() - startTime
        display.text("END MAZE {:.0f}s".format(second), 60, 105, 210, 3)
        display.update()
        start()
    
    display.update()
    
    
    