import random
import copy
import sys
import time
from operator import attrgetter

#============================================================================
# get_arg() returns command line arguments.
#============================================================================
def get_arg(index, default=None):
	'''Returns the command-line argument, or the default if not provided'''
	return sys.argv[index] if len(sys.argv) > index else default


#============================================================================
# List of possible moves
# https://ruwix.com/online-puzzle-simulators/2x2x2-pocket-cube-simulator.php
#
# Each move permutes the tiles in the current state to produce the new state
#============================================================================

RULES = {
	"U" : [ 2,  0,  3,  1,   20, 21,  6,  7,    4,  5, 10, 11, 
	       12, 13, 14, 15,    8,  9, 18, 19,   16, 17, 22, 23],
	"U'": [ 1,  3,  0,  2,    8,  9,  6,  7,   16, 17, 10, 11, 
	       12, 13, 14, 15,   20, 21, 18, 19,    4,  5, 22, 23],
	"R":  [ 0,  9,  2, 11,    6,  4,  7,  5,    8, 13, 10, 15, 
	       12, 22, 14, 20,   16, 17, 18, 19,    3, 21,  1, 23],
	"R'": [ 0, 22,  2, 20,    5,  7,  4,  6,    8,  1, 10,  3, 
	       12, 9, 14, 11,    16, 17, 18, 19,   15, 21, 13, 23],
	"F":  [ 0,  1, 19, 17,    2,  5,  3,  7,   10,  8, 11,  9, 
	        6,  4, 14, 15,   16, 12, 18, 13,   20, 21, 22, 23],
	"F'": [ 0,  1,  4,  6,   13,  5, 12,  7,    9, 11,  8, 10, 
	       17, 19, 14, 15,   16,  3, 18,  2,   20, 21, 22, 23],
	"D":  [ 0,  1,  2,  3,    4,  5, 10, 11,    8,  9, 18, 19, 
	       14, 12, 15, 13,   16, 17, 22, 23,   20, 21,  6,  7],
	"D'": [ 0,  1,  2,  3,    4,  5, 22, 23,    8,  9,  6,  7, 
	       13, 15, 12, 14,   16, 17, 10, 11,   20, 21, 18, 19],
	"L":  [23,  1, 21,  3,    4,  5,  6,  7,    0,  9,  2, 11, 
	        8, 13, 10, 15,   18, 16, 19, 17,   20, 14, 22, 12],
	"L'": [ 8,  1, 10,  3,    4,  5,  6,  7,   12,  9, 14, 11, 
	       23, 13, 21, 15,   17, 19, 16, 18,   20,  2, 22,  0],
	"B":  [ 5,  7,  2,  3,    4, 15,  6, 14,    8,  9, 10, 11, 
	       12, 13, 16, 18,    1, 17,  0, 19,   22, 20, 23, 21],
	"B'": [18, 16,  2,  3,    4,  0,  6,  1,    8,  9, 10, 11, 
	       12, 13,  7,  5,   14, 17, 15, 19,   21, 23, 20, 22]
}


'''
sticker indices:

        0  1
        2  3
16 17   8  9   4  5  20 21
18 19  10 11   6  7  22 23
       12 13
       14 15

face colors:

    0
  4 2 1 5
    3

rules:
[ U , U', R , R', F , F', D , D', L , L', B , B']
'''


class Cube:


	def __init__(self, config="WWWW RRRR GGGG YYYY OOOO BBBB"):
			
		#============================================================================
		# tiles is a string without spaces in it that corresponds to config 
		#============================================================================
		self.config = config
		self.tiles = config.replace(" ","")
		
		self.depth = 0
		self.rule = ""
		self.parent = None
		self.heuristicval= 0

	def __str__(self):
		#============================================================================
		# separates tiles into chunks of size 4 and inserts a space between them
		# for readability
		#============================================================================
		chunks = [self.tiles[i:i+4] + " " for i in range(0, len(self.tiles), 4)]
		return "".join(chunks)


	def __eq__(self,state):
		return (self.tiles == state.tiles) or (self.config == state.config)

	
	def toGrid(self):
		#============================================================================
		# produces a string portraying the cube in flattened display form, i.e.,
		#
		#	   RW       
		#	   GG       
		#	BR WO YO GY 
		#	WW OO YG RR 
		#	   BB       
		#	   BY       
		#============================================================================

		def part(face,portion):
			#============================================================================
			# This routine converts the string corresponding to a single face to a 
			# 2x2 grid
			#    face is in [0..5] if it exists, -1 if not
			#    portion is either TOP (=0) or BOTTOM (=1)
			# Example:
			# If state.config is "RWGG YOYG WOOO BBBY BRWW GYRR". 
			#   part(0,TOP) is GW , part(0,BOTTOM) is WR, ...
			#   part(5,TOP) is BR , part(5,BOTTOM) is BB
			#============================================================================
		
			result = "   "
			if face >=0 :	
				offset = 4*face + 2*portion
				result = self.tiles[offset] + self.tiles[offset+1] + " "
			return result
			
		TOP = 0
		BOTTOM = 1
		
		str = ""
		for row in [TOP,BOTTOM]:
			str += part(-1,row) + part(0,row) + \
				part(-1,row) + part(-1,row) + "\n"
			
		for row in [TOP,BOTTOM]:
			str += part(4,row) + part(2,row) + \
				part(1,row) + part(5,row) + "\n"
		
		for row in [TOP,BOTTOM]:
			str += part(-1,row) + part(3,row) + \
				part(-1,row) + part(-1,row) + "\n"
			
		return str


	def applicableRules(self):
		return list( RULES.keys() )


	def applyRule(self, rule):
		#============================================================================
		# apply a rule to a state
		#============================================================================
		theRule = RULES[rule]
		forChange=0
		newConfig=""
		newState = copy.deepcopy(self)
		values=self.tiles.split(",")
		theState=[]
		#=======================================================================================================
		#Change the string to a List because apparently this wasn't done elsewhere and we need to do this...
		#=======================================================================================================
		for i in values:
			theState+=list(i)
		newTheState=copy.deepcopy(theState)
		for i in theRule:
			newTheState[i]=theState[theRule[i]]
		#========================================================================================================
		# Create a new Config again after applying the rule...
		#========================================================================================================
		for i in newTheState:
			forChange+=1
			newConfig+= i
			if forChange%4==0 and forChange%24!=0:
				newConfig+=" "
		#Change newState's config and tiles to be the newConfig
		newState.config=newConfig
		newState.tiles=newConfig.replace(" ","")
		newState.rule=rule
		return newState

	
	def goal(self):
		#========================================================================================================
		# Split up the config, check the blocks on each face
		#========================================================================================================
		checkGoalSplit=self.config.split(" ")
		for face in checkGoalSplit:
			if face[0]==face[1]==face[2]==face[3]:
				continue
			else:
				return False
		return True

def changetoNum(n):
	if n=='W':
		return 0
	elif n=='R':
		return 1
	elif n=='G':
		return 2
	elif n=='Y':
		return 3
	elif n=='O':
		return 4
	else:
		return 5
def manhattan(a,b):
	return sum(abs(val1-val2) for val1, val2 in zip(a,b))
#========================================================================
#THIS IS NOT MANHATTAN DISTANCE, IT'S A MIX OF IT AND DISTANCE USING THE MANHATTAN FORMULA I'M PRETTY SURE IT'S NOT ADMISSIBLE? THE TRUE ADMISSIBLE FUNCTIONS FOR RUBIK'S CUBES REQUIRE GRADUATE LEVEL KNOWLEDGE AFAIK
# THIS REALLY ONLY WORKS QUICKLY FOR SMALLER SOLUTION PATHS, ASSUMING 10 OR LESS AS I CAN'T GET SOME OF THESE TO FINISH AND IDK THE SOLUTION PATH LENGTH
#========================================================================
def retryManhattan(state):
	if state.goal():
		return 0
	goal=[0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5]
	faces=state.config.split(" ")
	cubes=[]
	for cube in faces:
		cubes+=list(cube)
	cubes = map(changetoNum, cubes)
	return manhattan(goal, cubes)/16

	
#--------------------------------------------------------------------------------
#  GRAPH SEARCH
#--------------------------------------------------------------------------------
numNodesGen=0
numNodesExpanded=0
graphStart=0
graphEnd=0
def GraphSearch(start, isVerbose):
	global numNodesGen,numNodesExpanded,graphStart,graphEnd
	graphStart= time.time()
	OPEN = [ start ]
	CLOSED = []
	while OPEN !=[]:
		s = OPEN[0]
		numNodesExpanded+=1
		s.heuristicVal=retryManhattan(s)
		if(isVerbose):
			print(" Chosen Rule Change: " + s.rule + " State reached from that rule: " + str(s) + " Heuristical value of that state: " + str(s.heuristicVal))
		OPEN.pop(0)
		CLOSED.append(s)
		if s.goal():
			graphEnd=time.time()
			break
		for r in s.applicableRules():
			sp=s.applyRule(r)
			if not(sp in OPEN or sp in CLOSED):
				numNodesGen+=1
				sp.heuristicVal=retryManhattan(sp)
				sp.parent=s
				sp.depth=s.depth+1
				OPEN.append(sp)
				OPEN.sort(key=lambda x: (x.heuristicVal+x.depth))
			elif sp in OPEN:
				sp.parent = min(s, sp.parent, key=attrgetter('depth'))
				sp.depth = sp.parent.depth+1
			elif sp in CLOSED:
				sp.parent= min(s, sp.parent, key=attrgetter('depth'))
				sp.depth = sp.parent.depth+1
				for aState in OPEN:
					if not(aState.parent is None) and aState.parent==sp:
						aState.depth=aState.parent.depth+1
				for aState in CLOSED:
					if not (aState.parent is None) and aState.parent==sp:
						aState.depth=aState.parent.depth+1
	if s.goal():
		path=[]
		path.append(s)
		while path[0]!=start:
			path.insert(0,path[0].parent)
	return path

backCalls=0
fails=0
backTrackEnd=0
def backTrack (stateList, isVerbose, depthBound):
	state = stateList[0]
	global fails,backCalls,backTrackEnd
    #Check if member of statelist is duplicate
	for i in range(1, len(stateList)):
		if(stateList[i]==state):
			if isVerbose:
				print("This state has already been reached before.")
			return 'Failed-1'
	if state.goal():
		backTrackEnd=time.time()
		return 'NULL'
	if(depthBound<=0):
		if isVerbose:
			print("Reached the maximum depth.")
		return 'Failed-3'
    
	ruleSet = state.applicableRules()
	if (ruleSet=='NULL'):
		if isVerbose:
			print("The ruleSet has a NULL value.")
		return 'Failed-4'
    
	for rule in ruleSet:
		newState = state.applyRule(rule)
		if(isVerbose):
			print("Currently trying rule: " + str(rule))
			print("The state reached from that rule is:\n" + str(newState))
		newStateList = copy.deepcopy(stateList)
		newStateList.insert(0, newState)
		backCalls+=1
		path=backTrack(newStateList, isVerbose, depthBound-1)
		if path!= 'Failed-1' and path!= 'Failed-2' and path!= 'Failed-3' and path!= 'Failed-4' and path!='Failed-5':
			return path + str(newState.tiles + " " + rule + " ")
		fails+=1
	return 'Failed-5'
numDepthsTried=0
def iDBackTrack(stateList, isVerbose, maxDepth):
	global numDepthsTried
	result=""
	for i in range(maxDepth):
		numDepthsTried+=1
		result=backTrack(stateList, isVerbose, i)
		if result[0:4]=='NULL':
			return result
	return iDBackTrack(stateList, isVerbose, maxDepth+1)

			
#--------------------------------------------------------------------------------
#  MAIN PROGRAM
#--------------------------------------------------------------------------------

if __name__ == '__main__':
	
	#============================================================================
	# Read input from command line:
	#   python3 <this program>.py STATE VERBOSE
	# where
	# STATE is a string prescribing an initial state 
	#  (if empty, generate a problem to solve by applying a sequence of random 
	#   rules to the default state.)
	# VERBOSE specifies to enter VERBOSE mode for detailed algorithm tracing. 
	#============================================================================
	CONFIG = get_arg(1)

	VERBOSE = get_arg(2)	
	VERBOSE = (VERBOSE == "verbose" or VERBOSE == "v")		
	if VERBOSE:
		print("Verbose mode:")

	random.seed() # use clock to randomize RNG


	#============================================================================
	# Print list of all rules.
	#============================================================================
	print("All Rules:\n_________")
	for m in RULES.keys():
		print("  " + str(m) + ": " + str(RULES[m]))

	#============================================================================
	# Test case: default state is a goal state
	#============================================================================
	#state = Cube()
	#if state.goal():
	#	print("SOLVED!")
	#else:
	#	print("NOT SOLVED.")

	#============================================================================
	# Test case: This state is one move from a goal.  
	# Applying the "R" rule should solve the puzzle.
	#============================================================================
	#state = Cube("GRGR YYYY OGOG BOBO WWWW BRBR")
	#print(state.toGrid())
	#newState = state.applyRule("R")

	#print(newState.toGrid())
	#if newState.goal():
	#	print("SOLVED!")
	#else:
	#	print("NOT SOLVED.")
	graphState = copy.deepcopy(Cube(CONFIG))
	
	result=GraphSearch(graphState,VERBOSE)
	print("==============================\nGRAPH SEARCH\n=============================\nResulting solution tree:")
	for cube in result:
		if(cube==result[0]):
			print("Starting config: " + str(cube.config))
		else:
			print("Rule applied: " + str(cube.rule) + "\nResulting config: " + str(cube.config))
	print("Number of nodes Generated: " + str(numNodesGen) + " Number of nodes Expanded: " + str(numNodesExpanded) + "\nTime To complete: " + str(graphEnd-graphStart) + "\n")
	#==================================================
	#TEST BACKTRACKING
	#==================================================
	#state =  Cube("BRGG OBRY WWGY RBGO WROY WOBY")
	#state = Cube("BRGG OBRY WWGY RBGO WROY WOBY")
	backState = copy.deepcopy(Cube(CONFIG))
	initialStateList=[backState]
	maxDepth=1
	backTrackStart=time.time()
	results=iDBackTrack(initialStateList, VERBOSE, maxDepth)
	print("==============================\nITERATIVE DEEPENING BACK TRACK\n=============================\n")
	if results == 'Failed-5':
		print("Backtrack did not complete successfully")
	else:
		theResults=results[4:]
		theResults=theResults[::-1]
		splitResults=theResults.split(" ")
		splitResults=splitResults[1::]
		count=0
		print("\nStarting State: "+ str(backState))
		for i in splitResults:
			if count%2==1:
				print("Resulting State: " + i)
			else:
				print("\nRule Applied: " + i)
			count+=1
		print("Number of fails: " + str(fails) + "\nNumber of backtracks: " + str(backCalls) + "\nNumber of Depths tried: " + str(numDepthsTried) + "\nTime To Complete: " + str(backTrackEnd-backTrackStart))
