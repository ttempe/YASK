import sys, time
from machine import Pin
#Copyright 2022 Thomas TEMPE, DWTFYL license
#Do whatever you like with this code

### Excerpt from the Plover code:
# In the Gemini PR protocol, each packet consists of exactly six bytes
# and the most significant bit (MSB) of every byte is used exclusively
# to indicate whether that byte is the first byte of the packet
# (MSB=1) or one of the remaining five bytes of the packet (MSB=0). As
# such, there are really only seven bits of steno data in each packet
# byte. This is why the STENO_KEY_CHART below is visually presented as
# six rows of seven elements instead of six rows of eight elements.
#
# STENO_KEY_CHART = ("Fn", "#1", "#2", "#3", "#4", "#5", "#6",
#                    "S1-", "S2-", "T-", "K-", "P-", "W-", "H-",
#                    "R-", "A-", "O-", "*1", "*2", "res1", "res2",
#                    "pwr", "*3", "*4", "-E", "-U", "-F", "-R",
#                    "-P", "-B", "-L", "-G", "-T", "-S", "-D",
#                    "#7", "#8", "#9", "#A", "#B", "#C", "-Z")
# 
#      #1 #2  #3 #4 #5 #6 #7 #8 #9 #A #B #C
#      Fn S1- T- P- H- *1 *3 -F -P -L -T -D
#         S2- K- W- R- *2 *4 -R -B -G -S -Z
#               A- O-       -E -U

# Here is the YASK keymap, mapped on the Gemini protocole:
#              [["N/A", "Num", "Num", "Num", "Num", "Num", "Num",],
#               ["S-", "S-", "T-", "K-", "P-", "W-", "H-"],
#               ["R-",  "A", "O-", "*", "*", "N/A", "N/A"],
#               ["N/A", "*", "*",  "E", "U", "-F", "-R"],
#               ["-P", "-B", "-L", "-G", "-T", "-S", "-D"],
#               ["Num", "Num", "Num", "Num", "Num", "Num", "-Z"]]

#List of GPIOs connected to chording keys
__inputs =     [0, 1,  2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 18, 19, 20, 21, 22, 26, 27, 28, 29, 23, 17]
#Corresponds to:S- T-  K- P- W- H- R- A  O  *  #    E   U  -F  -R  -P  -B  -L  -G  -T  -S  -D  -Z, N/A
#Index          0  1   2  3  4  5  6  7  8  9  10  11  12  13  14  15  16  17  18  19  20  21  22  23

#Here is the index (in __inputs) of the GPIO used for each of the bits of 6 bytes of one protocole frame
__protocole = [[ 23, 10, 10, 10, 10, 10, 10],
               [  0,  0,  1,  2,  3,  4,  5],
               [  6,  7,  8,  9,  9, 23, 23],
               [ 23,  9,  9, 11, 12, 13, 14],
               [ 15, 16, 17, 18, 19, 20, 21],
               [ 10, 10, 10, 10, 10, 10, 22]]


class YACK:    
    def __init__(self):
        self.keymap = {}
        self.inputs_start = 0 	#Timestamp (for debouncing)
        self.inputs_max = 0 	#Bitmap (order is same as __inputs) 
        self.buffer = bytearray(6)
        self.keys = [] #List of Pin objects corresponding to __inputs
        for i in __inputs:
            self.keys.append(Pin(i, Pin.IN, Pin.PULL_UP)) 
        #print("Yet Another Chording Keyboard\nCopyright Thomas TEMPE 2022")
        
    def write(self):
        #Write stroke to USB
        for c in range(6):
            self.buffer[c] = 0
            for i, j in enumerate(__protocole[c]):
                self.buffer[c] += ((self.inputs_max>>__protocole[c][i])&0x01)<<(6-i)
        self.buffer[0] += 0x80
        sys.stdout.write(self.buffer)

    def loop(self):
        while True:
            inputs = 0
            for i, v in enumerate(self.keys):
                inputs += (v()^1) << i
            if self.inputs_max == 0 and inputs > 0: #First keypress of the stroke
                self.inputs_start = time.ticks_ms()
            self.inputs_max = inputs | self.inputs_max
            if inputs == 0 and self.inputs_max >0 and time.ticks_ms()-self.inputs_start>100: #stroke released and debounced
                self.write()
                self.inputs_max = 0
                time.sleep_ms(100)#Finish debouncing
            time.sleep_ms(1)
            #print(bin(inputs));time.sleep_ms(300)#Debug

c=YACK()
c.loop()
