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
Parsing of C++ and Python sources, to add the code for annotations to take place,
and also to consult the functions and classes (to use in the GUI, for instance).
'''
from base import AnnotationState
from call_graph import ProgramExecution
import code_regions_parsing
import os
import re
import shutil
import sys

ANNOTATION_CLASS = 'code_cropper::Annotation'
ANNOTATION_VAR_NAME = r'codeCropperAnnotation'
ANNOTATOR_INSTANCE = 'code_cropper::Annotator::instance()'
DUMPER_VAR_NAME = 'codeCropperDumper'
PYTHON_ANNOTATOR_VAR_NAME = 'CODE_CROPPER_annotator'
ANNOTATE = 'annotate'
METHOD_TYPE_PREFIX = 'code_cropper::FunctionCall::MethodType::'
BUILTIN_MODULE = 'code_cropper::CPlusPlusConstants::BUILTINS_MODULE_NAME'

CPP_INCLUDE_ANNOTATION = "#include <code_cropper/code_cropper.h>\n"
PYTHON_INCLUDE_ANNOTATION = "from __future__ import with_statement\nimport code_cropper.annotator\n"
CPP_INDENTATION = "\t"
PYTHON_INDENTATION = ' ' * 4
BKP_EXTENSION = '.bkp'

##
#@param pythonImport Python import line for a module.
def getPythonImportLine(pythonImport):
    '''
    Get the Python import line for a module.
    '''
    return "import " + pythonImport + '\n'

##
def getPythonObjectAnnotationHead():
    '''
    Get the beginning of a Python annotation line.
    '''
    return PYTHON_ANNOTATOR_VAR_NAME + '.' + ANNOTATE + '('

##
# @param pythonObjectName Name of a Python object to annotate.
# @param pythonFunctionName Function name
def getPythonObjectAnnotationToInsert(pythonObjectName, pythonFunctionName = None):
    '''
    Get annotation for a Python object.
    '''
    pythonFunctionTail = '' if not pythonFunctionName else ", '" + pythonFunctionName + "'"
    return getPythonObjectAnnotationHead() + pythonObjectName + pythonFunctionTail + ')'  

##
# @param pythonObjectName Name of a Python object to annotate.
# @param itsAModule If true, Python object is a module.
# @return The very pythonObjectName if itsAModule is True, else the "module" prefix in pythonObjectName.
def getPythonImportFromObject(pythonObjectName, itsAModule):
    '''
    Returns the very pythonObjectName if itsAModule is True, else the "module" prefix in pythonObjectName.
    '''
    if itsAModule:
        return pythonObjectName
    else:
        dotIndex = pythonObjectName.rfind('.')
        return None if dotIndex == -1 else pythonObjectName[:dotIndex]


##
# @param f File where the annotation code is being inserted.
# @param initSpaces Initial spaces to add in the line before the mark.
def beginCodeCropper( f, initSpaces = "" ):
    '''
    Write "BEGIN_CODE_CROPPER" mark in a file.
    '''
    f.write( initSpaces + code_regions_parsing.BEGIN_CODE_CROPPER )

##
# @param f File where the annotation code is being inserted.
# @param initSpaces Initial spaces to add in the line before the mark.
def endCodeCropper( f, initSpaces = "" ):
    '''
    Write "END_CODE_CROPPER" mark in a file.
    '''    
    f.write( initSpaces + code_regions_parsing.END_CODE_CROPPER )

##
# @param f File where the annotation code is being inserted.
# @param initSpaces Initial spaces to add in the line before the mark.
def beginAnnotations( f, initSpaces = "" ):
    '''
    Write "BEGIN_ANNOTATIONS" mark in a file.
    '''  
    f.write( initSpaces + code_regions_parsing.BEGIN_ANNOTATION )

##
# @param f File where the annotation code is being inserted.
# @param initSpaces Initial spaces to add in the line before the mark.
def endAnnotations( f, initSpaces = "" ):
    '''
    Write "END_ANNOTATIONS" mark in a file.
    '''  
    f.write( initSpaces + code_regions_parsing.END_ANNOTATION )

##
# @param language The programming language.
# @return An "Include" annotation, depending on the language.
def getIncludeAnnotation(language):
    '''
    Return an "Include" annotation, depending on the language.
    '''
    LANG = ProgramExecution.Languages
    assert language in [LANG.C_PLUS_PLUS, LANG.PYTHON]
    return CPP_INCLUDE_ANNOTATION if language == LANG.C_PLUS_PLUS else PYTHON_INCLUDE_ANNOTATION

##
# @param line Line to check
# @return True if "line" is empty, False otherwise.
def emptyLine( line ):
    '''
    Tell whether or not a line is empty. 
    '''
    return re.compile( "^\s*$" ).match( line )

##
# @param str A source code line.
# @return The difference between opened and closed brackets (for C++ code).
def countBrackets( str ):
    '''
    Count the brackets, to discover C++ regions opening and closing.
    '''
    return str.count("{") - str.count("}")

##
# @param typeName A C++ type ("int" or "const MyClass&", for example).
# @return The type name with the qualifiers stripped.
def stripQualifiersFromTypeName(typeName):
    '''
    Remove const, pointer or reference qualifiers for C++ variables.
    '''
    constPattern = "const "
    if typeName.startswith(constPattern):
        typeName = typeName[len(constPattern):]
    if typeName.endswith("*") or typeName.endswith("&"):
        typeName = typeName[:-1]
    return typeName

##
# @param params Arguments list to normalize, for instance: "  int  i,[TABULATOR]char  j"
def normalizeParamsSpaces(params):
    '''
    Normalize spaces in parameters a parameters list, replacing tabs by spaces,
    and removing useless spaces as well. 
    '''
    #Leave only allowed spaces: to separate const 
    params = params.strip()
    #Replace tabs by spaces
    params = params.replace('\t', ' ')
    splitted = params.split(' ')
    newParams = ''
    mayAcceptSpace = True
    for token in splitted:
        if token:
            newParams += token + ' '
    #Strip last space
    newParams.strip() 
    newParams = newParams.replace(' ,', ',')
    newParams = newParams.replace(', ', ',')
    newParams = newParams.replace(' *', '*')
    newParams = newParams.replace(' &', '&')
    newParams = newParams.replace(' >', '>')
    newParams = newParams.replace('< ', '<')
    newParams = newParams.replace(' <', '<')
    return newParams

##
# @param fileName A raw file name to be normalized.
def asCppPathString(fileName):
    '''
    Normalize a path to be recognized as a C++ format, for instance: "C:\\Temp\\MyFile.txt"
    '''
    fileName = fileName.replace("\\", "\\\\")
    fileName = fileName.replace("/", "\\\\")
    return fileName

##
# @param str A C++ string that may have unescaped quotes.
def escapeCppStringQuotes(str):
    '''
    Escape a C++ string quotes, i.e.: add a '\' prefix to quotes. 
    '''
    return str.replace('"', '\\"')

##
# @param classNames A class names container.
def isOneClass(classNames):
    '''
    Return whether or not classNames container has only one class element.
    '''
    return classNames and len(classNames) == 1

class FunctionAnnotator:
    '''
    Interface for action classes that annotate the functions.
    '''
    ##
    # @param self The FunctionAnnotator instance.
    # @param line A source code line to process.
    # @param initSpaces Initial spaces to add to the line.
    # @param resultFile Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param functionName Function name.
    # @param params Arguments list.
    # @param methodTypeEnum Method type. 
    # @param className Class name.
    def annotateFunctionBeginning(self, line, initSpaces, resultFile, headerToInclude, functionName, params, methodTypeEnum, className):
        '''
        Annotation code to be inserted at the beginning of the function.
        '''
        pass

    ##
    # @param self The FunctionAnnotator instance
    # @param resultFile Result file to add the modified lines.
    # @param initSpaces Initial spaces to add to the line.
    def annotateFunctionEnding(self, resultFile, initSpaces):
        '''
        Annotation code to be inserted at the end of the function.
        '''
        pass

class CppRegularFunctionAnnotator(FunctionAnnotator):
    '''
    Annotates C++ functions.
    '''
    ##
    # @param self The FunctionAnnotator instance.
    # @param line A source code line to process.
    # @param initSpaces Initial spaces to add to the line.
    # @param resultFile Result file to add the modified lines.
    # @param headerToInclude Header to include
    # @param functionName Function name.
    # @param params Arguments list
    # @param methodTypeEnum Method type 
    # @param className Class name    
    def annotateFunctionBeginning(self, line, initSpaces, resultFile, headerToInclude, functionName, params, methodTypeEnum, className):
        '''
        Annotation code to be inserted at the beginning of the function.
        '''
        regexParam = re.compile( '\s*(?P<typeName>.+)\s+(?P<paramName>\w+)\s*' )
        bracketsCount = 1
        # ANNOTATE
        beginCodeCropper(resultFile, initSpaces)
        declaration = ANNOTATION_CLASS + ' ' + ANNOTATION_VAR_NAME + ';'
        resultFile.write(initSpaces + "\t" + declaration + '\n' )
        classStr = "" if not className else ', "' + className + '"'
        #For static methods, there's no "this" pointer 
        if className and methodTypeEnum != 'STATIC_METHOD':
            classStr += ', this'
        functionCall = ANNOTATOR_INSTANCE + '.addFunctionInfo("' + functionName + '", ' + METHOD_TYPE_PREFIX + methodTypeEnum + ', "' + escapeCppStringQuotes(headerToInclude) + '"' + classStr + ');'
        resultFile.write(initSpaces + "\t" + functionCall + '\n' )
        if not emptyLine( params ):
            params = normalizeParamsSpaces(params)
            mapPrefix = ''
            paramsList = params.split( "," )
            for param in paramsList:
                #Special case: protect map against split
                if mapPrefix:
                    param = mapPrefix + ',' + param
                    mapPrefix = ''
                else:
                    #No const
                    pureParam = stripQualifiersFromTypeName(param)
                    if pureParam.startswith('std::map<') or pureParam.startswith('map<'):
                        mapPrefix = param
                        continue
                mParam = regexParam.match( param )
                if mParam:
                    typeName = mParam.group( 'typeName' )
                    paramName = mParam.group( 'paramName' )
                else:
                    raise( Exception, r'Unrecognized parameter: ' + param )
                #Calculate module
                pureTypeName = stripQualifiersFromTypeName(typeName)
                if pureTypeName in ["int", "unsigned int", "float", "double", "void", "bool"]:
                    moduleName = BUILTIN_MODULE
                else:
                    if pureTypeName.startswith("vector<") or pureTypeName.startswith("std::vector<"):
                        moduleName = "<vector>"
                    elif pureTypeName in ["string", "std::string"]:
                        moduleName = "<string>"
                    elif pureTypeName.startswith("list<") or pureTypeName.startswith("std::list<"):
                        moduleName = "<list>"
                    elif pureTypeName.startswith("map<") or pureTypeName.startswith("std::map<"):
                        moduleName = "<map>"
                    else:
                        #Assume it's the same file
                        moduleName = headerToInclude
                    moduleName = '"' + moduleName + '"'
                strParam = ANNOTATOR_INSTANCE + '.addArgument(' + moduleName + ', "' + typeName + '", ' + paramName + ');'
                resultFile.write(initSpaces + "\t" + strParam + '\n' )
        resultFile.write(initSpaces + "\t" + ANNOTATOR_INSTANCE + '.endFunctionCallAnnotation();\n')
        endCodeCropper( resultFile, initSpaces )

class MainFileAnnotator(FunctionAnnotator):
    '''
    Annotator for the program's main file.
    '''
    ##
    # @param self The MainFileAnnotator instance to construct.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param dumpFileName File where the call graph database will be dumped.
    def __init__(self, doAdd, dumpFileName):
        '''
        Constructor.
        '''
        self.doAdd_ = doAdd
        self.dumpFileName_ = dumpFileName 

    ##
    # @param self The FunctionAnnotator instance.
    # @param line A source code line to process.
    # @param initSpaces Initial spaces to add to the line.
    # @param resultFile Result file to add the modified lines.
    # @param headerToInclude Header to include
    # @param functionName Function name.
    # @param params Arguments list
    # @param methodTypeEnum Method type.
    # @param className Class name    
    def annotateFunctionBeginning(self, line, initSpaces, resultFile, headerToInclude, functionName, params, methodTypeEnum, className):
        '''
        Annotation code to be inserted at the beginning of the function.
        '''
        beginCodeCropper(resultFile, initSpaces)
        self.insertDumpFileCode_(resultFile, initSpaces)
        endCodeCropper(resultFile, initSpaces)

    ##
    # @param self The FunctionAnnotator instance.
    # @param resultFile Result file to add the modified lines.
    # @param initSpaces Initial spaces to add to the line.
    def insertDumpFileCode_(self, resultFile, initSpaces):
        '''
        Insert in the resultFile a line to dump the call graph into a Json database.
        Abstract function, implement it in the derivatives, according to the language.
        '''
        raise NotImplementedError( "Should have implemented this" )

class CppMainFileAnnotator(MainFileAnnotator):
    '''
    Annotator for a C++ program's main file.
    '''
    ##
    # @param self The CppMainFileAnnotator instance to construct.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param dumpFileName File where the call graph database will be dumped.
    def __init__(self, doAdd, dumpFileName):
        '''
        Constructor.
        '''
        MainFileAnnotator.__init__(self, doAdd, dumpFileName)

    ##
    # @param self The CppMainFileAnnotator instance.
    # @param resultFile Result file to add the modified lines.
    # @param initSpaces Initial spaces to add to the line.
    def insertDumpFileCode_(self, resultFile, initSpaces):
        '''
        Insert in the resultFile a line to dump the call graph into a Json database.
        '''
        annotStr = 'code_cropper::ProgramExecutionDumper ' + DUMPER_VAR_NAME + '("' + asCppPathString(self.dumpFileName_) + '");'
        resultFile.write(initSpaces + CPP_INDENTATION + annotStr + '\n')

class PythonMainFileAnnotator(MainFileAnnotator):
    '''
    Annotator for a Python program's main file.
    '''
    ##
    # @param self The PythonMainFileAnnotator instance to construct.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param dumpFileName File where the call graph database will be dumped.
    def __init__(self, doAdd, dumpFileName):
        '''
        Constructor.
        '''    
        MainFileAnnotator.__init__(self, doAdd, dumpFileName)

    ##
    # @param self The PythonMainFileAnnotator instance.
    # @param resultFile Result file to add the modified lines.
    # @param initSpaces Initial spaces to add to the line.
    def insertDumpFileCode_(self, resultFile, initSpaces):
        '''
        Insert in the resultFile a line to dump the call graph into a Json database.
        '''
        resultFile.write(initSpaces + PYTHON_ANNOTATOR_VAR_NAME + " = code_cropper.annotator.annotatorInstance()\n")
        resultFile.write(initSpaces + PYTHON_ANNOTATOR_VAR_NAME + ".resetForNewAnnotations()\n")
        beginAnnotations(resultFile, initSpaces)        
        endAnnotations(resultFile, initSpaces)
        annotStr = 'with code_cropper.annotator.ProgramExecutionDumper("' + asCppPathString(self.dumpFileName_) + '") as ' + DUMPER_VAR_NAME + ':'
        resultFile.write(initSpaces + annotStr + '\n')

##
# @param doAdd If True, we're adding annotations, else we're removing them.
# @param language The program's programming language.
# @param dumpFileName File where the call graph database will be dumped.
# @return A new MainFileAnnotator instance.
def createMainFileAnnotator(doAdd, language, dumpFileName):
    '''
    Create the MainFileAnnotator, according to the language.
    '''
    
    LANG = ProgramExecution.Languages
    assert language in [LANG.C_PLUS_PLUS, LANG.PYTHON]
    return CppMainFileAnnotator(doAdd, dumpFileName) if language == LANG.C_PLUS_PLUS else PythonMainFileAnnotator(doAdd, dumpFileName)

class LineProcessor:
    '''
    Base class for "Line Processors": they process file lines
    in processLine() function, to perform a concrete task.
    '''
    ##
    # @param self The LineProcessor instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor.
        '''
        self.languageTokenizer_ = code_regions_parsing.LanguageTokenizer(language)
        
        self.line_ = None
        
        self.processingFirstEvent_ = False
        
        self.insideAnnotations_ = False
        self.insideCodeCropper_ = False
        self.insideFunction_ = False
        self.insideClass_ = False
        
        self.params_ = None
        self.className_ = None

    ##
    # @param self The LineProcessor instance.
    def beginProcess(self):
        '''
        Call this function before processing the file lines.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def endProcess(self):
        '''
        Call this function after processing the file lines.
        '''
        if self.languageTokenizer_.getFunctionName():
            self.exitFunction_()
        if self.languageTokenizer_.getClassName():
            self.exitClass_()
    
    ##
    # @param self The LineProcessor instance.
    # @param line The current source code line being processed.
    # @param nextLine The next code line (in Python, this affects the current line parsing, because it may indicate a code region enter or exit).
    def processLine(self, line, nextLine):
        '''
        Callback for processFile.
        Parse a line ("spying" nextLine, if necessary).
        With the help of a LanguageTokenizer, discover the line events.
        And later process them in the derivatives through
        template methods like enterClass_(), exitClass_(), etc.
        '''
        self.languageTokenizer_.parseLine(line, nextLine)
        self.line_ = line
        self.beginProcessLine_()
        
        #Process events:
        LE = code_regions_parsing.LanguageTokenizer.LineEvents
        lineEvents = self.languageTokenizer_.getLineEvents()
        self.processingFirstEvent_ = True
        if not lineEvents:
            #If no events are present, process anyway
            self.endProcessLine_()
            self.processingFirstEvent_ = False
        else:
            for lineEvent in lineEvents:
                if lineEvent == LE.ENTER_ANNOTATIONS:
                    self.insideAnnotations_= True
                    self.enterAnnotations_()
                elif lineEvent == LE.EXIT_ANNOTATIONS:
                    self.insideAnnotations_ = False
                    self.exitAnnotations_()
                    self.clearAnnotationsStuff()
                elif lineEvent == LE.ENTER_CODE_CROPPER:
                    self.insideCodeCropper_= True
                    self.enterCodeCropper_()
                elif lineEvent == LE.EXIT_CODE_CROPPER:
                    self.insideCodeCropper_ = False
                    self.exitCodeCropper_()
                    self.clearCodeCropperStuff()
                elif lineEvent == LE.ENTER_FUNCTION:
                    self.insideFunction_ = True
                    self.enterFunction_()
                elif lineEvent == LE.EXIT_FUNCTION:
                    assert self.insideFunction_
                    self.insideFunction_ = False
                    self.exitFunction_()
                    self.clearFunctionStuff()
                elif lineEvent == LE.ENTER_CLASS:
                    self.insideClass_ = True
                    self.enterClass_()
                else:
                    assert lineEvent == LE.EXIT_CLASS
                    assert self.insideClass_
                    self.insideClass_ = False
                    self.exitClass_()
                    self.clearClassStuff()
                self.endProcessLine_()
                self.processingFirstEvent_ = False

    ##
    # @param self The LineProcessor instance.
    def enterClass_(self):
        '''
        Template method to be called right after entering a class.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def exitClass_(self):
        '''
        Template method to be called right before leaving a class.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def enterFunction_(self):
        '''
        Template method to be called right after entering a function.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def exitFunction_(self):
        '''
        Template method to be called right before leaving a function.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def enterCodeCropper_(self):
        '''
        Template method to be called right after entering a "Code Cropper" region.
        '''
        pass
    
    ##
    # @param self The LineProcessor instance.
    def exitCodeCropper_(self):
        '''
        Template method to be called right before leaving a "Code Cropper" region.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def enterAnnotations_(self):
        '''
        Template method to be called right after entering the annotations region.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def exitAnnotations_(self):
        '''
        Template method to be called right before leaving the annotations region.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def beginProcessLine_(self):
        '''
        Template method to be called right before processing a line.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def endProcessLine_(self):
        '''
        Template method to be called right after processing a line.
        '''
        pass

    ##
    # @param self The LineProcessor instance.
    def clearAnnotationsStuff(self):
        '''
        Clear annotations-related data.
        '''
        self.languageTokenizer_.clearAnnotationsStuff()

    ##
    # @param self The LineProcessor instance.
    def clearCodeCropperStuff(self):
        '''
        Clear "Code Cropper"-related data.
        '''
        self.languageTokenizer_.clearCodeCropperStuff()

    ##
    # @param self The LineProcessor instance.
    def clearFunctionStuff(self):
        '''
        Clear function-related data.
        '''
        self.languageTokenizer_.clearFunctionStuff()
        self.params_ = None
        
    ##
    # @param self The LineProcessor instance.
    def clearClassStuff(self):
        '''
        Clear class-related data.
        '''
        self.languageTokenizer_.clearClassStuff()

class LineProcessorWithResultFile(LineProcessor):
    '''
    Base class for "Line Processors" that write in a result file.
    '''
    ##
    # @param self The LineProcessor instance to construct.
    # @param language The program's programming language.
    # @param resultFile Result file to add the modified lines.
    def __init__(self, language, resultFile):
        '''
        Constructor.
        '''
        LineProcessor.__init__(self, language)
        self.resultFile_ = resultFile

    ##
    # @param self The LineProcessor instance.
    # @param line The line to insert in the result file.
    def writeInFile_(self, line):
        '''
        Insert the line in the result file, with the condition
        that it's the first time the current event is processed
        (to prevent multiple insertions).
        '''
        if self.processingFirstEvent_:
            self.resultFile_.write(line)

class GetClassesAndFunctionsLineProcessor(LineProcessor):
    '''
    "Line Processor" class that gets all the functions and classes
    for a file, and calculates their annotation state.
    '''
    ##
    # @param self The GetClassesAndFunctionsLineProcessor instance to construct.
    # @param language The program's programming language.    
    def __init__(self, language):
        '''
        Constructor.
        '''
        LineProcessor.__init__(self, language)
        self.classes_ = []
        self.functions_ = []
        self.functionAnnotationState_ = AnnotationState.NOT_ANNOTATED
        self.classAnnotationState_ = AnnotationState.NOT_ANNOTATED

    ##
    # @param self The GetClassesAndFunctionsLineProcessor instance.
    def enterCodeCropper_(self):
        '''
        Enter a "Code Cropper" region. The current class or function
        is hence annotated -> upgrade its status.
        '''
        if self.languageTokenizer_.getFunctionName():
            self.functionAnnotationState_ = AnnotationState.ANNOTATED
        if self.languageTokenizer_.getClassName():
            self.classAnnotationState_ = AnnotationState.ANNOTATED

    ##
    # @param self The GetClassesAndFunctionsLineProcessor instance.
    def exitClass_(self):
        '''
        Leave a class, and consolidate its annotation state.
        '''
        self.classes_.append((self.languageTokenizer_.getClassName(), self.classAnnotationState_))
        self.classAnnotationState_ = AnnotationState.NOT_ANNOTATED
        self.className_ = None

    ##
    # @param self The GetClassesAndFunctionsLineProcessor instance.
    def exitFunction_(self):
        '''
        Leave a function, and consolidate its annotation state.
        '''
        if not self.languageTokenizer_.getClassName():
            self.functions_.append((self.languageTokenizer_.getFunctionName(), self.functionAnnotationState_))
        self.functionAnnotationState_ = AnnotationState.NOT_ANNOTATED

    ##
    # @param self The GetClassesAndFunctionsLineProcessor instance.
    # @return A list of tuples (class name, annotation state) for all classes in the file.
    def getClasses(self):
        '''
        Return a list of tuples (class name, annotation state) for all classes in the file.
        '''
        return self.classes_

    ##
    # @param self The GetClassesAndFunctionsLineProcessor instance.
    # @return A list of tuples (function name, annotation state) for all global function in the file.
    def getFunctions(self):
        '''
            Return a list of tuples (function name, annotation state) for all global function in the file.
        '''
        return self.functions_

class AnnotatePythonObjectLineProcessor(LineProcessorWithResultFile):
    '''
    "Line Processor" to annotate Python Objects in a Python source file.
    '''
    ##
    # @param self The AnnotatePythonObjectLineProcessor instance to construct.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param language The program's programming language.
    # @param resultFile Result file to add the modified lines.
    # @param pythonObjectName Python object to annotate.
    # @param itsAModule If true, pythonObjectName is a Python module.
    # @param pythonFunctionName Optional child function to annotate (if empty, all pythonObjectName's children function are annotated).
    def __init__(self, doAdd, language, resultFile, pythonObjectName, itsAModule, pythonFunctionName = None):
        '''
        Constructor.
        '''    
        LineProcessorWithResultFile.__init__(self, language, resultFile)
        self.doAdd_ = doAdd
        self.pythonObjectName_ = pythonObjectName
        self.headerToInclude_ = getPythonImportFromObject(pythonObjectName, itsAModule)
        self.pythonImportLine_ = None if self.headerToInclude_ is None else getPythonImportLine(self.headerToInclude_)
        self.pythonImportLineFound_ = False
        self.pythonFunctionName_ = pythonFunctionName
        self.aboutToExitAnnotations_ = False
        self.alreadyErasedAnnotation_ = False
        self.alreadyProcessedIncludes_ = False
        self.aboutToExitIncludes_ = False
        self.pythonObjAnnotation_ = getPythonObjectAnnotationToInsert(pythonObjectName, pythonFunctionName)
        
    ##
    # @param self The AnnotatePythonObjectLineProcessor instance.
    def exitCodeCropper_(self):
        '''
        Exit a Code Cropper region. It's important for later adding the Python import.
        '''
        if not self.alreadyProcessedIncludes_:
            self.aboutToExitIncludes_ = True
            self.alreadyProcessedIncludes_ = True

    ##
    # @param self The AnnotatePythonObjectLineProcessor instance.
    def exitAnnotations_(self):
        '''
        About to Exit annotations. Flag this state for later use.
        '''
        self.aboutToExitAnnotations_ = True

    ##
    # @param self The AnnotatePythonObjectLineProcessor instance.
    def endProcessLine_(self):
        '''
        Method to be called right after processing a line.
        It actually performs the annotations (if any) in the result file.
        '''
        if self.doAdd_:
            if not self.alreadyProcessedIncludes_:
                if self.pythonImportLine_ and self.line_ == self.pythonImportLine_:
                    self.pythonImportLineFound_ = True
            elif self.aboutToExitIncludes_:
                if self.headerToInclude_ and not self.pythonImportLineFound_:
                    self.writeInFile_("import " + self.headerToInclude_ + '\n')
                self.aboutToExitIncludes_ = False
            elif self.aboutToExitAnnotations_:
                initSpaces = self.languageTokenizer_.getFunctionInitialSpaces()
                self.writeInFile_(initSpaces + self.pythonObjAnnotation_ + '\n')
                self.aboutToExitAnnotations_ = False
            self.writeInFile_(self.line_)
        else:
            skipLine = False
            if self.insideAnnotations_:
                if not self.alreadyErasedAnnotation_:
                    if self.line_.find(self.pythonObjAnnotation_) >= 0:
                        skipLine = True
                        self.alreadyErasedAnnotation_ = True
            if not skipLine:
                self.writeInFile_(self.line_)

class CountAnnotationsLineProcessor(LineProcessor):
    '''
    "Line Processor" class that counts all "Code Cropper" code regions in a file.
    '''
    ##
    # @param self The CountAnnotationsLineProcessor instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor.
        '''    
        LineProcessor.__init__(self, language)
        self.annotationsCount_ = 0

    ##
    # @param self The CountAnnotationsLineProcessor instance.
    def enterCodeCropper_(self):
        '''
        Enter a "Code Cropper" region. The current class or function
        is hence annotated -> increase the annotations count.
        '''
        self.annotationsCount_ += 1

    ##
    # @param self The CountAnnotationsLineProcessor instance.
    # @return The cumulated total number of "Code Cropper" code regions in the file.
    def getAnnotationsCount(self):
        '''
        Get the total number of "Code Cropper" code regions in the file.
        '''
        return self.annotationsCount_

class CountPythonImportsUseLineProcessor(LineProcessor):
    '''
    "Line Processor" class that counts all occurrences of a Python import line.
    '''
    ##
    # @param self The CountPythonImportsUseLineProcessor instance to construct.
    # @param language The program's programming language.
    # @param pythonImport Python import sentence to find in the file.
    def __init__(self, language, pythonImport):
        '''
        Constructor.
        '''
        LineProcessor.__init__(self, language)
        self.pythonImportsUseCount_ = 0
        self.annotationToFind_ = getPythonObjectAnnotationHead() + pythonImport

    ##
    # @param self The CountPythonImportsUseLineProcessor instance.
    def endProcessLine_(self):
        '''
        Method to be called right after processing a line.
        If found, it actually cumulates the occurrences number for the searched Python import.
        '''
        if self.insideAnnotations_:
            if self.line_.find(self.annotationToFind_) >= 0: 
                self.pythonImportsUseCount_ += 1

    ##
    # @param self The CountPythonImportsUseLineProcessor instance.
    # @return the occurrences number for the searched Python import.
    def getCount(self):
        '''
        Return the occurrences number for the searched Python import.
        '''
        return self.pythonImportsUseCount_
    
class CalculatePythonAnnotationStatesLineProcessor(LineProcessor):
    '''
    "Line Processor" class that calculates annotation state
    for all Python objects in the main file.
    '''
    ##
    # @param self The CalculatePythonAnnotationStatesLineProcessor instance to construct.
    # @param language The program's programming language.
    # @param pythonImport Python import sentence to add a prefix to the classes or functions.
    # @param classes Container with tuples (class name, annotation state), whose states will be updated after processing the file.
    # @param functions Container with tuples (function name, annotation state), whose states will be updated after processing the file.
    def __init__(self, language, pythonImport, classes, functions):
        '''
        Constructor.
        '''
        LineProcessor.__init__(self, language)
        self.pythonImport_ = pythonImport
        self.classes_ = classes
        self.functions_ = functions

    # @param self The CalculatePythonAnnotationStatesLineProcessor instance to construct.
    def endProcessLine_(self):
        '''
        Method to be called right after processing a line.
        It takes the classes and function containers, and it upgrades their status to "annotated"
        if their annotations are found in this line.
        '''
        ##
        # @param aPythonClassName A Python class name.
        # @return The annotation line correspondent to the Python class.
        def getPythonObjectAnnotationToInsertForClasses(aPythonClassName):
            '''
            Return the annotation line correspondent to Python class. 
            '''
            head = self.pythonImport_ + '.' if self.pythonImport_ else ''
            pythonFullClassName = head + aPythonClassName
            return getPythonObjectAnnotationToInsert(pythonFullClassName)

        ##
        # @param aFunctionName A Python function name.
        # @return The annotation line correspondent to the Python function name.
        def getPythonObjectAnnotationToInsertForFunctions(aFunctionName):
            '''
            Return the annotation line correspondent to the Python function name.
            '''
            return getPythonObjectAnnotationToInsert(self.pythonImport_, aFunctionName)
            
        ##
        # @param container Container to process its annotations.
        # @param getPythonObjectAnnotationToInsertCb Callback to get the Python annotation for the class or function being processed.
        # @return Annotation state for the whole container (ANNOTATED if there's at least one child annotated).
        def processLineForContainer(container, getPythonObjectAnnotationToInsertCb):
            '''
            Process current line for a container (classes or functions).
            '''
            #Verify whether this line is an annotation for container
            index = 0
            state = AnnotationState.NOT_ANNOTATED
            for aPythonObject, annotState in container:
                pythonObjAnnotation = getPythonObjectAnnotationToInsertCb(aPythonObject)
                if self.line_.strip() == pythonObjAnnotation:
                    state = AnnotationState.ANNOTATED
                    break
                index += 1
            if state == AnnotationState.ANNOTATED:
                aPythonObject, annotState = container[index]
                annotState = AnnotationState.ANNOTATED
                container[index] = aPythonObject, annotState
            return state
            
        if self.insideAnnotations_:
            state = processLineForContainer(self.classes_, getPythonObjectAnnotationToInsertForClasses)
            if state == AnnotationState.NOT_ANNOTATED:
                state = processLineForContainer(self.functions_, getPythonObjectAnnotationToInsertForFunctions)

class RemoveIncludesLineProcessor(LineProcessorWithResultFile):
    '''
    "Line Processor" that removes an Include line from a file.
    '''
    ##
    # @param self The RemoveIncludesLineProcessor instance to construct.
    # @param language The program's programming language.
    # @param resultFile Result file to remove the include to.
    def __init__(self, language, resultFile):
        '''
        Constructor.
        '''
        LineProcessorWithResultFile.__init__(self, language, resultFile)
        self.skipLines_ = False
        self.removeBraEndMark_ = False

    ##
    # @param self The RemoveIncludesLineProcessor instance.
    def enterCodeCropper_(self):
        '''
        Enter a "Code Cropper" region. If it's the first region (i.e.: the "includes"),
        mark it to skip the lines, to remove the includes.
        '''
        self.skipLines_ = True

    ##
    # @param self The RemoveIncludesLineProcessor instance.
    def exitCodeCropper_(self):
        '''
        Exit a "Code Cropper" region. Flag the removing process as finished.
        '''
        self.skipLines_ = False
        self.removeBraEndMark_ = True

    ##
    # @param self The RemoveIncludesLineProcessor instance.
    def endProcessLine_(self):
        '''
        End processing a line. If we're inside the "includes" region, skip this code.
        Else, copy it in the result file.
        '''
        if not self.skipLines_:
            if self.removeBraEndMark_:
                self.removeBraEndMark_ = False
            else:
                self.writeInFile_(self.line_)

class RemovePythonImportLineProcessor(LineProcessorWithResultFile):
    '''
    "Line Processor" that removes a Python import line from a file.
    '''
    ##
    # @param self The RemovePythonImportLineProcessor instance to construct.
    # @param language The program's programming language.
    # @param resultFile Result file to remove the include to.
    # @param pythonImport Python import line to remove from the result file.
    def __init__(self, language, resultFile, pythonImport):
        '''
        Constructor.
        '''
        LineProcessorWithResultFile.__init__(self, language, resultFile)
        self.pythonImportLine_ = getPythonImportLine(pythonImport)
 
    ##
    # @param self The RemovePythonImportLineProcessor instance.
    def enterCodeCropper_(self):
        '''
        Enter a "Code Cropper" region. If it's the first region (i.e.: the "includes"),
        flag it to look for the import line later, and remove it.
        '''
        self.annotatingIncludes_ = True

    ##
    # @param self The RemovePythonImportLineProcessor instance.
    def exitCodeCropper_(self):
        '''
        Exit a "Code Cropper" region. Flag the removing process as finished.
        '''
        self.annotatingIncludes_ = False

    ##
    # @param self The RemovePythonImportLineProcessor instance.
    def endProcessLine_(self):
        '''
        End processing a line. If we're inside the "includes" region,
        and we find the import line to remove -> skip this code.
        Else, copy it in the result file.
        '''
        if self.line_ != self.pythonImportLine_:
            #else, skip line
            self.writeInFile_(self.line_)

class AnnotateGlobalFunctionsLineProcessor(LineProcessorWithResultFile):
    '''
    "Line Processor" to annotate functions.
    '''
    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance to construct.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param language The program's programming language.
    # @param myFunctionAnnotator Action instance that actually annotates.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFile Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param classNames Class names from the file.
    # @param functionNames Function names from the file.
    def __init__(self, doAdd, language, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, classNames, functionNames):
        '''
        Constructor.
        '''
        LineProcessorWithResultFile.__init__(self, language, resultFile)
        self.doAdd_ = doAdd
        self.myFunctionAnnotator_ = myFunctionAnnotator
        self.headerToInclude_ = headerToInclude
        self.functionNames_ = functionNames
        self.classNames_ = classNames
        self.justEnteredFunction_ = False
        self.functionInitialSpaces_ = None
        self.skipLines_ = False
        self.pendingLine_ = None
        self.mustExitFunction_ = False
        self.mustExitCodeCropper_ = False
        self.thisFunctionWasAnnotated_ = False
        self.unannotatingFunction_ = False

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    def enterCodeCropper_(self):
        '''
        Enter a "Code Cropper" region.
        Prepare the flags to (un)annotate in endProcessLine_().
        '''
        if not self.doAdd_ and self.unannotatingFunction_:
            self.thisFunctionWasAnnotated_ = True
            self.skipLines_ = True
            self.pendingLine_ = None

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    def exitCodeCropper_(self):
        '''
        Exit a "Code Cropper" region.
        Prepare the flags to annotate in endProcessLine_().
        '''
        if not self.doAdd_ and self.unannotatingFunction_:
            self.mustExitCodeCropper_ = True

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    def enterFunction_(self):
        '''
        Enter a function. Set the flags for endProcessLine_().
        '''
        if self.satisfiesClassConditions_():
            if not self.functionNames_ or ( self.languageTokenizer_.getFunctionName() in self.functionNames_ ):
                self.justEnteredFunction_ = True
                if not self.doAdd_:
                    self.unannotatingFunction_ = True

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    def exitFunction_(self):
        '''
        Leave a function. Set the flags for endProcessLine_().
        '''
        if self.doAdd_:
            if self.satisfiesClassConditions_():
                if self.functionIsBeingAnnotated_():
                    self.myFunctionAnnotator_.annotateFunctionEnding(self.resultFile_, self.functionInitialSpaces_)
                self.functionInitialSpaces_ = None
        else:
            self.mustExitFunction_ = True

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    def enterClass_(self):
        '''
        Enter a class.
        '''
        pass

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    def exitClass_(self):
        '''
        Exit a class.
        '''
        pass

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    # @return Whether or not current class must be (un)annotated.
    def satisfiesClassConditions_(self):
        '''
        Current class name is included in the classes list to process
        (if the latter is empty, all classes do satisfy the condition).
        '''
        return not self.classNames_ or ( self.languageTokenizer_.getClassName() in self.classNames_ )

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    # @return Whether or not current function is being (un)annotated.
    def functionIsBeingAnnotated_(self):
        '''
        Return whether or not current function is being (un)annotated.
        '''
        return self.functionInitialSpaces_ is not None

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    def endProcessLine_(self):
        '''
        Call this function after processing a line.
        This is the function that actually (un)annotates, with the help
        of a FunctionAnnotator instance.
        '''
        if not self.doAdd_:
            if not self.skipLines_:
                #TODO GERVA: This is not correct, it's just a patch
                #This class shouldn't know anything about languages,
                #just give that responsibility to LanguageTokenizer
                if self.languageTokenizer_.getLanguage() == ProgramExecution.Languages.PYTHON:
                    line = self.line_
                    if self.unannotatingFunction_ and self.thisFunctionWasAnnotated_:
                        #Unindent initial spaces
                        line = line.replace(PYTHON_INDENTATION, '', 1)
                    if self.pendingLine_:
                        self.writeInFile_(self.pendingLine_)
                    self.pendingLine_ = line
                else:
                    self.writeInFile_(self.line_)
            if self.mustExitCodeCropper_:
                self.skipLines_ = False
                self.mustExitCodeCropper_ = False
            if self.mustExitFunction_:
                self.unannotatingFunction_ = False
                self.mustExitFunction_ = False
                self.thisFunctionWasAnnotated_ = False
        else:
            if self.justEnteredFunction_:
                if self.enterFunctionLineBeforeAnnotations_():
                    #This line is "{", so it keeps its indentation 
                    self.writeInFile_(self.line_)
                self.functionInitialSpaces_ = self.languageTokenizer_.getFunctionInitialSpaces()
                functionName = self.languageTokenizer_.getFunctionName()
                className = self.languageTokenizer_.getClassName()
                params = self.languageTokenizer_.getParams()
                methodTypeEnum = self.languageTokenizer_.getMethodTypeEnumForClass(functionName, className)
                self.myFunctionAnnotator_.annotateFunctionBeginning(self.line_, self.functionInitialSpaces_, self.resultFile_, self.headerToInclude_, functionName, params, methodTypeEnum, className)
                self.justEnteredFunction_ = False
                if not self.enterFunctionLineBeforeAnnotations_():
                    self.writeInFile_(self.getAdditionalIndentation_() + self.line_)
            else:
                #TODO GERVA: this is not correct, it adds the spaces at the beginning, it doesn't work for fixed indentation
                #tabs + spaces
                prefix = self.getAdditionalIndentation_() if self.functionIsBeingAnnotated_() else ''
                self.writeInFile_(prefix + self.line_)
       
    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    # @return The additional indentation to annotate.
    def getAdditionalIndentation_(self):
        '''
        Get additional indentation to annotate (besides initial spaces).
        Default: CPP, no indentation.
        '''
        return ''
    
    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    # @return Whether or not the "function discovery" comes before the annotations (C++) or may match (Python).
    def enterFunctionLineBeforeAnnotations_(self):
        '''
        Return whether or not the "function discovery" comes before the annotations or may match.
        Default: CPP, { comes before annotations.
        In Python, discovery line is part of the function body.
        '''
        return True

    ##
    # @param self The AnnotateGlobalFunctionsLineProcessor instance.
    def endProcess(self):
        '''
        End file process.
        '''
        if self.pendingLine_:
            self.processingFirstEvent_ = True
            self.writeInFile_(self.pendingLine_)
            self.processingFirstEvent_ = False
        
#Use the same class, because defaults are for C++
CppAnnotateGlobalFunctionsLineProcessor = AnnotateGlobalFunctionsLineProcessor

class PythonAnnotateGlobalFunctionsLineProcessor(AnnotateGlobalFunctionsLineProcessor):
    '''
    "Line Processor" to annotate Python functions.
    '''
    ##
    # @param self The PythonAnnotateGlobalFunctionsLineProcessor instance to construct.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param language The program's programming language.
    # @param myFunctionAnnotator Action instance that actually annotates.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFile Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param classNames Class names from the file.
    # @param functionNames Function names from the file.
    def __init__(self, doAdd, language, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, classNames, functionNames):
        ''''
        Constructor.
        '''
        AnnotateGlobalFunctionsLineProcessor.__init__(self, doAdd, language, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, classNames, functionNames) 

    ##
    # @param self The PythonAnnotateGlobalFunctionsLineProcessor instance.
    # @return The additional indentation to annotate.
    def getAdditionalIndentation_(self):
        '''
        Get additional indentation to annotate (besides initial spaces).
        '''
        return PYTHON_INDENTATION

    ##
    # @param self The PythonAnnotateGlobalFunctionsLineProcessor instance.
    # @return Whether or not the "function discovery" comes before the annotations (C++) or may match (Python).
    def enterFunctionLineBeforeAnnotations_(self):
        '''
        Return whether or not the "function discovery" comes before the annotations or may match.
        In Python, discovery line is part of the function body
        '''
        return False

##
# @param doAdd If True, we're adding annotations, else we're removing them.
# @param language The program's programming language.
# @param myFunctionAnnotator Action instance that actually annotates.
# @param originalFileName File name of the original (unprocessed) file name.
# @param resultFile Result file to add the modified lines.
# @param headerToInclude Header to include.
# @param classNames Class names from the file.
# @param functionNames Function names from the file.
# @return A new AnnotateGlobalFunctionsLineProcessor instance.
def createAnnotateGlobalFunctionsLineProcessor(doAdd, language, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, classNames, functionNames):
    '''
    Create the AnnotateGlobalFunctionsLineProcessor, according to the language.
    '''

    LANG = ProgramExecution.Languages
    assert language in [LANG.C_PLUS_PLUS, LANG.PYTHON]
    if language == LANG.C_PLUS_PLUS:
        return CppAnnotateGlobalFunctionsLineProcessor(doAdd, language, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, classNames, functionNames)
    else:
        return PythonAnnotateGlobalFunctionsLineProcessor(doAdd, language, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, classNames, functionNames)

class SourceCodeParser:
    '''
    It parses a source code file (Python or C++), and performs actions like adding or removing annotations,
    or consulting annotations state for classes and functions.
    '''
    ##
    # @param self The SourceCodeParser instance to construct.
    # @param language The program's programming language.
    # @param mainFilePath The program's main file path.
    # @param mainFunction The program's main function name.
    # @param backupFiles If True, create a backup file before annotating.
    def __init__(self, language, mainFilePath, mainFunction = 'main', backupFiles = False):
        '''
        Constructor.
        '''
        assert language in (ProgramExecution.Languages.PYTHON, ProgramExecution.Languages.C_PLUS_PLUS)
        self.language_ = language
        self.mainFilePath_ = mainFilePath
        self.mainFunction_ = mainFunction
        self.backupFiles_ = backupFiles

    @staticmethod
    ##
    # @param fileName File path.
    # @return The backup file name path.
    def getBackupFileName(fileName):
        '''
        Return The backup file name path.
        '''
        return fileName + BKP_EXTENSION

    # @param self The SourceCodeParser instance.
    # @param fileName The file to process.
    # @param aLineProcessor Concrete LineProcessor that processes every file line.
    def processFile_(self, fileName, aLineProcessor):
        '''
        Generic function to process a file, applying a "Line Processor"
        to every line.
        '''
        with open( fileName, 'r' ) as origFile:
            fileLines = origFile.readlines()
        
        currentLine = 0
        lastLine = len(fileLines) - 1
        
        aLineProcessor.beginProcess()
        for line in fileLines:
            if currentLine == lastLine:
                nextLine = None
            else:
                nextLine = fileLines[currentLine + 1]
                currentLine += 1
            aLineProcessor.processLine(line, nextLine)
        aLineProcessor.endProcess()

    # @param self The SourceCodeParser instance.
    # @param fileName The file to process.
    # @return The total "Code Cropper" regions in the file.
    def countAnnotations_(self, fileName):
        '''
        Count all the "Code Cropper" regions in the file.
        '''
        myLineProcessor = CountAnnotationsLineProcessor(self.language_)
        
        self.processFile_(fileName, myLineProcessor)
    
        return myLineProcessor.getAnnotationsCount()

    # @param self The SourceCodeParser instance.
    # @param pythonImport Python import to search.
    # @return The ocurrences of a Python import in the main file.
    def countPythonImportsUse_(self, pythonImport):
        '''
        Count all the ocurrences of a Python import in the main file.
        '''
        myLineProcessor = CountPythonImportsUseLineProcessor(self.language_, pythonImport)
        
        self.processFile_(self.mainFilePath_, myLineProcessor)
    
        return myLineProcessor.getCount()

    # @param self The SourceCodeParser instance.
    # @param fileName The file to process.
    # @return Whether or not a file has at least one include.
    def fileHasIncludes_(self, fileName):
        '''
        Return whether or not a file has at least one include.
        '''
        return self.countAnnotations_(fileName) > 0

    # @param self The SourceCodeParser instance.
    # @param fileName The file to process.
    # @param headerToInclude Header to include.
    # @return A tuple (classes, functions) with all annotations for a file. The containers have tuples (name, annotation state).
    def getAllClassesAndFunctionsAnnotations(self, fileName, headerToInclude = None):
        '''
        Get all annotations for a file's classes and global functions.
        '''
        myLineProcessor = GetClassesAndFunctionsLineProcessor(self.language_)
        
        self.processFile_(fileName, myLineProcessor)
        
        classes = myLineProcessor.getClasses()
        functions = myLineProcessor.getFunctions()
        
        #For Python, correct annotation states according to main file
        if self.language_ == ProgramExecution.Languages.PYTHON and headerToInclude:
            myLineProcessor = CalculatePythonAnnotationStatesLineProcessor(self.language_, headerToInclude, classes, functions)
            self.processFile_(self.mainFilePath_, myLineProcessor)
        
        return classes, functions

    # @param self The SourceCodeParser instance.
    # @param fileName The file to process.
    # @param headerToInclude Header to include.
    # @return A tuple (classes, functions) with all the classes and global functions from a file.
    def getAllClassesAndFunctions(self, fileName, headerToInclude = None):
        '''
        Get a file's classes and global functions.
        '''
        annotClasses, annotFunctions = self.getAllClassesAndFunctionsAnnotations(fileName, headerToInclude)
        classes = []
        functions = []
        for annotClass in annotClasses:
            classes.append(annotClass[0])
        for annotFunction in annotFunctions:
            functions.append(annotFunction[0])
        return classes, functions

    # @param self The SourceCodeParser instance.
    # @param dumpFileName File where the call graph database will be dumped.
    def annotateMainFile(self, dumpFileName ):
        '''
        Add annotations to main file.
        '''
        #First, unannotate... this is a good way to refresh changes in file
        self.unAnnotateMainFile()
        #Now, actually annotate
        self.addOrRemoveAnnotationsToMainFile_(self.language_, True, dumpFileName)

    # @param self The SourceCodeParser instance.
    def unAnnotateMainFile(self):
        '''
        Remove annotations from main file.
        '''
        self.addOrRemoveAnnotationsToMainFile_(self.language_, False)

    ##
    # @param self The SourceCodeParser instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to add the modified lines.
    # @param headerToInclude Header to include.
    def annotateCppFile(self, originalFileName, resultFileName, headerToInclude):
        '''
        Annotate a C++ source file.
        '''
        #First, unannotate... this is a good way to refresh changes in file
        unannotatedFileName = originalFileName  + ".aux"
        classAnnotatedFileName = originalFileName  + ".aux2"
        try:
            shutil.copy(originalFileName, unannotatedFileName)
            self.unAnnotateCppFile(originalFileName, unannotatedFileName)
            #Now, actually annotate
            classNames, functionNames = self.getAllClassesAndFunctions(unannotatedFileName, headerToInclude)
            self.addOrRemoveClassesAnnotations_(True, unannotatedFileName, classAnnotatedFileName, headerToInclude, classNames, [], annotateIncludes = True)
            self.addOrRemoveFunctionAnnotations_(True, classAnnotatedFileName, resultFileName, headerToInclude, functionNames, annotateIncludes = False)
        except Exception, e:
            raise e
        finally:
            if os.path.exists(unannotatedFileName):
                os.remove(unannotatedFileName)
            if os.path.exists(classAnnotatedFileName):
                os.remove(classAnnotatedFileName)
    
    ##
    # @param self The SourceCodeParser instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param functionNames Global functions filter to process.
    def annotateCppFunctions(self, originalFileName, resultFileName, headerToInclude, functionNames = []):
        '''
        Annotate a C++ source file global functions.
        '''
        if not functionNames:
            _, functionNames = self.getAllClassesAndFunctions(originalFileName, headerToInclude)
        #First, unannotate... this is a good way to refresh changes in file
        unannotatedFileName = originalFileName  + ".aux"
        try:
            shutil.copy(originalFileName, unannotatedFileName)
            self.unannotateCppFunctions(originalFileName, unannotatedFileName, functionNames)
            #Now, actually annotate
            self.addOrRemoveFunctionAnnotations_(True, unannotatedFileName, resultFileName, headerToInclude, functionNames)
        except Exception, e:
            import traceback
            traceback.print_exc()
            raise e
        finally:
            if os.path.exists(unannotatedFileName):
                os.remove(unannotatedFileName)

    ##
    # @param self The SourceCodeParser instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param classNames Classes filter to process.
    def annotateCppClasses(self, originalFileName, resultFileName, headerToInclude, classNames = []):
        '''
        Annotate a C++ source file classes.
        '''
        if not classNames:
            classNames, _ = self.getAllClassesAndFunctions(originalFileName, headerToInclude)

        #First, unannotate... this is a good way to refresh changes in file
        unannotatedFileName = originalFileName  + ".aux"
        try:
            shutil.copy(originalFileName, unannotatedFileName)
            self.unannotateCppClasses(originalFileName, unannotatedFileName, classNames)
            #Now, actually annotate
            self.addOrRemoveClassesAnnotations_(True, unannotatedFileName, resultFileName, headerToInclude, classNames)
        finally:
            if os.path.exists(unannotatedFileName):
                os.remove(unannotatedFileName)

    ##
    # @param self The SourceCodeParser instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param className Class filter to process.
    # @param functionNames The classes' member functions to process.
    def annotateCppClassFunctions(self, originalFileName, resultFileName, headerToInclude, className, functionNames = []):
        '''
        Annotate a C++ source file classes member functions.
        '''
        #First, unannotate... this is a good way to refresh changes in file
        unannotatedFileName = originalFileName  + ".aux"
        try:
            shutil.copy(originalFileName, unannotatedFileName)
            self.unannotateCppClassFunctions(originalFileName, unannotatedFileName, className, functionNames)
            #Now, actually annotate
            self.addOrRemoveClassesAnnotations_(True, unannotatedFileName, resultFileName, headerToInclude, [className], functionNames)
        except Exception, e:
            raise e
        finally:
            if os.path.exists(unannotatedFileName):
                os.remove(unannotatedFileName)

    ##
    # @param self The SourceCodeParser instance.
    # @param pythonObjectName Name of a Python object to annotate.
    # @param itsAModule If true, Python object is a module.
    # @param functionName Function to process.   
    def annotatePythonObject(self, pythonObjectName, itsAModule, functionName = None):
        '''
        Annotate a Python object.
        '''
        self.unAnnotatePythonObject(pythonObjectName, itsAModule, functionName)
        mainFileAux = self.mainFilePath_ + '.aux'
        shutil.copy(self.mainFilePath_, mainFileAux)
        #Now, actually annotate
        try:
            with open(self.mainFilePath_, 'w') as resultFile:
                myLineProcessor = AnnotatePythonObjectLineProcessor(True, self.language_, resultFile, pythonObjectName, itsAModule, functionName)
                self.processFile_(mainFileAux, myLineProcessor)
        finally:
            if os.path.exists(mainFileAux):
                os.remove(mainFileAux)

    ##
    # @param self The SourceCodeParser instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to remove the annotations to. 
    def unAnnotateCppFile(self, originalFileName, resultFileName):
        '''
        Remove annotations from a C++ source file.
        '''
        classNames, functionNames = self.getAllClassesAndFunctions(originalFileName)
        self.addOrRemoveFileAnnotations_(False, originalFileName, resultFileName, "", classNames, functionNames)

    ##
    # @param self The SourceCodeParser instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to remove the annotations to.
    # @param functionNames Global functions to process.
    def unannotateCppFunctions(self, originalFileName, resultFileName, functionNames = []):
        '''
        Remove annotations from a C++ source file, filtering the global functions.
        '''
        if not functionNames:
            _, functionNames = self.getAllClassesAndFunctions(originalFileName)
        self.addOrRemoveFileAnnotations_(False, originalFileName, resultFileName, "", None, functionNames)

    ##
    # @param self The SourceCodeParser instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to remove the annotations to.
    # @param classNames Class names to process.
    def unannotateCppClasses(self, originalFileName, resultFileName, classNames = []):
        '''
        Remove annotations from a C++ source file, filtering the classes.
        '''
        if not classNames:
            classNames, _ = self.getAllClassesAndFunctions(originalFileName)
        self.addOrRemoveFileAnnotations_(False, originalFileName, resultFileName, "", classNames)

    ##
    # @param self The SourceCodeParser instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to remove the annotations to.
    # @param className Class name to process.
    # @param functionNames Member function names to process.
    def unannotateCppClassFunctions(self, originalFileName, resultFileName, className, functionNames = []):
        '''
        Remove annotations from a C++ source file, filtering the classes and their member functions.
        '''
        self.addOrRemoveFileAnnotations_(False, originalFileName, resultFileName, "", [className], functionNames)

    ##
    # @param pythonObjectName Name of a Python object to unannotate.
    # @param itsAModule If true, Python object is a module.
    # @param functionName Function to process.
    def unAnnotatePythonObject(self, pythonObjectName, itsAModule, functionName = None):
        '''
        Unannotate a Python object.
        '''
        mainFileAux = self.mainFilePath_ + '.aux'
        shutil.copy(self.mainFilePath_, mainFileAux)
        try:
            with open(self.mainFilePath_, 'w') as resultFile:
                myLineProcessor = AnnotatePythonObjectLineProcessor(False, self.language_, resultFile, pythonObjectName, itsAModule, functionName)
                self.processFile_(mainFileAux, myLineProcessor)
        except Exception, e:
            raise e
        finally:
            if os.path.exists(mainFileAux):
                os.remove(mainFileAux)
        #Finally, get rid of unused imports
        pythonImport = getPythonImportFromObject(pythonObjectName, itsAModule)
        if pythonImport: 
            self.removePythonImports_(pythonImport)
       
    #Private functions

    ##
    # @param self The SourceCodeParser instance.
    # @param language The program's programming language.    
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param dumpFileName File where the call graph database will be dumped.
    def addOrRemoveAnnotationsToMainFile_(self, language, doAdd, dumpFileName = ""):
        '''
        Add or remove annotations to the program's main file.
        '''
        try:
            #For every method, work with a temporary file, and leave results there.
            #Use the temporary results by reaming the files
            mainFileBackup = SourceCodeParser.getBackupFileName(self.mainFilePath_)
            shutil.copy(self.mainFilePath_, mainFileBackup)
            with open(self.mainFilePath_, 'w') as resultFile:
                if doAdd:
                    self.annotateIncludes_(self.language_, mainFileBackup, resultFile)
                #TODO GERVA: ver el tema de doAdd
                myFunctionAnnotator = createMainFileAnnotator(doAdd, language, dumpFileName)
                self.processGlobalFunctions_(doAdd, myFunctionAnnotator, mainFileBackup, resultFile, None, None, [self.mainFunction_])
            if not doAdd:
                self.removeIncludes_(self.mainFilePath_)
        except Exception, e:
            import traceback
            traceback.print_exc()
            #restore main file
            shutil.copy(mainFileBackup, self.mainFilePath_)
            print str(e)
            raise e
        finally:
            if not self.backupFiles_ and os.path.exists(mainFileBackup):
                os.remove(mainFileBackup)            

    ##
    # @param self The SourceCodeParser instance.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param classNames Class names from the file.
    # @param functionNames Function names from the file.
    # @param annotateIncludes If True, annotate the includes.
    def addOrRemoveFileAnnotations_(self, doAdd, originalFileName, resultFileName, headerToInclude = "", classNames = [], functionNames = [], annotateIncludes = True):
        '''
        Generic function to add or remove annotations to a source file.
        '''
        #For every method, work with a temporary file, and leave results there.
        #Use the temporary results by reaming the files
        originalFileNameWork = originalFileName  + ".work"
        originalFileNameWork2 = originalFileName  + ".work2"
        try:
            shutil.copy(originalFileName, originalFileNameWork)
            myFunctionAnnotator = CppRegularFunctionAnnotator()
            #Annotate functions
            # originalFileNameWork2 must be the file to process in the nex step
            # -> if not functionNames to process, just copy the file
            if functionNames and not isOneClass(classNames):
                with open( originalFileNameWork2, 'w' ) as resultFile:
                    if doAdd and annotateIncludes:
                        self.annotateIncludes_(originalFileNameWork, resultFile)
                    self.processGlobalFunctions_(doAdd, myFunctionAnnotator, originalFileNameWork, resultFile, headerToInclude, None, functionNames)
            else:
                shutil.copy(originalFileNameWork, originalFileNameWork2)
            #Annotate classes
            if classNames:
                with open( resultFileName, 'w' ) as resultFile:
                    myFunctionNames = functionNames if isOneClass(classNames) else []
                    self.processClasses_(doAdd, myFunctionAnnotator, originalFileNameWork2, resultFile, headerToInclude, classNames, myFunctionNames)
            else:
                shutil.copy(originalFileNameWork2, resultFileName)
            if not doAdd:
                self.removeIncludes_(resultFileName)
        except Exception, e:
            raise e
        finally:
            if os.path.exists(originalFileNameWork):
                os.remove(originalFileNameWork)
            if os.path.exists(originalFileNameWork2):
                os.remove(originalFileNameWork2)

    ##
    # @param self The SourceCodeParser instance.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param classNames Class names from the file.
    # @param functionNames Function names from the file.
    # @param annotateIncludes If True, annotate the includes.
    def addOrRemoveClassesAnnotations_(self, doAdd, originalFileName, resultFileName, headerToInclude, classNames, functionNames = [], annotateIncludes = True):
        '''
        Generic function to add or remove annotations to a source file classes.
        '''
        self.addOrRemoveAnnotations_(doAdd, originalFileName, resultFileName, headerToInclude, classNames, functionNames, self.processClasses_, annotateIncludes)

    ##
    # @param self The SourceCodeParser instance.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param functionNames Global functions to process.
    # @param annotateIncludes If True, annotate the includes.
    def addOrRemoveFunctionAnnotations_(self, doAdd, originalFileName, resultFileName, headerToInclude, functionNames, annotateIncludes = True):
        '''
        Generic function to add or remove annotations to a source file global functions.
        '''
        self.addOrRemoveAnnotations_(doAdd, originalFileName, resultFileName, headerToInclude, [], functionNames, self.processGlobalFunctions_, annotateIncludes)
    
    #Implementation

    ##
    # @param self The SourceCodeParser instance.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFileName Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param classNames Class names from the file.    
    # @param functionNames Function names from the file.
    # @param processCallback Action to take with the file after annotating the includes.
    # @param annotateIncludes If True, annotate the includes.
    def addOrRemoveAnnotations_(self, doAdd, originalFileName, resultFileName, headerToInclude, classNames, functionNames, processCallback, annotateIncludes):
        '''
        Add or remove annotations to a source file, with a parameter callback to process.
        '''
        #For every method, work with a temporary file, and leave results there.
        #Use the temporary results by reaming the files
        originalFileNameWork = originalFileName  + ".work"
        try:
            shutil.copy(originalFileName, originalFileNameWork)
            with open( resultFileName, 'w' ) as resultFile:
                myFunctionAnnotator = CppRegularFunctionAnnotator()
                if doAdd:
                    if annotateIncludes:
                        self.annotateIncludes_(self.language_, originalFileNameWork, resultFile)
                    processCallback(doAdd, myFunctionAnnotator, originalFileNameWork, resultFile, headerToInclude, classNames, functionNames)
            if not doAdd:
                removeIncludes(resultFileName)
        finally:
            if os.path.exists(originalFileNameWork):
                os.remove(originalFileNameWork)

    ##
    # @param self The SourceCodeParser instance.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param myFunctionAnnotator Action instance that actually annotates.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFile Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param functionNames Function names from the file.
    def processGlobalFunctions_(self, doAdd, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, _, functionNames ):
        '''
        Add or remove annotations to a source file global functions.
        '''
        myLineProcessor = createAnnotateGlobalFunctionsLineProcessor(doAdd, self.language_, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, [], functionNames)
        self.processFile_(originalFileName, myLineProcessor)

    ##
    # @param self The SourceCodeParser instance.
    # @param doAdd If True, we're adding annotations, else we're removing them.
    # @param myFunctionAnnotator Action instance that actually annotates.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFile Result file to add the modified lines.
    # @param headerToInclude Header to include.
    # @param classNames Class names from the file.
    # @param functionNames Function names from the file.
    def processClasses_(self, doAdd, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, classNames, functionNames = []):
        '''
        Add or remove annotations to a source file classes.
        '''
        myLineProcessor = createAnnotateGlobalFunctionsLineProcessor(doAdd, self.language_, myFunctionAnnotator, originalFileName, resultFile, headerToInclude, classNames, functionNames)
        self.processFile_(originalFileName, myLineProcessor)

    ##
    # @param self The SourceCodeParser instance.
    # @param language The program's programming language.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param resultFile Result file to add the modified lines.
    def annotateIncludes_(self, language, originalFileName, resultFile):
        '''
        Add annotation includes to a file.
        '''
        if not self.fileHasIncludes_(originalFileName):
            beginCodeCropper(resultFile)
            resultFile.write(getIncludeAnnotation(language))
            endCodeCropper(resultFile)

    ##
    # @param self The SourceCodeParser instance.
    # @param fileName File where the includes will be removed.
    def removeIncludes_(self, fileName):
        '''
        Remove #includes from a file.
        '''
        annotationsCount = self.countAnnotations_(fileName)
        if annotationsCount == 1:
            resultFileName = fileName + '.incl'
            try:
                with open(resultFileName, 'w' ) as resultFile:
                    myLineProcessor = RemoveIncludesLineProcessor(self.language_, resultFile)
                    self.processFile_(fileName, myLineProcessor)
                shutil.move(resultFileName, fileName)
            except Exception, e:
                raise e
            finally:
                if os.path.exists(resultFileName):
                    os.remove(resultFileName)

    ##
    # @param self The SourceCodeParser instance.
    # @param pythonImport Python import to remove.
    def removePythonImports_(self, pythonImport):
        '''
        Remove a Python from the main file. 
        '''
        importsCount = self.countPythonImportsUse_(pythonImport)
        if importsCount == 0:
            resultFileName = self.mainFilePath_ + '.imp'
            try:
                with open(resultFileName, 'w' ) as resultFile:
                    myLineProcessor = RemovePythonImportLineProcessor(self.language_, resultFile, pythonImport)
                    self.processFile_(self.mainFilePath_, myLineProcessor)
                shutil.move(resultFileName, self.mainFilePath_)
            except Exception, e:
                raise e
            finally:
                if os.path.exists(resultFileName):
                    os.remove(resultFileName)