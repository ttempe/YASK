#Copyright Thomas TEMPE, 2022, DWTFYL license
import sys, time
from machine import Pin

#Config:
FirstUpChordSend = True
AutoRepeat = False
#TODO: add auto-repete on a specified list of strokes (or values + masks) (or any, on second press?)

### Extract from Plover code:
# In the Gemini PR protocol, each packet consists of exactly six bytes
# and the most significant bit (MSB) of every byte is used exclusively
# to indicate whether that byte is the first byte of the packet
# (MSB=1) or one of the remaining five bytes of the packet (MSB=0). As
# such, there are really only seven bits of steno data in each packet
# byte. This is why the STENO_KEY_CHART below is visually presented as
# six rows of seven elements instead of six rows of eight elements.

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

#__keymap = {"N/A":22, "S-":0, "T-":1, "K-":2, "P-":3, "W-":4, "H-":5, "R-":6, "A":7, "O":8, "*":9, "Num":10, "E":11, "U":12, "-F":18, "-R":19, "-P":20, "-B":21, "-L":22, "-G":26, "-T":27, "-S":28, "-D":29, "-Z":23}
#__protocole = [["N/A", "Num", "Num", "Num", "Num", "Num", "Num",],
#               ["S-", "S-", "T-", "K-", "P-", "W-", "H-"],
#               ["R-",  "A", "O-", "*", "*", "N/A", "N/A"],
#               ["N/A", "*", "*",  "E", "U", "-F", "-R"],
#               ["-P", "-B", "-L", "-G", "-T", "-S", "-D"],
#               ["Num", "Num", "Num", "Num", "Num", "Num", "-Z"]]


#List of GPIOs connected to chording keys
__inputs =     [0, 1,  2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 18, 19, 20, 21, 22, 26, 27, 28, 15, 14, 17] #GPIO address
#Corresponds to:S- T-  K- P- W- H- R- A  O  *  #    E   U  -F  -R  -P  -B  -L  -G  -T  -S  -D  -Z, N/A #key name
#Index          0  1   2  3  4  5  6  7  8  9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  #list index

#Here is the index (in __inputs) of the GPIO used for each of the bits of 6 bytes of one protocole frame
__protocole = [[ 23, 10, 10, 10, 10, 10, 10],
               [  0,  0,  1,  2,  3,  4,  5],
               [  6,  7,  8,  9,  9, 23, 23],
               [ 23,  9,  9, 11, 12, 13, 14],
               [ 15, 16, 17, 18, 19, 20, 21],
               [ 10, 10, 10, 10, 10, 10, 22]]

#Bitmaps
#                ~ZDSTGLBPRFUE#*OARHWPKTS
__left_hand  = 0b000000000000000111111111
__right_hand = 0b011111111111100000000000

# Autorepeat configuration: 
#                      key states                  mask: which keys to match?
#                        ZDSTGLBPRFUE#*OARHWPKTS    ZDSTGLBPRFUE#*OARHWPKTS
__autoRepeatRules = [ (0b00000000000000001010101, 0b11110000001111111111111),  #Ted's navigation: move cursor
                      (0b00000000000000001010101, 0b11110000001111111111111),  #Ted's navigation: move cursor
                      (0b00000000000000000101011, 0b11110000001111111111111),  #Ted's navigation: select
                    ]
__autoRepeatDelay = 700 #before 1st repeat
__autoRepeatRepeat= 300 #between subsequent repeats

__LED = Pin(25, Pin.OUT)

class YASK:    
    def __init__(self):
        self.keymap = {}
        self.inputs_max = 0 #Bitmap (order is same as __inputs) 
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
        sys.stdout.buffer.write(self.buffer)

    def loop(self):
        left, right, left_max, right_max = (0, 0, 0, 0) #bitmaps, like self.input_max
        already_written = False
        timeStamp = 0
        inputs = 0
        t0 = 0
        repeatingStarted = False
        autoRepeatEngaged = False
       
        while True:
            #polls in a loop
            inputs_old = inputs
            inputs = 0
            for i, v in enumerate(self.keys):
                inputs += (v()^1) << i
            self.inputs_max = inputs | self.inputs_max
            left  = inputs & __left_hand
            right = inputs & __right_hand
            left_max  = left  | left_max
            right_max = right | right_max

            if inputs_old != inputs:
                #A change in the keypresses
                t0 = time.ticks_ms()
                repeatingStarted = False
                autoRepeatEngaged = False
                if self.inputs_max >0: #pressed
                    if inputs == 0:
                        if already_written:
                            already_written = False
                        else:
                            __LED(1)
                            #print(bin(self.inputs_max))
                            self.write()
                        self.inputs_max = 0
                        left_max, right_max = (0, 0)
                    elif (( left == 0 and left_max > 0 and already_written != "R") or (right == 0 and right_max > 0 and already_written != "L")) and FirstUpChordSend: #only released the left or right hand
                        __LED(1)
                        self.write()
                        self.inputs_max = inputs
                        if left == 0:
                            left_max = 0
                            already_written = "L" if right else True
                        if right == 0:
                            right_max= 0
                            already_written = "R" if left else True
                if AutoRepeat and inputs != 0 and self.inputs_max == inputs:
                    for keys, mask in __autoRepeatRules:
                        if (inputs & mask) == (keys & mask): #satisfy at least one rule
                            autoRepeatEngaged = True
                            __LED(1);time.sleep_ms(100)
            elif autoRepeatEngaged:
                if repeatingStarted == False and time.ticks_ms()-t0 > __autoRepeatDelay:
                    self.write()
                    repeating = True
                    t0 = time.ticks_ms()
                elif repeatingStarted == True and time.ticks_ms()-t0 > __autoRepeatRepeat:
                    self.write()
                    t0 = time.ticks_ms()
            time.sleep_ms(20)#anti-rebound
            __LED(0)

c=YASK()
c.loop()
