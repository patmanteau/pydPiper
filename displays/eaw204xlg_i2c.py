#!/usr/bin/python
# coding: UTF-8

# Driver for EA W204-XLG LCD display on the RPi
# Written by: Ron Ritchey
# W204-XLG specifics contributed by Patrick Haas
# Derived from Lardconcepts
# https://gist.github.com/lardconcepts/4947360
# Which was also drived from Adafruit
# http://forums.adafruit.com/viewtopic.php?f=8&t=29207&start=15#p163445
#
# Useful references
# General overview of HD44780 style displays
# https://en.wikipedia.org/wiki/Hitachi_HD44780_LCD_controller
#
# EA W204-XLG spec sheet
# http://www.lcd-module.de/fileadmin/eng/pdf/doma/olede.pdf
#
# More detail on initialization and timing
# http://web.alfredstate.edu/weimandn/lcd/lcd_initialization/lcd_initialization_index.html
#

import time, math,logging
import lcd_display_driver
import fonts
from PIL import Image

import graphics
try:
	import smbus
except:
	logging.debug("smbus not installed")

class I2CDevice:
	def __init__(self, address, port=1):
		self.address = address
		self.bus = smbus.SMBus(port)

# Write four bits
	def write(self, cmd):
		self.bus.write_byte(self.address, cmd)
		time.sleep(0.0001)

class eaw204xlg_i2c(lcd_display_driver.lcd_display_driver):

	# commands
	LCD_CLEARDISPLAY = 0x01
	LCD_RETURNHOME = 0x02
	LCD_ENTRYMODESET = 0x04
	LCD_DISPLAYCONTROL = 0x08
	LCD_CURSORSHIFT = 0x10
	LCD_MODESET = 0x13
	LCD_FUNCTIONSET = 0x20
	LCD_SETCGRAMADDR = 0x40
	LCD_SETDDRAMADDR = 0x80

	# flags for display entry mode
	LCD_ENTRYRIGHT = 0x00
	LCD_ENTRYLEFT = 0x02
	LCD_ENTRYSHIFTINCREMENT = 0x01
	LCD_ENTRYSHIFTDECREMENT = 0x00

	# flags for display on/off control
	LCD_DISPLAYON = 0x04
	LCD_DISPLAYOFF = 0x00
	LCD_CURSORON = 0x02
	LCD_CURSOROFF = 0x00
	LCD_BLINKON = 0x01
	LCD_BLINKOFF = 0x00

	# flags for display/cursor shift
	LCD_DISPLAYMOVE = 0x08
	LCD_CURSORMOVE = 0x00
	LCD_MOVERIGHT = 0x04
	LCD_MOVELEFT = 0x00

	# flags for mode and power set
	LCD_GRAPHICMODE = 0x08
	LCD_CHARACTERMODE = 0x00
	LCD_POWERON = 0x04
	LCD_POWEROFF = 0x00

	# flags for function set
	LCD_8BITMODE = 0x10
	LCD_4BITMODE = 0x00
	LCD_2LINE = 0x08
	LCD_1LINE = 0x00
	LCD_5x10s = 0x04
	LCD_5x8DOTS = 0x00
	LCD_ENGJAP_FONT = 0x00
	LCD_EUR1_FONT = 0x01
	LCD_RUS_FONT = 0x02
	LCD_EUR2_FONT = 0x03

	En = 0x04
	Rw = 0x02
	Rs = 0x01


	character_translation = [
		  0,  1,  2,  3,  4,  5,  6,  7,255, -1, -1, -1, -1, -1, -1, -1,	#0
		 -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,	#16
		 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,	#32
		 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63,	#48
		 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79,	#64
		 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 97, 93, 94, 95,	#80
		 96, 97, 98, 99,100,101,102,103,104,105,106,107,108,109,110,111,	#96
		112,113,114,115,116,117,118,119,120,121,122, -1,124,125,126,127,	#112
		 -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,	#128
		 -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,	#144


		 32,234,236,237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,	#160
		223, -1, -1, -1, -1,228, -1,176, -1, -1, -1, -1, -1, -1, -1, -1,	#176
		 -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,	#192
		 -1, 78, -1, -1, -1, -1, -1,235, -1, -1, -1, -1, -1, -1, -1,226,	#208
		 -1, -1, -1, -1,225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,	#224
		 -1,238, -1, -1, -1, -1,239,253, -1, -1, -1, -1,245, -1, -1, -1 ]	#240

	
	def __init__(self, rows=16, cols=80, i2c_address=0x3f, i2c_port=1):
		# Check default arguments, they might not be appropriate for your build

		self.i2c_address = i2c_address
		self.i2c_port = i2c_port
		self.i2c = I2CDevice(i2c_address, i2c_port)
		
		self.rows = rows
		self.cols = cols
		self.rows_char = rows/8
		self.cols_char = cols/5
		self.curposition = (0,0)

		# image buffer to hold current display contents.  Used to prevent unnecessary refreshes
		self.curimage = Image.new("1", (self.cols, self.rows))

		self.FONTS_SUPPORTED = True

		# Initialize the default font
		self.font = fonts.bmfont.bmfont('latin1_5x8_fixed.fnt')
		self.fp = self.font.fontpkg

		# Sets the values to offset into DDRAM for different display lines
		# self.row_offsets = [ 0x00, 0x40, 0x14, 0x54 ]
		self.row_offsets = [0x80, 0xc0, 0x94, 0xd4]


		for i in range(1,5):
			self.writeonly4bits(0x00, False)

		self.delayMicroseconds(2)

		# Now place in 8 bit mode so that we start from a known state
		# issuing function set twice in case we are in 4 bit mode
		self.writeonly4bits(0x03, False)
		self.delayMicroseconds(2)
		self.writeonly4bits(0x03, False)
		self.delayMicroseconds(2)
		self.writeonly4bits(0x03, False)
		self.delayMicroseconds(2)

		# placing display in 4 bit mode
		self.writeonly4bits(0x02, False)
		self.delayMicroseconds(60)

		# From this point forward, we need to use write4bits function which
		# implements the two stage write that 4 bit mode requires

		# Function set for 4 bits, 2 lines, 5x8 font, Western European font table
		self.write4bits(self.LCD_FUNCTIONSET | self.LCD_2LINE | self.LCD_5x8DOTS | self.LCD_4BITMODE | self.LCD_EUR1_FONT)
		self.delayMicroseconds(60)
		
		# Turn off display
		self.write4bits(self.LCD_DISPLAYCONTROL | self.LCD_DISPLAYOFF | self.LCD_CURSOROFF | self.LCD_BLINKOFF)
		self.delayMicroseconds(60)

		# Entry Mode set to increment and no shift
		self.write4bits(self.LCD_ENTRYMODESET | self.LCD_ENTRYLEFT)
		self.delayMicroseconds(60)

		# Character mode and internel power on
		self.write4bits(self.LCD_MODESET | self.LCD_CHARACTERMODE | self.LCD_POWERON)
		self.delayMicroseconds(60)            
		
		# Clear display and reset cursor
		self.write4bits(self.LCD_CLEARDISPLAY)
		self.delayMicroseconds(4000)

		# return home
		self.write4bits(self.LCD_RETURNHOME) # set cursor position to zero
		self.delayMicroseconds(2000) # this command takes a long time!

		#self.write4bits(0x17, False) # Set to char mode and turn on power
		self.write4bits(self.LCD_DISPLAYCONTROL | self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF)
		self.delayMicroseconds(60)
		self.displaycontrol = self.LCD_DISPLAYON
		
		# Set up parent class.
		super(eaw204xlg_i2c, self).__init__(rows,cols)

	def writeonly4bits(self, bits, char_mode=False):

		self.i2c.write(bits)
		self.pulseEnable(bits)

	def write4bits(self, bits, char_mode=False):

		mode = self.Rs if char_mode else 0
		self.writeonly4bits(mode | (bits & 0xf0))
		self.writeonly4bits(mode | ((bits << 4) & 0xf0))

	def pulseEnable(self, bits):

		# the pulse timing in the 16x2_oled_volumio 2.py file is 1000/500
		# the pulse timing in the original version of this file is 10/10
		# with a 100 post time for setting

		self.i2c.write(bits | self.En)
		self.delayMicroseconds(5) # 1 microsecond pause - enable pulse must be > 450ns
		self.i2c.write(bits & ~self.En)
		self.delayMicroseconds(5) # 1 microsecond pause - enable pulse must be > 450ns
		#self.delayMicroseconds(10) # commands need > 37us to settle

	def createcustom(self, image):

		if self.currentcustom == 0:
			# initialize custom font memory
			self.customfontlookup = {}

		# The image should only be 5x8 but if larger, crop it
		img = image.crop( (0,0,5,8) )

		imgdata = list(img.convert("1").getdata())

		# Check to see if a custom character has already been created for this image
		if tuple(imgdata) in self.customfontlookup:
			return self.customfontlookup[tuple(imgdata)]

		# If there is space, create a custom character using the image provided
		if self.currentcustom > 7:
			return ord('?')

		# Set pointer to position char in CGRAM
		self.write4bits(self.LCD_SETCGRAMADDR+(self.currentcustom*8))

		# Increment currentcustom to point to the next custom char position
		self.currentcustom += 1


		# For each line of data from the image
		for j in range(8):
			line = 0
			# Computer a five bit value
			for i in range(5):
				if imgdata[j*5+i]:
					line |= 1<<4-i
			# And then send it to the custom character memory region for the current customer character
			self.write4bits(line, True)

		# Save custom character in lookup table
		self.customfontlookup[tuple(imgdata)] = self.currentcustom - 1

		# Return the custom character position.  We have to subtract one as we incremented it earlier in the function
		return self.currentcustom - 1

	def compare(self, image, position):
		imgdata = tuple(list(image.getdata()))
		disdata = tuple(list(self.curimage.crop((position[0], position[1], position[0]+5, position[1]+8)).getdata()))
		if imgdata == disdata:
			return True
		return False

	def update(self, image):

		# Make image the same size as the display
		img = image.crop( (0,0,self.cols, self.rows))

		# Make image black and white
		img = img.convert("1")


		# For each character sized cell from image, try to determine what character it is
		# by comparing it against the font reverse lookup dictionary
		# If you find a matching entry, output the cooresponding unicode value
		# else output a '?' symbol
		self.currentcustom = 0
		for j in range(self.rows_char):
			for i in range(self.cols_char):
				imgtest = img.crop( (i*5, j*8, (i+1)*5, (j+1)*8) )

				# Check to see if the img is the same as was previously updated
				# If it is, skip to the next character
#				if self.compare(imgtest, (i*5, j*5)):
#					continue
				imgdata = tuple(list(imgtest.getdata()))
				char = self.font.imglookup[imgdata] if imgdata in self.font.imglookup else self.createcustom(imgtest)
				#print "Using char {0}".format(char)
				#frame = graphics.getframe(imgtest,0,0,5,8)
				#graphics.show(frame,5,1)

				# Check to see if there is a character in the font table that matches.  If not, try to create a custom character for it.
				char = self.character_translation[char] if self.character_translation[char] >= 0 else self.createcustom(imgtest)

				# Write the resulting character value to the display
				self.setCursor(i,j)
				self.write4bits(char, True)

		# Save the current image to curimage
		self.curimage.paste(image.crop((0,0,self.cols,self.rows)),(0,0))
		self.setCursor(0,0)

		displaycontrol = self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF
		self.write4bits(self.LCD_DISPLAYCONTROL | displaycontrol, False)


	def clear(self):

		# Set cursor back to 0,0
		self.setCursor(0,0)
		self.curposition = (0,0)

		self.curimage = Image.new("1",(self.cols,self.rows))

		# And then clear the screen
		self.write4bits(self.LCD_CLEARDISPLAY) # command to clear display
		self.delayMicroseconds(2000) # 2000 microsecond sleep, clearing the display takes a long time

	def setCursor(self, col_char, row_char):

		if row_char > self.rows_char or col_char > self.cols_char:
			raise IndexError

		if (row_char > self.rows_char):
			row = self.rows_char - 1 # we count rows starting w/0

		self.write4bits(self.LCD_SETDDRAMADDR | (col_char + self.row_offsets[row_char]))

		self.curposition = (col_char, row_char)


	def loadcustomchars(self, char, fontdata):
		# Load custom characters

		# Verify that there is room in the display
		# Only 8 special characters allowed

		if len(fontdata) + char > 8:
			logging.debug("Can not load fontset at position {0}.  Not enough room left".format(char))
			raise IndexError

		# Set pointer to position char in CGRAM
		self.write4bits(self.LCD_SETCGRAMADDR+(char*8))

		# Need a short sleep for display to stablize
		time.sleep(.01)

		# For each font in fontdata
		for font in fontdata:
			for byte in font:
				self.write4bits(byte, True)

	def message(self, text, row_char=0, col_char=0):
		''' Send string to LCD. Newline wraps to second line'''

		if row_char > self.rows_char or col_char > self.cols_char:
			raise IndexError

		self.setCursor(col_char, row_char)

		for char in text:
			if char == '\n':
				row = self.curposition[1]+1 if self.curposition[1]+1 < self.rows_char else self.curposition[1]
				self.setCursor(0, row)
			else:
				# Translate incoming character into correct value for European charset
				# and then send it to display.  Use space if character is out of range.
				c = ord(char)
				if c > 255: c = 32
				ct = self.character_translation[c]
				if ct > 0:
					self.write4bits(self.character_translation[c], True)

	def cleanup(self):
		pass

	def msgtest(self, text, wait=1.5):
		self.clear()
		lcd.message(text)
		time.sleep(wait)

if __name__ == '__main__':

	import getopt,sys
	try:
		opts, args = getopt.getopt(sys.argv[1:],"hr:c:",["row=","col=","rs=","e=","d4=","d5=","d6=", "d7="])
	except getopt.GetoptError:
		print 'eaw204xlg_i2c.py -r <rows> -c <cols> --address <smbus_address>'
		sys.exit(2)

	# Set defaults
	# These are for the wiring used by a Raspdac V3
	rows = 16
	cols = 80
	address = 0x3f

	for opt, arg in opts:
		if opt == '-h':
			print 'eaw204xlg_i2c.py -r <rows> -c <cols> --address <smbus_address>'
			sys.exit()
		elif opt in ("-r", "--rows"):
			rows = int(arg)
		elif opt in ("-c", "--cols"):
			cols = int(arg)
		elif opt in ("--address"):
			address  = int(arg)

	try:

		print "EA W204-XLG I2C LCD Display Test"
		print "ROWS={0}, COLS={1}, ADDRESS={2}".format(rows,cols,hex(address))

		lcd = eaw204xlg_i2c(rows,cols,address)
		lcd.clear()

		lcd.message("EA W204-XLG LCD\nPi Powered")
		time.sleep(4)

		lcd.clear()

		time.sleep(2)


	except KeyboardInterrupt:
		pass

	finally:
		try:
			lcd.clear()
			lcd.message("Goodbye!")
			time.sleep(2)
			lcd.clear()
		except:
			pass
		time.sleep(.5)
		print u"LCD Display Test Complete"
