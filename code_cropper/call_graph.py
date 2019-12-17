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
This is the object-oriented representation in memory to store a Call Graph.
'''

class InvalidParentException(Exception):
    '''
    Exception class for "Invalid parent". For example, an instance's parent should be a class,
    not a module or another instance.
    '''
    ##
    # @param self The InvalidParentException instance to construct.
    # @param parentLanguageType Language Type (see LanguageType class for constants) for the parent.
    # @param childLanguageType Language Type for the child.
    def __init__(self, parentLanguageType, childLanguageType ):
        '''
        Constructor.
        '''
        self.parentLanguageType_ = parentLanguageType
        self.childLanguageType_ = childLanguageType

    ##
    # @param self The InvalidParentException instance.
    def __str__(self):
        '''
        String representation for the exception to be called like this: str(exc).
        '''
        return "'" + LanguageType.asString(self.parentLanguageType_) + "' is not a valid parent language type for '" + LanguageType.asString(self.childLanguageType_) + "'!" 

class LanguageType(object):
    '''
    It represents which language element an object belongs to.
    Python objects do have a hierarchical structure:
        Module 
          |
        Class
          |
        Instance

    LanguageType indicates where the object is located in the hierarchy,
    or a special "None" value (for a "module parent").
    '''
    NONE, MODULE, CLASS, INSTANCE = range(4)

    @staticmethod
    ##
    # @param lt Language Type to query.
    # @return String representation for a LanguageType.
    def asString( lt ):
        '''
        Get string representation for a LanguageType.
        '''
        return { LanguageType.NONE: "None",  LanguageType.MODULE: "Module", LanguageType.CLASS : "Class", LanguageType.INSTANCE : "Instance" } [lt]
    
    @staticmethod
    # @param parentLanguageType Language Type for the parent object.
    # @param childLanguageType Language Type for the child object.
    # @return Whether or not this is a valid parent-child relation.
    def isValidParent(parentLanguageType, childLanguageType):
        '''
        Return whether or not this is a valid parent-child relation.
        For instance, an instance parent and a child module is not valid.
        See the graphic representation for objects hierarchy in this class documentation (LanguageType).
        '''
        assert childLanguageType != LanguageType.NONE
        return (parentLanguageType == LanguageType.NONE and childLanguageType == LanguageType.MODULE) or parentLanguageType == childLanguageType - 1

class LanguageObject(object):
    '''
    KEY CLASS. It represents a Python "object" (it may be a module, class, or instance) whose functions we're annotating.
    EVERY OBJECT is declared as a LanguageObject. For instance, if we find the object "number 5", these are the new LanguageObject's to declare:
    * __builtin__ module.
    * int class.
    * 5.
    '''
    class DECLARATION_TYPES(object):
        '''
        It indicates how to declare the object. It may be:
            * CONSTRUCTOR: object will be declared with a constructor syntax ( var1 = MyClass() )
            * FIXED_VALUE: there's a fixed string representation for the object. For instance, [4, 5] representation is "[4,5]". 
            * DUMMY: As we don't know how to create the object, use a Dummy class.
            * NULL: Object is None.
        '''
        CONSTRUCTOR = 'CONSTRUCTOR'
        FIXED_VALUE = 'FIXED_VALUE'
        DUMMY = 'DUMMY'
        NULL = 'NULL'

    ##
    # @param self The LanguageObject instance to construct.
    # @param id Unique id to identify this Language Object.
    # @param languageType Object's LanguageType.
    # @param declarationType Declaration Type for this object. See DECLARATION_TYPES enum. 
    # @param declarationCode It's a string with the object representation.
    # @param parent Parent Language Object for the new instance.
    def __init__(self, id, languageType, declarationType, declarationCode = None, parent = None):
        '''
        Constructor.
        '''
        assert id > 0
        self.id_ = id
        self.languageType_ = languageType
        self.declarationType_ = declarationType
        self.declarationCode_ = declarationCode
        self.parent_ = parent
        parentLanguageType = parent.languageType_ if parent else LanguageType.NONE
        if not LanguageType.isValidParent(parentLanguageType, languageType):
            raise InvalidParentException(parentLanguageType, languageType)

    ##
    # @param self The LanguageObject instance.
    # @return The unique id to identify this Language Object.
    def getId(self):
        '''
        Get the unique id to identify this Language Object.
        '''
        return self.id_

    ##
    # @param self The LanguageObject instance.
    # @return The object's LanguageType.
    def getLanguageType(self):
        '''
        Get the object's LanguageType.
        '''        
        return self.languageType_
 
    ##
    # @param self The LanguageObject instance.
    # @return This object's Declaration Type.
    def getDeclarationType(self):
        '''
        Get this object's Declaration Type. See DECLARATION_TYPES enum.
        '''
        return self.declarationType_

    ##
    # @param self The LanguageObject instance.
    # @return A string with the object representation.
    def getDeclarationCode(self):
        '''
        Get a string with the object representation.
        '''
        return self.declarationCode_

    ##
    # @param self The LanguageObject instance.
    # @return The parent Language Object.
    def getParent(self):
        '''
        Get the parent Language Object.
        '''
        return self.parent_

class Argument(object):
    '''
    Represents a function argument.
    '''
    class ArgumentType(object):
        '''
        Type of argument.
        '''
        VALUE, POINTER, REFERENCE = range(3)
    
    ##
    # @param self The Argument instance to construct.
    # @param aLanguageObject Language Object representing the argument.
    # @param name Argument name for named arguments, None for the most common unnamed arguments.
    # @param argType Argument type (see ArgumentType for the values).
    # @param isConst It's a const argument (for C++ only).
    def __init__(self, aLanguageObject, name = None, argType = ArgumentType.VALUE, isConst = False):
        '''
        Constructor.
        '''
        assert aLanguageObject
        self.languageObject_ = aLanguageObject
        self.argType_ = argType
        self.isConst_ = isConst
        self.name_ = name
        
    ##
    # @param self The Argument instance.
    # @return The Language Object representing the argument.
    def getLanguageObject(self):
        '''
        Get the Language Object representing the argument.
        '''
        return self.languageObject_
    
    ##
    # @param self The Argument instance.
    # @return The argument name, if it's a named argument. Else, return None.
    def getName(self):
        '''
        Get the optional argument name.
        '''
        return self.name_
    
    ##
    # @param self The Argument instance.
    # @return The argument type (see ArgumentType for the values).
    def getArgumentType(self):
        '''
        Get the argument type (see ArgumentType for the values).
        '''
        return self.argType_

    ##
    # @param self The Argument instance.
    # @return Whether or not it's a const argument (for C++ only).
    def isConst(self):
        '''
        Tell whether or not it's a const argument (for C++ only).
        '''
        return self.isConst_

class FunctionCall(object):
    '''
    Class that represents a Function Call in the original program.
    '''
    class MethodType(object):
        '''
        'code_cropper' method type for a function.
        Some of these constants come from "inspect" module
        '''
        CLASS_METHOD = 'class method'   #created via classmethod()
        STATIC_METHOD = 'static method' #created via staticmethod()
        PROPERTY = 'property'           #created via property()
        CONSTRUCTOR = 'constructor'     #created via property()
        DESTRUCTOR = 'destructor'       #C++ destructor
        METHOD = 'method'               #any other flavor of method

    ##
    # @param self The FunctionCall instance to construct.
    # @param id Unique id to identify this FunctionCall instance.
    # @param callee The callee, i.e.: the receiver of the message (the function call).
    # @param functionName Function name.
    # @param methodType This function's method type (see MethodType for the values).
    # @param argsList List of argument objects (see Argument class).
    # @param level The function nesting level (it starts with 0, and increases going deep).
    # @param returnedObject If threwException is False, the object returned by the function. If True, the exception being raised.
    # @param threwException The function has raised an exception.
    # @param totalTime Time taken by the function (this may be used for profiling).
    def __init__(self, id, callee, functionName, methodType, argsList, level, returnedObject = None, threwException = False, totalTime = None):
        '''
        Constructor.
        '''
        self.id_ = id
        self.callee_ = callee
        self.functionName_ = functionName
        self.methodType_ = methodType
        self.argsList_ = argsList
        self.level_ = level
        self.returnedObject_ = returnedObject
        self.threwException_ = threwException
        self.totalTime_ = totalTime

    # @param self The FunctionCall instance.
    # @return The unique id to identify this FunctionCall instance.
    def getId(self):
        '''
        Get the unique id to identify this FunctionCall instance.
        '''
        return self.id_

    ##
    # @param self The FunctionCall instance.
    # @return The callee, i.e.: the receiver of the message (the function call).
    def getCallee(self):
        '''
        Get the receiver of the message (the function call).
        '''
        return self.callee_

    ##
    # @param self The FunctionCall instance.
    # @return The function name.
    def getFunctionName(self):
        '''
        Get the function name.
        '''
        return self.functionName_

    ##
    # @param self The FunctionCall instance.
    # @return This function's method type (see MethodType for the values).
    def getMethodType(self):
        '''
        Get this function's method type (see MethodType for the values).
        '''
        return self.methodType_

    ##
    # @param self The FunctionCall instance.
    # @return The list of argument objects (see Argument class) for this function.
    def getArgsList(self):
        '''
        Get the list of argument objects (see Argument class) for this function.
        '''
        return self.argsList_

    ##
    # @param self The FunctionCall instance.
    # @return The function nesting level (it starts with 0, and increases going deep).
    def getLevel(self):
        '''
        Get the function nesting level (it starts with 0, and increases going deep).
        '''
        return self.level_

    ##
    # @param self The FunctionCall instance.
    # @return If no exception has been thrown, the object returned by the function. Else, the exception being raised.
    def getReturnedObject(self):
        '''
        Get the object returned by the function (or a possible exception raised).
        '''
        return self.returnedObject_

    ##
    # @param self The FunctionCall instance.
    # @param returnedObject If no exception has been thrown, the object returned by the function. Else, the exception being raised.
    def setReturnedObject(self, returnedObject):
        '''
        Set the object returned by the function (or a possible exception raised).
        '''
        self.returnedObject_ = returnedObject

    ##
    # @param self The FunctionCall instance.
    # @return Whether or not the function has raised an exception.
    def threwException(self):
        '''
        Return whether or not the function has raised an exception.
        '''
        return self.threwException_ 

    ##
    # @param self The FunctionCall instance.
    # @param threwException The function has raised an exception.
    def setThrewException(self, threwException):
        '''
        Set whether or not the function has raised an exception.
        '''
        self.threwException_ = threwException

    ##
    # @param self The FunctionCall instance.
    # @return The time taken by the function (this may be used for profiling).
    def getTotalTime(self):
        '''
        Get the time taken by the function (this may be used for profiling).
        '''
        return self.totalTime_
    
class DuplicatedLanguageObjectIdException(Exception):
    '''
    Exception class for "Duplicated LanguageObject id". It is raised
    when there's an attempt to create a LanguageObject with an already-used id.
    '''
    ##
    # @param self The DuplicatedLanguageObjectIdException instance to construct.
    # @param id The duplicated id to report.
    def __init__(self, id):
        '''
        Constructor.
        '''
        self.id_ = id

    ##
    # @param self The DuplicatedLanguageObjectIdException instance.
    def __str__(self):
        '''
        String representation for the exception to be called like this: str(exc).
        '''
        return "Duplicated LanguageObject id: " + str(self.id_) 

class ProgramExecution(object):
    '''
    It represents a program execution, i.e.: the call graph and all the objects being used
    in the functions.
    '''
    MIN_LEVEL = 0
    class Languages(object):
        '''
        Languages supported by "Code Cropper".
        '''
        PYTHON = 'Python'
        C_PLUS_PLUS = 'C++'

    ##
    # @param self The ProgramExecution instance to construct.
    # @param language The program's programming language.
    def __init__(self, language):
        '''
        Constructor.
        '''
        assert language in (ProgramExecution.Languages.PYTHON, ProgramExecution.Languages.C_PLUS_PLUS)
        self.language_ = language
        LT = LanguageType
        self.languageTypes_ = [ LT.NONE, LT.MODULE, LT.CLASS, LT.INSTANCE ]
        self.languageObjects_ = {}
        self.functionCalls_ = []

    ##
    # @param self The ProgramExecution instance.
    # @return The program's programming language.
    def getLanguage(self):
        '''
        Return the program's programming language.
        '''
        return self.language_
    
    
    ##
    # @param self The ProgramExecution instance.
    # @return A list of all available LanguageType's (see LanguageType).
    def getLanguageTypes(self):
        '''
        Get the list of all available LanguageType's (see LanguageType).
        '''
        return self.languageTypes_

    ##
    # @param self The ProgramExecution instance.
    # @param aLanguageObject The LanguageObject instance to add to the container.
    def addLanguageObject(self, aLanguageObject):
        '''
        Add a LanguageObject instance to an internal container.
        '''
        id = aLanguageObject.getId()
        if self.languageObjects_.has_key(id):
            raise DuplicatedLanguageObjectIdException(id)
        parent = aLanguageObject.getParent() 
        assert parent is None or self.languageObjects_.has_key(parent.getId())
        self.languageObjects_[id] = aLanguageObject

    ##
    # @param self The ProgramExecution instance.
    # @return The internal LanguageObject container.
    def getLanguageObjects(self):
        '''
        Get the internal LanguageObject container.
        '''
        return self.languageObjects_

    ##
    # @param self The ProgramExecution instance.
    # @param aFunctionCall A FunctionCall instance.
    def addFunctionCall(self, aFunctionCall):
        '''
        Add a new function call to an internal container.
        '''
        self.functionCalls_.append(aFunctionCall)

    ##
    # @param self The ProgramExecution instance.
    # @return The internal FunctionCall container.
    def getFunctionCalls(self):
        '''
        Get the internal FunctionCall container.
        '''
        return self.functionCalls_ 
