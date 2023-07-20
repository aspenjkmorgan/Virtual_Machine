import re
import sys
input = sys.argv
filename1 = sys.argv[1]
outName = sys.argv[2]
if sys.argv[3] == 'True':
    needsInit = True
else:
    needsInit = False
filename2 = sys.argv[4]

if filename1.endswith(".vm") == False: raise Exception("Incorrect input file type.")
file1 = open(filename1, "r")

if filename2 != '' and filename2.endswith(".vm"): 
    file2 = open(filename2, "r")
else:
    file2 = ""

LABEL_NUMBER = 0
c = 0

def uniqueLabel():
    # Returns a unique label.
    global LABEL_NUMBER
    LABEL_NUMBER += 1
    return "LABEL_" + str(LABEL_NUMBER)


def getPushD():
     # This method takes no arguments and returns a string with assembly language
     # that will push the contents of the D register to the stack, referenced by
     # the stack pointer, SP.

     return "\n@SP \nA=M \nM=D \n@SP \nM=M+1 \n"

def getPopD():
    # This method takes no arguments and returns a string with assembly language
    # that will pop the stack to the D register.
    # SIDE EFFECT: The A register contains the SP
    
    # SP contains address of top of stack +1
    return "\n@SP \nA=M-1 \nD=M \n@SP \nM=M-1 \n"

# assume that a getPopD() is called before the assembly instructions
ARITH_BINARY = {
     'add': "\nA=M-1 \nM=M+D \n",
     'sub': "\nA=M-1 \nM=M-D \n",
     'and': "\nA=M-1 \nM=M&D \n",
     'or': "\nA=M-1 \nM=M|D \n"}

# apply operation to element at top of stack IN stack
ARITH_UNARY = {
     'neg': "\n@SP \nA=M-1 \nM=-M \n",
     'not': "\n@SP \nA=M-1 \nM=!M \n"}

ARITH_LOGIC = {
    'lt': "JLT",
    'eq': "JEQ",
    'gt': "JGT"}

def pointerSeg(push,seg,index):
    # The following puts the segment's pointer + index in the D
    # register, then achives its aim of either pushing RAM[seg+index]
    # to the stack or poping the stack to RAM[seg+index]. This will
    # work for ARG, LCL, THIS, and THAT segements
    # 
    # INPUTS:
    # push - a string that defines 'push' or 'pop' the operation occuring
    # seg - a string that specifies the segment being worked with, 
    # here it is LCL, ARG, THIS, or THAT
    # index - an integer that species the offset from the segment's base address
    # OUTPUTS:
    # a string of hack machine language instructions that performs push/pop seg index
    if push == "push":
        return ("\n@" + seg + "\nD=M \n@" + str(index) + "\nD=D+A \nA=D \nD=M" 
                + getPushD() + "\n")
    elif push == "pop":
        return ("\n@" + seg + "\nD=M \n@" + str(index) + "\nD=D+A \n@R13 \nM=D"
                + getPopD() + "\n@R13 \nA=M \nM=D \n")

def constantSeg(push,seg,index, f):
    # This function returns a sequence of machine language
    # instructions that places a constant value onto the
    # top of the stack. Note pop is undefined for this 
    # function if seg is 'constant'. However, this function
    # also addresses seg = 'static', for which pop is defined.
    # NOTE: For seg = 'static' the filename is needed. This can be a global 
    # or you can change the parameters to the function.

    # INPUTS:
    # push - a string that defines 'push' or 'pop' the operation occuring
    # seg - a string that specifies the segment being worked with, here 'constant' or 'static'
    # index - an integer that species the offset in general, but here is the literal value
    # OUTPUTS:
    # a string of hack machine language instructions that perform push/pop seg index
    # if push = 'push', seg = 'constant', and index = an integer
    # or if push = 'push' or 'pop', seg = 'static' and index = and integer
    if push == "push" and seg == "constant":
        return "\n@" + str(index) + "\nD=A" + getPushD()
    elif push == "push" and seg == "static":
        return "\n@" + f + "." + str(index) + "\nD=M" + getPushD()
    elif push == "pop" and seg == "static":
        return getPopD() + "\n@" + f + "." + str(index) + "\nM=D"


def fixedSeg(push,seg,index):
    # The following puts the segment's value + index in the D
    # register and then either pops from the stack to that address
    # or pushes from that address to the stack. Note that for fixed segments
    # the base address is 'fixed' as follows and is NOT a pointer:
    # pointer = 3
    # temp    = 5
    # INPUTS:
    # push - a string that defines 'push' or 'pop' the operation occuring
    # seg - a string that specifies the segment being worked with, 
    # here 'pointer' or 'temp'
    # index - an integer that species the offset from the segment's base address
    # OUTPUTS:
    # a string of hack machine language instructions that performs push/pop seg index
    x = 3
    if seg == "temp":
        x = 5
    
    if push == "push":
        return "\n@" + str(x) + "\nD=A \n@" + str(index) + "\nD=D+A \nA=D \nD=M" + getPushD()
    elif push == "pop":
        return ("\n@" + str(x) + "\nD=A \n@" + str(index) + "\nD=D+A \n@R13 \nM=D" + getPopD() +
                "\n@R13 \nA=M \nM=D \n")

def arithTest(type):
    # INPUT: type = one of 'lt','gt',or 'eq'
    # OUTPUT: a string of assembly that carries out the command
    # this can be helper function
    global c
    c+=1
    
    return (getPopD() + ARITH_BINARY["sub"] + "\n@T" + str(c) + 
                "\nD;" + ARITH_LOGIC[type] + "\n@F" + str(c) + "\nD=0;JMP \n(T" + str(c) +
                ") \nD=-1 \n(F" + str(c) + ") \n@SP \nA=M-1 \nM=D")

def getLabel(label):
    # Marks a label in assembly language, a labled line of code
    # specifically, (label)
    # INPUT: label - a string that provides a label to branch to
    # OUTPUT: a string that contains the assembly instructions
    return "\n(" + label + ")"

def getGoto(label):
    # Unconditional jump to the label provided
    # INPUT: label - a string that provides a label to branch to
    # OUTPUT: a string that contains the assembly instructions
    return "\n@" + label + "\n0;JMP"

def getIf_goto(label):
    # Return the machine language to branch (goto) if D
    # register does not equal zero. D should be made top of stack.
    # INPUT: label - a string that provides a label to branch to
    # OUTPUT: a string that contains the assembly instructions

    # after pop, D reg holds 0 for false or -1 for true
    return ("\n" + getPopD() +"\n@" + label + "\nD;JNE")

def _getPushMem(src):
    # INPUT: src - a text string that is a symbol corresponding to a RAM address containing an address
    # OUTPUT: a text string that will result in the address in src being pushed 
    # to the top of the stack. 
    return ("\n@" + src + "\nD=M" + getPushD())

def _getPushLabel(src):
    # INPUT: src - a text string that is some label, eg '(MAIN_LOOP)' which 
    # corresponds to a ROM address in the symbol table.
    # OUTPUT: a text string that will result in the ROM address 
    # to the top of the stack.
    return ("\n@" + src + "\nD=A" + getPushD())

def _getPopMem(dest):
    # INPUT: src - a text string that is a symbol that corresponding to a RAM address containing an address
    # OUTPUT: a text string that pops the stack and places that value into the dest segment pointer
    return ("\n" + getPopD() + "\n@" + dest + "\nA=M \nM=D")

def _getMoveMem(src,dest):
    # INPUT: src - a text string that is a symbol corresponding to a RAM address containing an address
    # INPUT: dest- a text string that is a symbol corresponding to a RAM address containing an address
    # OUPUT: a text string that copies the address in src to dest
    return ("\n@" + src + "\nD=M \n@" + dest + "\nM=D")

def getCall(functionName, nargs):
    # push retAddrLabel
    x = uniqueLabel()
    out = _getPushLabel(x)

    # push LCL, ARG, THIS and THAT
    out += _getPushMem("LCL") + _getPushMem("ARG") + _getPushMem("THIS") + _getPushMem("THAT")
    
    # ARG = SP - 5 - nArgs
    out += "\n@SP \nD=M \n@5 \nD=D-A \n@" + str(nargs) + "\nD=D-A \n@ARG \nM=D"
    # out += "\n@5" + "\nD=A" + "\n@" + str(nargs) + "\nD=D+A \n@SP \nA=M \nD=M-D \n@ARG \nM=D"
    
    # LCL = SP
    out += _getMoveMem("SP", "LCL")

    # goto functionName
    out += "\n@" + functionName + "\n0;JMP"
    # get goto 

    # (retAddrLabel)
    out += "\n(" + x + ")"
    # get label

    return out


def getFunction(functionName, nLocals):
    # (functionName)
    output = "\n(" + functionName + ")"

    # initialize local variables to 0
    output += "\nD=0"
    for i in nLocals:
        output += getPushD()
    
    return output

def getReturn():
    # endframe = LCL
    output = "\n@LCL \nD=M \n@R15 \nM=D"
    
    # retAddr = *(endframe - 5)
    output += "\n@5 \nD=D-A \nD=M \n@R14 \nM=D"
    
    # *ARG = pop()
    output += _getPopMem("ARG")
    
    # SP = ARG + 1
    output += "\n@1 \nD=A \n@ARG \nD=D+M \n@SP \nM=D"

    # THAT = *(endframe - 1) ... LCL = *(endframe - 4)
    output += "\n@1 \nD=A \n@R15 \nA=M-D \nD=M \n@THAT \nM=D"
    output += "\n@2 \nD=A \n@R15 \nA=M-D \nD=M \n@THIS \nM=D"
    output += "\n@3 \nD=A \n@R15 \nA=M-D \nD=M \n@ARG \nM=D"
    output += "\n@4 \nD=A \n@R15 \nA=M-D \nD=M \n@LCL \nM=D"

    # goto retAddr
    output += "\n@R14 \nA=M \n0;JMP"
    
    return output

def getInit(sysinit):
    if sysinit:
        os = ""
        os += '\n@256 \nD=A \n@SP \nM=D'
        os += '\nA=A+1 \nM=-1 \nA=A+1 \nM=-1 \nA=A+1 \nM=-1 \nA=A+1 \nM=-1'  # initialize ARG, LCL, THIS, THAT
        os += getCall('Sys.init', 0) # release control to init
        halt = uniqueLabel()
        os += '\n@%s \n(%s) \n0;JMP' % (halt, halt)
        return os
    else:
        return ""


def ParseFile(f, name):
    # INPUT: a filehandle, f
    # OUTPUT: a string of assembly commands that carry out
    # the vm instructions in the file f
     
    # create array to hold actual lines of code
    result = ""

    lines = []
    for line in f:
        x = line.split("//")[0].strip()
    
        if x.startswith("//") == False and len(x) != 0:
            lines.append(x)

    for line in lines:
        a = re.split(" ", line)
        
        if a[0] == "push" or a[0] == "pop":
            if a[1] == "local":
                result += pointerSeg(a[0], "LCL", a[2])
            elif a[1] == "argument":
                result += pointerSeg(a[0], "ARG", a[2])
            elif a[1] == "this":
                result += pointerSeg(a[0], "THIS", a[2])
            elif a[1] == "that":
                result += pointerSeg(a[0], "THAT", a[2])
            elif a[1] == "constant" or a[1] == "static":
                result +=constantSeg(a[0], a[1], a[2], name)
            else:
                result += fixedSeg(a[0], a[1], a[2])
        elif a[0] in ARITH_LOGIC:
            result += arithTest(a[0])
        elif a[0] in ARITH_UNARY:
            result += ARITH_UNARY[a[0]]
        elif a[0] in ARITH_BINARY :
            result += getPopD() + ARITH_BINARY[a[0]]
        elif a[0] == "if-goto":
            result += getIf_goto(a[1])
        elif a[0] == "goto":
            result+= getGoto(a[1])
        elif a[0] == "label":
            result += getLabel(a[1])
        elif a[0] == "function":
            result += getFunction(a[1], a[2])
        elif a[0] == "call":
            result += getCall(a[1], a[2])
        elif a[0] == "return":
            result += getReturn()
    
    return result

def main():
   combined = getInit(needsInit)

   part1 = ParseFile(file1, filename1)

   if file2 != '':
       part2 = (ParseFile(file2, filename2)) + "\n(INFINITE_LOOP) \n@INFINITE_LOOP \n0;JMP"
   else:
       part2 = "\n(INFINITE_LOOP) \n@INFINITE_LOOP \n0;JMP"

   combined += part1 + part2
   
   # write to .asm file
   sys.stdout = open(outName + '.asm','wt')
   
   print(combined)

if __name__ == "__main__":
    main()

