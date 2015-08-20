# This file is part of Code Cropper
# The tool has been designed and developed by Eng. Gervasio Calderon
# 
# Copyright (c) 2011, Core Security Technologies
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#  1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials
# provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE 
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
Helper functions and classes to parse source code, and discover "code regions".
A code region is a group of source lines that represent a programming concept
recognized by "Code Cropper".

The code regions currently recognized are: 

 * ANNOTATIONS: group of functions being annotated.
 * CODE_CROPPER: code added by the tool is sorrounded by marks, to make it easier to "unannotate".
 * FUNCTION: a programming function.
 * CLASS: a class.
'''
import os
import sys
import re
from base import AnnotationState
from call_graph import ProgramExecution

BEGIN_ANNOTATION = "#ifdef CODE_CROPPER_ANNOTATIONS\n"
END_ANNOTATION = "#endif //CODE_CROPPER_ANNOTATIONS\n"
BEGIN_CODE_CROPPER = "#ifdef CODE_CROPPER_ENABLED\n"
END_CODE_CROPPER = "#endif //CODE_CROPPER_ENABLED\n"
REGEX_ANY_CPP_CLASS = re.compile( r'(?P<declarationSpaces>\s*)(class|struct)\s*(?P<className>\w+)\s*' )
REGEX_ANY_PYTHON_CLASS = re.compile( r'(?P<declarationSpaces>\s*)class\s*(?P<className>\w+)\s*' )
REGEX_ANY_CPP_GLOBAL_FUNCTION= re.compile( r'(?P<declarationSpaces>\s*).*\s(?P<funcName>~*\w+)\s*\((?P<params>.*?)\)' )
REGEX_ANY_PYTHON_GLOBAL_FUNCTION= re.compile( r'(?P<declarationSpaces>\s*)def\s*(?P<funcName>\w+)\s*\((?P<params>.*?)\)' )
REGEX_CPP_FUNCTION_BEGIN = re.compile( "(?P<initSpaces>\s*){\s*" )
REGEX_CPP_CLASS_BEGIN = REGEX_CPP_FUNCTION_BEGIN
REGEX_PYTHON_FUNCTION_BEGIN = re.compile( r"(?P<initSpaces>\s*)[^\s]+.*" )
REGEX_PYTHON_CLASS_BEGIN = REGEX_PYTHON_FUNCTION_BEGIN

class CodeRegionType:
    '''
    Enum constants to classify "code regions", for instance: class, function, etc.
    '''
    VALID_CODE_REGIONS_COUNT = 4
    ANNOTATIONS, CODE_CROPPER, FUNCTION, CLASS = range(VALID_CODE_REGIONS_COUNT)
    

class CodeRegionIdentifier:
    '''
    It processes code regions. It identifies them, calculates their name, and discovers
    when the code enters the region and when it exits the latter.
    '''
    class CodeRegionEvents:
        '''
        Code region events.
        '''
        NONE, ENTER, EXIT = range(3)

    ##
    # @param self The CodeRegionIdentifier instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor.
        '''
        self.language_ = language
        
        #Volatile data: they change in calls to parseLine()
        self.line_ = None
        self.nextLine_ = None

    ##
    # @param self The CodeRegionIdentifier instance.
    # @param line The current source code line being processed.
    # @param nextLine The next code line (in Python, this affects the current line parsing, because it may indicate a code region enter or exit).
    def parseLine(self, line, nextLine):
        '''
        Parse a line ("spying" nextLine, if necessary).
        '''
        self.line_ = line
        self.nextLine_ = nextLine
        
        #Actual implementation
        self.parseLine_(line, nextLine)

    ##
    # @param self The CodeRegionIdentifier instance.
    # @return Whether or not this line enters in a code region.
    def enterCodeRegion(self):
        '''
        It tells whether or not this line enters in a code region. 
        '''
        return False

    ##
    # @param self The CodeRegionIdentifier instance.
    # @return Whether or not this line exits a code region.
    def exitCodeRegion(self):
        '''
        It tells whether or not this line exits a code region. 
        '''
        return False
    
    ##
    # @param self The CodeRegionIdentifier instance.
    # @return This region name.
    def getRegionName(self):
        '''
        Return this region name.
        '''
        return None

    ##
    # @param self The CodeRegionIdentifier instance.   
    def clearRegionStuff(self):
        '''
        Clear the current region information, to be prepared to discover the next.
        '''
        pass

    ##
    # @param self The CodeRegionIdentifier instance.
    # @param line The current source code line being processed.
    # @param nextLine The next code line (in Python, this affects the current line parsing, because it may indicate a code region enter or exit).
    def parseLine_(self, line, nextLine):
        '''
        Template method for the derivatives to implement line parsing.
        This parsing calculates the data for functions like "getRegionName()"
        to work properly.
        '''
        pass


class BetweenMacrosRegionIdentifier(CodeRegionIdentifier):
    '''
    Region identifier that discovers regions surrounded by macros, for instance:
    #ifdef CODE_CROPPER
    CODE REGION
    #endif //CODE_CROPPER
    '''
    ##
    # self The BetweenMacrosRegionIdentifier instance to construct.
    # @param language The program's programming language.
    # @param enterMacroLine Macro for entering the region.
    # @param exitMacroLine Macro for exiting the region.
    def __init__(self, language, enterMacroLine, exitMacroLine):
        '''
        Constructor.
        '''
        CodeRegionIdentifier.__init__(self, language)
        self.enterMacroLine_ = enterMacroLine
        self.exitMacroLine_ = exitMacroLine
    
    ##
    # @param self the BetweenMacrosRegionIdentifier instance.
    # @return Whether or not this line enters in a code region.
    def enterCodeRegion(self):
        '''
        It tells whether or not this line enters in a code region.
        '''
        return self.line_.find(self.enterMacroLine_) >= 0

    # @param self the BetweenMacrosRegionIdentifier instance.
    # @return Whether or not this line exits a code region.
    def exitCodeRegion(self):
        '''
        It tells whether or not this line exits in a code region.
        '''
        return self.line_.find(self.exitMacroLine_) >= 0
    
class AnnotationsIdentifier(BetweenMacrosRegionIdentifier):
    '''
    Region identifier that discovers annotations.
    '''
    ##
    # self The AnnotationsIdentifier instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor.
        '''
        BetweenMacrosRegionIdentifier.__init__(self, language, BEGIN_ANNOTATION, END_ANNOTATION)

class CodeCropperIdentifier(BetweenMacrosRegionIdentifier):
    '''
    Region identifier that discovers "Code Cropper" regions.
    '''
    ##
    # self The CodeCropperIdentifier instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor.
        '''
        BetweenMacrosRegionIdentifier.__init__(self, language, BEGIN_CODE_CROPPER, END_CODE_CROPPER)

class LanguageRegionMatcher:
    '''
    Base class region matcher, whose details by language are implemented by derivatives.
    '''
    ##
    # @param self The LanguageRegionMatcher instance to construct.
    # @param discoverRegionRegex Regex to discover the code region.
    # @param regionNameInRegex Regex to match the region name.
    # @param enterRegionRegex Regex to discover region entering.
    def __init__(self, discoverRegionRegex, regionNameInRegex, enterRegionRegex):
        '''
        Constructor.
        '''
        self.line_ = None
        self.nextLine_ = None
        self.discoverRegionRegex_ = discoverRegionRegex
        self.regionNameInRegex_ = regionNameInRegex
        self.enterRegionRegex_ = enterRegionRegex
        self.regionMatch_ = None
        self.regionName_ = None
        self.declarationSpaces_ = None
        self.initialSpaces_ = None

    ##
    # @param self The LanguageRegionMatcher instance.
    # @param line The current source code line being processed.
    # @param nextLine The next code line (in Python, this affects the current line parsing, because it may indicate a code region enter or exit).
    def parseLine(self, line, nextLine):
        '''
        This parsing calculates the data for functions like "getRegionName()"
        to work properly.
        '''
        self.line_ = line
        self.nextLine_ = nextLine
        self.parseLine_()

    ##
    # @param self The LanguageRegionMatcher instance.
    # @return This region name.
    def getRegionName(self):
        '''
        Return this region name.
        '''
        return self.regionName_

    ##
    # @param self The LanguageRegionMatcher instance.
    # @return Initial spaces to add in the line being processed.
    def getInitialSpaces(self):
        '''
        Get the initial spaces to add in the line being processed.
        '''
        return self.initialSpaces_

    ##
    # @param self The LanguageRegionMatcher instance.
    # @return: The declaration spaces (initial spaces at the line of code region entering).
    def getDeclarationSpaces(self):
        '''
        Get the "declaration spaces", i.e., the initial spaces in the line where the code region has been entered.
        '''
        return self.declarationSpaces_

    ##
    # @param self The LanguageRegionMatcher instance.
    def clearRegionStuff(self):
        '''
        Clear the current region information, to be prepared to discover the next.
        '''
        self.initialSpaces_ = None
        self.declarationSpaces_ = None
        self.regionName_ = None
        self.regionMatch_ = None
        self.matchingLine_ = None

    ##
    # @param self the LanguageRegionMatcher instance.
    # @return Whether or not this line enters in a code region.
    def enterCodeRegion(self):
        '''
        It tells whether or not this line enters in a code region. 
        '''
        if self.alreadyDiscoveredRegion():
            if not self.isInsideCodeRegion_(): 
                enterRegionMatch = self.enterRegionRegex_.match(self.line_)
                if enterRegionMatch:
                    self.initialSpaces_ = enterRegionMatch.group('initSpaces')
                    return True
                else:
                    return False
            else:
                return False
        else:
            self.discoveredCodeRegion()
            return False

    ##
    # @param self the LanguageRegionMatcher instance.
    # @return Whether or not this line discovers a code region.
    def discoveredCodeRegion(self):
        '''
        It tells whether or not this line discovers a code region.
        '''
        if not self.alreadyDiscoveredRegion():
            self.regionMatch_ = self.discoverRegionRegex_.match(self.line_)
            if self.regionMatch_:
                self.regionName_ = self.regionMatch_.group(self.regionNameInRegex_)
                self.declarationSpaces_ = self.regionMatch_.group('declarationSpaces')
                self.matchingLine_ = self.line_
                return True
            else:
                return False
        else:
            return False

    ##
    # @param self the LanguageRegionMatcher instance.
    # @return Whether or not a region has already been discovered.
    def alreadyDiscoveredRegion(self):
        '''
        It tells whether or not a region has already been discovered.
        '''
        return self.regionName_ is not None

    ##
    # @param self the LanguageRegionMatcher instance.
    # @return The region regex match (it may be None).
    def getRegionMatch(self):
        '''
        Get the region regex match (it may be None).
        '''
        return self.regionMatch_

    ##
    # @param self the LanguageRegionMatcher instance.
    # @return Whether or not the current lines are inside a region.
    def isInsideCodeRegion_(self):
        '''
        It tells whether or not the current lines are inside a region.
        '''
        return self.initialSpaces_ is not None
    
    # @param self the BetweenMacrosRegionIdentifier instance.
    # @return Whether or not this line exits a code region.
    def exitCodeRegion(self):
        '''
        It tells whether or not this line exits in a code region.
        It's implemented in the derivatives ('cause it depends on the language).
        '''
        raise NotImplementedError( "Should have implemented this" )

    ##
    # @param self The CodeRegionIdentifier instance.
    def parseLine_(self):
        '''
        Template method for the derivatives to implement line parsing.
        This parsing calculates the data for functions like "getRegionName()"
        to work properly.
        '''
        pass

    ##
    # @param self The CodeRegionIdentifier instance.
    def clearRegionStuff_(self):
        '''
        Template method for the derivatives to implement region cleaning.
        '''
        pass

class CppRegionMatcher(LanguageRegionMatcher):
    '''
    C++ region matcher.
    '''
    ##
    # @param self The CppRegionMatcher instance to construct.
    # @param discoverRegionRegex Regex to discover the code region.
    # @param regionNameInRegex Regex to match the region name.
    # @param enterRegionRegex Regex to discover region entering.
    def __init__(self, discoverRegionRegex, regionNameInRegex, enterRegionRegex):
        '''
        Constructor.
        '''
        LanguageRegionMatcher.__init__(self, discoverRegionRegex, regionNameInRegex, enterRegionRegex)
        self.bracketsCount_ = 0

    ##
    # @param self The CppRegionMatcher instance.
    # @return The function parameters list as a string.
    def getParams(self):
        '''
        Get the function parameters list as a string.
        '''
        regionMatch = self.getRegionMatch()
        assert regionMatch
        return regionMatch.group('params')

    ##
    # @param self The CppRegionMatcher instance.
    # @param funcName Function name.
    # @param className Name for the class that funcName belongs to.
    # @return The method type for this function.
    def getMethodTypeEnumForClass(self, funcName, className):
        '''
        Get the method type (method, static method, constructor or destructor)
        for a function, according to its parent class.
        '''
        methodTypeEnum = 'METHOD'
        if self.matchingLine_.strip().startswith('static'):
            methodTypeEnum = 'STATIC_METHOD'
        elif funcName == className:
            methodTypeEnum = 'CONSTRUCTOR'
        elif className and (funcName == '~' + className):
            methodTypeEnum = 'DESTRUCTOR'
        return methodTypeEnum

    ##
    # @param self The CppRegionMatcher instance.
    def clearRegionStuff_(self):
        '''
        Clear the current region information, to be prepared to discover the next.
        '''
        self.bracketsCount_ = 0

    ##
    # @param self The CppRegionMatcher instance.
    def parseLine_(self):
        '''
        Parse the current line, to later detect enter/exit events.
        '''
        if self.alreadyDiscoveredRegion():
            self.bracketsCount_ += self.countBrackets_()
   
    ##
    # @param self The CppRegionMatcher instance.
    # @return Whether or not this line exits a code region.
    def exitCodeRegion(self):
        '''
        It tells whether or not this line exits in a code region.
        '''
        return self.isInsideCodeRegion_() and self.bracketsCount_ == 0

    ##
    # @param self The CppRegionMatcher instance.
    # @return The difference between opened and closed brackets (for C++ code).
    def countBrackets_(self):
        '''
        Count the brackets, to discover C++ regions opening and closing.
        '''
        return self.line_.count("{") - self.line_.count("}")

##
# @param str A string.
# @return The string initial spaces
def initialSpaces(str):
    '''
    Return a string initial spaces.
    '''
    return str[: -len(str.lstrip())]

##
# @param line A source code line.
# @return Whether or not the line is empty (i.e.: it only has spaces).
def emptyLine( line ):
    '''
    Tell whether or not a line is empty (i.e.: it only has spaces).
    '''
    return re.compile( "^\s*$" ).match( line )

##
# @param self The CodeRegionIdentifier instance.
# @param line A source code line.
# @param initialSpaces Code region initial spaces at the moment of entering.
# @param lineSpaces Current line initial spaces.
# @return Whether or not this line exits a Python code region.
def exitPythonCodeRegion(line, initialSpaces, lineSpaces):
    '''
    It tells whether or not this line exits in a code region. 
    '''
    if line is None:
        return True
    if lineSpaces is None:
        return False
    return not emptyLine(line) and len(initialSpaces) >= len(lineSpaces)

class PythonRegionMatcher(LanguageRegionMatcher):
    '''
    Python region matcher
    '''
    ##
    # @param self The PythonRegionMatcher instance to construct.
    # @param discoverRegionRegex Regex to discover the code region.
    # @param regionNameInRegex Regex to match the region name.
    # @param enterRegionRegex Regex to discover region entering.
    def __init__(self, discoverRegionRegex, regionNameInRegex, enterRegionRegex):
        '''
        Constructor.
        '''
        LanguageRegionMatcher.__init__(self, discoverRegionRegex, regionNameInRegex, enterRegionRegex)
        self.nextLineSpaces_ = None

    ##
    # @param self The PythonRegionMatcher instance.
    # @return The function parameters list as a string.
    def getParams(self):
        '''
        Get the function parameters list as a string.
        '''
        regionMatch = self.getRegionMatch()
        assert regionMatch
        return regionMatch.group('params')

    #
    ##
    # @param self The PythonRegionMatcher instance.
    # @param funcName Function name.
    # @param className Name for the class that funcName belongs to.
    # @return The method type for this function.
    def getMethodTypeEnumForClass(self, funcName, className):
        '''
        Get the method type (method, static method, constructor or destructor)
        for a function, according to its parent class.
        NOTE: We assume the only parsing for Python is for main function.
        -> return a fixed value 'METHOD'.
        '''
        return 'METHOD'

    ##
    # @param self The PythonRegionMatcher instance.
    def clearRegionStuff_(self):
        '''
        Clear the current region information, to be prepared to discover the next.
        '''
        self.nextLineSpaces_ = None

    ##
    # @param self The PythonRegionMatcher instance.
    # @param line The current source code line being processed.
    # @param nextLine The next code line (in Python, this affects the current line parsing, because it may indicate a code region enter or exit).
    def parseLine(self, line, nextLine):
        '''
        Parse a line ("spying" nextLine, if necessary).
        '''
        self.line_ = line
        self.nextLine_ = nextLine
        self.nextLineSpaces_ = self.getInitialSpacesFromLine_(nextLine)

    ##
    # @param self The PythonRegionMatcher instance.
    # @return Whether or not this line exits a code region.
    def exitCodeRegion(self):
        '''
        It tells whether or not this line exits in a code region.
        '''
        return self.isInsideCodeRegion_() and exitPythonCodeRegion(self.nextLine_, self.declarationSpaces_, self.nextLineSpaces_)

    ##
    # @param self The PythonRegionMatcher instance.
    # @param line A source code line.
    # @return This line's initial spaces.
    def getInitialSpacesFromLine_(self, line):
        '''
        Get this line's initial spaces.
        '''
        if line:
            fb = self.enterRegionRegex_.match( line )
            if fb:
                return fb.group( 'initSpaces' )
            else:
                return None
        else:
            return None

##
# @param language The program's programming language.
# @param myCodeRegionType The code region type (see CodeRegionType).
# @return A LanguageRegionMatcher instance.
def createLanguageRegionMatcher(language, myCodeRegionType):
    '''
    Create the LanguageRegionMatcher, according to the combination of language and region code type.
    It's a double dispatch.
    '''
    LANG = ProgramExecution.Languages
    if language == LANG.C_PLUS_PLUS:
        if myCodeRegionType == CodeRegionType.FUNCTION:
            return CppRegionMatcher(REGEX_ANY_CPP_GLOBAL_FUNCTION, 'funcName', REGEX_CPP_FUNCTION_BEGIN)
        elif myCodeRegionType == CodeRegionType.CLASS:
            return CppRegionMatcher(REGEX_ANY_CPP_CLASS, 'className', REGEX_CPP_CLASS_BEGIN)
        assert not "CodeRegionType not allowed to use region matcher"
    else:
        assert language == LANG.PYTHON
        if myCodeRegionType == CodeRegionType.FUNCTION:
            return PythonRegionMatcher(REGEX_ANY_PYTHON_GLOBAL_FUNCTION, 'funcName', REGEX_PYTHON_FUNCTION_BEGIN)
        elif myCodeRegionType == CodeRegionType.CLASS:
            return PythonRegionMatcher(REGEX_ANY_PYTHON_CLASS, 'className', REGEX_PYTHON_CLASS_BEGIN)
        assert not "CodeRegionType not allowed to use region matcher"

#Proxy pattern
class ComplexRegionIdentifier(CodeRegionIdentifier):
    '''
    CodeRegionIdentifier for "complex" code regions, i.e.:
    not simple macros-related regions, but more complex regions, as functions or classes.
    '''
    ##
    # @param self The ComplexRegionIdentifier instance to construct.
    # @param language The program's programming language.
    # @param myCodeRegionType The code region type (see CodeRegionType).
    def __init__(self, language, myCodeRegionType):
        '''
        Constructor.
        '''
        CodeRegionIdentifier.__init__(self, language)
        self.languageRegionMatcher_ = createLanguageRegionMatcher(language, myCodeRegionType)

    ##
    # @param self The ComplexRegionIdentifier instance.
    # @param line The current source code line being processed.
    # @param nextLine The next code line (in Python, this affects the current line parsing, because it may indicate a code region enter or exit).
    def parseLine_(self, line, nextLine):
        '''
        Parse a line ("spying" nextLine, if necessary).
        '''
        self.languageRegionMatcher_.parseLine(line, nextLine)

    ##
    # @param self The ComplexRegionIdentifier instance.
    # @return Whether or not this line enters in a code region.
    def enterCodeRegion(self):
        '''
        It tells whether or not this line enters in a code region.
        '''
        return self.languageRegionMatcher_.enterCodeRegion()

    ##
    # @param self The ComplexRegionIdentifier instance.
    # @return Whether or not this line exits a code region.
    def exitCodeRegion(self):
        '''
        It tells whether or not this line exits a code region.
        '''
        return self.languageRegionMatcher_.exitCodeRegion()

    ##
    # @param self The ComplexRegionIdentifier instance.
    # @return This region name.
    def getRegionName(self):
        '''
        Get this region name.
        '''
        return self.languageRegionMatcher_.getRegionName()

    ##
    # @param self The ComplexRegionIdentifier instance.
    # @return Initial spaces to add in the line being processed.
    def getInitialSpaces(self):
        '''
        Get the initial spaces to add in the line being processed.
        '''
        return self.languageRegionMatcher_.getInitialSpaces()

    ##
    # @param self The ComplexRegionIdentifier instance.
    def clearRegionStuff(self):
        '''
        Clear the current region information, to be prepared to discover the next.
        '''
        return self.languageRegionMatcher_.clearRegionStuff()
    
class FunctionsIdentifier(ComplexRegionIdentifier):
    '''
    Code regions identifier specialized in functions.
    '''
    ##
    # @param self The FunctionsIdentifier instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor.
        '''
        ComplexRegionIdentifier.__init__(self, language, CodeRegionType.FUNCTION)

    ##
    # @param self The FunctionsIdentifier instance.
    # @return The function parameters list as a string.
    def getParams(self):
        '''
        Get the function parameters list as a string.
        '''
        return self.languageRegionMatcher_.getParams()
    
    ##
    # @param self The FunctionsIdentifier instance.
    # @param funcName Function name.
    # @param className Name for the class that funcName belongs to.
    # @return The method type for this function.
    def getMethodTypeEnumForClass(self, funcName, className):
        '''
        Get the method type (method, static method, constructor or destructor)
        for a function, according to its parent class.
        '''
        return self.languageRegionMatcher_.getMethodTypeEnumForClass(funcName, className)

class ClassesIdentifier(ComplexRegionIdentifier):
    '''
    Code regions identifier specialized in functions.
    '''
    ##
    # @param self The ClassesIdentifier instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor.
        '''
        ComplexRegionIdentifier.__init__(self, language, CodeRegionType.CLASS)

##
# @param myCodeRegionType The code region type (see CodeRegionType).
# @param language The program's programming language.
# @return A new CodeRegionIdentifier instance.
def createCodeRegionIdentifier(myCodeRegionType, language):
    '''
    Create the CodeRegionIdentifier, according to the combination of language and region code type.
    It's a double dispatch.
    '''
    if myCodeRegionType == CodeRegionType.ANNOTATIONS:
        return AnnotationsIdentifier(language)
    elif myCodeRegionType == CodeRegionType.CODE_CROPPER:
        return CodeCropperIdentifier(language)
    elif myCodeRegionType == CodeRegionType.FUNCTION:
        return FunctionsIdentifier(language)
    elif myCodeRegionType == CodeRegionType.CLASS:
        return ClassesIdentifier(language)
    assert not "Unrecognized codeRegionType"
    
class LanguageTokenizer:
    '''
    It parses source code and detects events for code regions.
    In parseLine(), it calculates all the events for all possible code regions.
    It's up to the calling code to use them.
    '''
    class LineEvents:
        '''
        Line Events constants
        '''
        ENTER_ANNOTATIONS, EXIT_ANNOTATIONS,\
        ENTER_CODE_CROPPER, EXIT_CODE_CROPPER,\
        ENTER_FUNCTION, EXIT_FUNCTION,\
        ENTER_CLASS, EXIT_CLASS = range(8)

    ##
    # @param self The LanguageTokenizer instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor
        '''
        self.language_ = language
        self.codeRegionIdentifiers_ = []
        for regionType in range(CodeRegionType.VALID_CODE_REGIONS_COUNT):
            self.codeRegionIdentifiers_.append(createCodeRegionIdentifier(regionType, language))

        #Events
        self.lineEvents_ = []

    ##
    # @param self The LanguageObject instance.
    # @return The object LanguageType.
    def getLanguage(self):
        '''
        Return the program's programming language.
        '''
        return self.language_


    ##
    # @param self The LanguageTokenizer instance.
    # @param line The current source code line being processed.
    # @param nextLine The next code line (in Python, this affects the current line parsing, because it may indicate a code region enter or exit).
    def parseLine(self, line, nextLine):
        '''
        Parse a line ("spying" nextLine, if necessary).
        Discover "Line Events" for all possible code regions, and return them
        in an internal events list, that may be obtained by getLineEvents().
        
        IMPORTANT: The events are appended to the list in a special order,
        that ensures the correct processing (for example, an "enter class" event
        must be processed before an "enter function", to detect that the function
        belongs to the class, and is not global).
        For Python processing, one line may fire more than one event.
        For instance: exit function and exit class, or enter function and enter CodeCropper.
        Enter and exit events are symmetrically appended in reverse order.
        '''
        ##
        # @param regionIdentifierIndex Index in the self.codeRegionIdentifiers_ list for this Code Region identifier. 
        # @param enterEvent Enter event to append, if the code has entered a code region.
        def addLineEnterEventsFromRegionIdentifier(regionIdentifierIndex, enterEvent):
            '''
            If the code has just entered a code region (use the correspondent Code Region identifier to detect it),
            add the "enter" event to the events list.
            '''
            if self.codeRegionIdentifiers_[regionIdentifierIndex].enterCodeRegion():
                self.lineEvents_.append(enterEvent)

        ##
        # @param regionIdentifierIndex Index in the self.codeRegionIdentifiers_ list for this Code Region identifier.
        # @param exitEvent Exit event to append, if the code has left a code region.
        def addLineExitEventsFromRegionIdentifier(regionIdentifierIndex, exitEvent):
            '''
            If the code has just exited a code region (use the correspondent Code Region identifier to detect it),
            add the "exit" event to the events list.
            '''
            if self.codeRegionIdentifiers_[regionIdentifierIndex].exitCodeRegion():
                self.lineEvents_.append(exitEvent)

        #These events are valid only for current line
        LE = LanguageTokenizer.LineEvents
        
        self.clearEvents_()
        
        for regionType in range(CodeRegionType.VALID_CODE_REGIONS_COUNT):
            self.codeRegionIdentifiers_[regionType].parseLine(line, nextLine)

        #Custom events
        #IMPORTANT: this order ensures that events are processed in order.
        #For Python processing, one line may fire more than one event
        #For instance: exit function and exit class
        #Or enter function and enter CodeCropper
        #Observe the reverse order of enter and exit events

        #Enter events
        addLineEnterEventsFromRegionIdentifier(CodeRegionType.CLASS, LE.ENTER_CLASS)
        addLineEnterEventsFromRegionIdentifier(CodeRegionType.FUNCTION, LE.ENTER_FUNCTION)
        addLineEnterEventsFromRegionIdentifier(CodeRegionType.CODE_CROPPER, LE.ENTER_CODE_CROPPER)
        addLineEnterEventsFromRegionIdentifier(CodeRegionType.ANNOTATIONS, LE.ENTER_ANNOTATIONS)
        #Exit events         
        addLineExitEventsFromRegionIdentifier(CodeRegionType.ANNOTATIONS, LE.EXIT_ANNOTATIONS)
        addLineExitEventsFromRegionIdentifier(CodeRegionType.CODE_CROPPER, LE.EXIT_CODE_CROPPER)
        addLineExitEventsFromRegionIdentifier(CodeRegionType.FUNCTION, LE.EXIT_FUNCTION)
        addLineExitEventsFromRegionIdentifier(CodeRegionType.CLASS, LE.EXIT_CLASS)        

    ##
    # @param self The LanguageTokenizer instance.
    def clearEvents_(self):
        '''
        Clear the internal line events list.
        This must be called at the beginning of parseLine(),
        because the events handling is by line.
        '''
        self.lineEvents_ = []

    ##
    # @param self The LanguageTokenizer instance.
    # @return The line events for current line.
    def getLineEvents(self):
        '''
        Return the line events for current line.
        '''
        return self.lineEvents_

    ##
    # @param self The LanguageTokenizer instance.
    # @return The current function initial spaces at the point of entering.
    def getFunctionInitialSpaces(self):
        '''
        Return the current function initial spaces at the point of entering.
        '''
        return self.codeRegionIdentifiers_[CodeRegionType.FUNCTION].getInitialSpaces()

    ##
    # @param self The LanguageTokenizer instance.
    # @return The current function name.
    def getFunctionName(self):
        '''
        Return the current function name.
        '''
        return self.codeRegionIdentifiers_[CodeRegionType.FUNCTION].getRegionName()
        
    ##
    # @param self The LanguageTokenizer instance.
    # @return The function parameters list as a string.
    def getParams(self):
        '''
        Get the function parameters list as a string.
        '''
        return self.codeRegionIdentifiers_[CodeRegionType.FUNCTION].getParams()

    ##
    # @param self The LanguageTokenizer instance.
    # @param functionName Function name.
    # @param className Name for the class that funcName belongs to.
    # @return The method type for this function.
    def getMethodTypeEnumForClass(self, functionName, className):
        '''
        Get the method type (method, static method, constructor or destructor)
        for a function, according to its parent class.
        '''
        return self.codeRegionIdentifiers_[CodeRegionType.FUNCTION].getMethodTypeEnumForClass(functionName, className)

    ##
    # @param self The LanguageTokenizer instance.
    # @return The current class name.
    def getClassName(self):
        '''
        Return the current class name.
        '''
        return self.codeRegionIdentifiers_[CodeRegionType.CLASS].getRegionName()
    
    #Clear functions
    
    ##
    # @param self The LanguageTokenizer instance.
    def clearAnnotationsStuff(self):
        '''
        Clear annotations-related data.
        '''
        self.codeRegionIdentifiers_[CodeRegionType.ANNOTATIONS].clearRegionStuff()

    ##
    # @param self The LanguageTokenizer instance.
    def clearCodeCropperStuff(self):
        '''
        Clear "Code Cropper"-related data.
        '''
        self.codeRegionIdentifiers_[CodeRegionType.CODE_CROPPER].clearRegionStuff()

    ##
    # @param self The LanguageTokenizer instance.
    def clearFunctionStuff(self):
        '''
        Clear function-related data.
        '''
        self.codeRegionIdentifiers_[CodeRegionType.FUNCTION].clearRegionStuff()

    ##
    # @param self The LanguageTokenizer instance.
    def clearClassStuff(self):
        '''
        Clear class-related data.
        '''
        self.codeRegionIdentifiers_[CodeRegionType.CLASS].clearRegionStuff()    
