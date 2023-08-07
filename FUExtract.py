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
	magicBytes = bytes(("\x00".join("FURBY")) + ("\x00" * 0x17), encoding='ascii') + bytearray([0x5C, 0xD5, 0xA6, 0xD0, 0x00, 0x00, 0x00, 0x00])
	headerLength = 0x28 # The length of the main header
	dlcFilename = bytes(("\x00".join("DLCCode.")) + "\x00", encoding='ascii') # DLC Prefix thingy
	initialSectionCounter = 0x0040cfb5 # Section counter increases by 0x1A for each section, must be converted back to little-endian before being written to file
	sectionEntryLength = 38 # The length of each "section entry" in the header
	
	unknownField = "???" # There are blank spaces for currently unknown field types
	
	headerFields = ["bin"]
	
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
			rawBytes.read(5) # Skip 2 byte padding (or just single utf-16 null char) and the subsequent 4 byte counter
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

			rawBytes += bytes("DLCCode." + field, encoding='utf-16')[2:] # Write "filename"
			rawBytes += bytes("\x00\x00", encoding='ascii') # Padding
			rawBytes += struct.pack('<I', fieldCounter) # Write internal counter stuff
			rawBytes += struct.pack('<I', fieldLengths[field]["length"]) # Write field length
			rawBytes += bytes("\x00\x00\x00\x00", encoding='ascii') # More padding

			fieldCounter += 0x1A

		#Once we've finished, we should make sure that the header length is exactly 0x288
		#(this seems to be important.)
		assert(len(rawBytes) == 0x288)

		return rawBytes

		

with open('../CDN Dump/fu001680.dlc', 'rb') as file:
	dlcHeader = DLC_Header()
	fileLengths = dlcHeader.extract(file)
	
	os.makedirs('./outputFiles/', exist_ok=True)
	for outFileName in list(fileLengths.keys()):
		file.seek(fileLengths[outFileName]["origin"])
		with open(os.path.join('./outputFiles/', 'DLC_0000.' + outFileName), 'wb') as outFile:
			outFile.write(file.read(fileLengths[outFileName]["length"]))