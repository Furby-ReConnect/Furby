from io import BufferedReader
import struct
import os

class FormatError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)


# Functions for extracting and compiling header information
class DLC_Header():
	# Set of bytes which identify a FURBY DLC file
	magicBytes = bytes(("\x00".join("FURBY")) + ("\x00" * 23) + ("\x78\x56\x34\x12\x02\x00\x08\x00"), encoding='ascii') # yes, ascii, reffer to micheal
	headerLength = 0x288 # The length of the main header
	dlcFilename = bytes(("\x00".join("DLC_0000.")) + "\x00", encoding='ascii') # DLC Prefix thingy
	initialSectionCounter = 0x0040cfb5 # Section counter increases by 0x1A for each section, must be converted back to little-endian before being written to file
	sectionEntryLength = 38 # The length of each "section entry" in the header
	
	unknownField = "???" # There are blank spaces for currently unknown field types
	
	headerFields = [unknownField, "PAL", "SPR", "CEL", "XLS", unknownField, unknownField, unknownField, unknownField, "AMF", "APL", "LPS", "SEQ", "MTR", unknownField, unknownField]
	unused_fields = ["FIR", "FIT", "CMR", "INT"] # Who knows LOL
	
	fieldLengths = {}

	def extract(self, rawBytes: BufferedReader): # Reads data from the header
		# Read magic bytes
		if (rawBytes.read(len(self.magicBytes)) != self.magicBytes):
			raise FormatError("Invalid DLC header")
		
		fieldCursor = self.headerLength # Field data starts immediately after the header

		# Read sections of header and get information
		for headerField in self.headerFields:
			#if (headerField == unknownField): # Skip field if unknown or blank
			#	rawBytes.read(sectionEntryLength)
			#	continue

			if (rawBytes.read(len(self.dlcFilename)) != self.dlcFilename):
				rawBytes.read(self.sectionEntryLength - len(self.dlcFilename))
				continue # Skip if blank section

			# Read actual field data
			fieldType = rawBytes.read(6).decode('utf-16') # PAL, SPR, etc
			rawBytes.read(6) # Skip 2 byte padding (or just single utf-16 null char) and the subsequent 4 byte counter
			fieldLength = struct.unpack("<I", rawBytes.read(4))[0] # The size of the section
			rawBytes.read(4) # Skip 4 byte padding

			self.fieldLengths[fieldType] = {
				"length": fieldLength, # The length of the field
				"origin": fieldCursor  # The start of the field's data
			}
			fieldCursor += fieldLength # Incremend field origin

		return self.fieldLengths
	
	def compile(self, fieldLengths):
		rawBytes = self.magicBytes # Get magic header stuff

		fieldCounter = self.initialSectionCounter
		for field in self.headerFields:
			if (field == self.unknownField or not field in fieldLengths.keys()):
				rawBytes += bytes('\x00' * self.sectionEntryLength, encoding='ascii') # Add empty section
				continue

			rawBytes += bytes("DLC_0000." + field, encoding='utf-16')[2:] # Write "filename"
			rawBytes += bytes("\x00\x00", encoding='ascii') # Padding
			rawBytes += struct.pack('<I', fieldCounter) # Write internal counter stuff
			rawBytes += struct.pack('<I', fieldLengths[field]["length"]) # Write field length
			rawBytes += bytes("\x00\x00\x00\x00", encoding='ascii') # More padding

			fieldCounter += 0x1A

		#Once we've finished, we should make sure that the header length is exactly 0x288
		#(this seems to be important.)
		assert(len(rawBytes) == 0x288)

		return rawBytes
			

###
# Palletes
###
# The "PAL" file consists of a series of Furby palletes
# Each pallete is a block of data with the size 0x80
# Every 2 bytes represents a colour in the pallete, with RGBA value
# The ALPHA channel can only be a 0 or 1
# Each pallete consists of 64 colours
class DLC_Pallete():
	palette_size = 0x80
	num_colours = 64

	def extract(self, rawbytes):
		self.palettes = []

		# Calculate number of palettes from palette size
		paletteCount,leftover = divmod(len(rawbytes.read()), self.palette_size)
		rawbytes.seek(0)
		assert(leftover == 0)
		
		for i in range(paletteCount):
			palette = []
			
			for j in range(self.num_colours): # Get all 64 colours in the palette
				single_colour = struct.unpack("<H", rawbytes.read(2))[0] # Colours are 16 bit

				# Get individual colour values
				# Wacky 16-bit RGBA nonsense
				R = ((single_colour & 0b0111110000000000) >> 7)
				G = ((single_colour & 0b0000001111100000) >> 2)
				B = ((single_colour & 0b0000000000011111) << 3)
				A = ((single_colour & 0b1000000000000000) >> 8)

				if A == 0:
					A = 0xff
				else:
					A = 0

				palette.append((R,G,B,A)) # Add colours to current palette
			
			assert(len(palette) == self.num_colours) # Make sure we have all 64 colours
			
			self.palettes.append(palette) # Add palette to final result
		return self.palettes
	
	def compile(self, palettes):
		rawbytes = bytes()

		for palette in palettes:
			assert(len(palette) == self.num_colours) # Make sure we have all 64 colours

			for colour in palette:
				#Unpack into 16-bit RGBA.
				R = (colour[0] & 0b11111000) << 7
				G = (colour[1] & 0b11111000) << 2
				B = (colour[2] & 0b11111000) >> 3
				A = 0b1000000000000000 if (colour[3] == 0) else 0

				colour = R+G+B+A # Ok, I don't really get how this works
				rawbytes += struct.pack("<H", colour)

		return rawbytes

		

with open('./dlc/dlc2/tu003410.dlc', 'rb') as file:
	dlcHeader = DLC_Header()
	fileLengths = dlcHeader.extract(file)
	
	os.makedirs('./outputFiles/', exist_ok=True)
	for outFileName in list(fileLengths.keys()):
		file.seek(fileLengths[outFileName]["origin"])
		with open(os.path.join('./outputFiles/', 'DLC_0000.' + outFileName), 'wb') as outFile:
			outFile.write(file.read(fileLengths[outFileName]["length"]))

	with open("./outputFiles/DLC_0000.PAL", 'rb') as file:
		palReader = DLC_Pallete()
		data = palReader.extract(file)
		print(data)