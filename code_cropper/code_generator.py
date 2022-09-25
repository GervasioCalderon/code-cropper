# This file is part of Code Cropper
# The tool has been designed and developed by Eng. Gervasio Calderon
# 
# Copyright (c) 2019, Core Security Technologies
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
"""
Module to generate source code (a main program or a unit test) from
a call graph.
"""
import types
from .call_graph import FunctionCall, LanguageObject, LanguageType, ProgramExecution
from .python_language import PythonConstants
from .serialization import fromJsonString, CallGraphSerializer


class AuxiliarClassForDummy:
    """
    A wrapper for a class, to have a "Dummy" object.
    """
    ##
    # @param self The AuxiliarClassForDummy instance to construct.
    # @param classString String representation for the class.
    def __init__(self, classString):
        """
        Constructor.
        """
        self.classString_ = classString

    ##
    # @param self The AuxiliarClassForDummy instance.
    # @return The class string representation.     
    def getClassString(self):
        """
        Return the class string representation.
        """
        return self.classString_
    
##
# @param obj The AuxiliarClassForDummy instance.
# @return The class (as a string) for an object, or the wrapped class for an AuxiliarClassForDummy instance.
def getClassStringForDummy(obj):
    """
    Get the class (as a string) for an object, or the wrapped class for an AuxiliarClassForDummy instance.
    """
    return obj.getClassString() if isinstance(obj, AuxiliarClassForDummy) else obj.__class__

class GeneratedSourceType:
    """
    Type of result source file to generate.
    """
    MAIN_FILE, MAIN_FILE_WITH_ASSERTS, UNIT_TEST = range(3) 

class TokensGenerator:
    """
    Get source code tokens from a ProgramExecution.
    Abstract interface: implement one per language.
    """
    INSTANCE_NAME_PREFIX = "var"
    MODULE_NAME_PREFIX = "mod"
    CLASS_NAME_PREFIX = "cls"
    MAX_LENGTH_FOR_NOT_DECLARING = 50

    class VariableInfo:
        """
        Information for the variables.
        """
        ##
        # @param self The VariableInfo instance to construct.
        # @param varName Variable name.
        # @param declarationType The variable declaration type (see LanguageObject.DECLARATION_TYPES).
        # @param useVarNameForRepr If true, use the name to refer to the variable. Else (for instance: basic types), use a string representation.
        # @param pythonObject Python object representation.
        def __init__(self, varName, declarationType, useVarNameForRepr, pythonObject = None):
            """
            Constructor.
            """
            self.varName_ = varName
            self.declarationType_ = declarationType
            self.useVarNameForRepr_ = useVarNameForRepr
            self.pythonObject_ = pythonObject
        
        ##
        # @param self The VariableInfo instance.
        # @return The variable name.
        def getVarName(self):
            """
            Get variable name.
            """
            return self.varName_
        
        ##
        # @param self The VariableInfo instance.
        # @return The variable declaration type.
        def getDeclarationType(self):
            """
            Get the variable declaration type (see LanguageObject.DECLARATION_TYPES).
            """
            return self.declarationType_
        
        ##
        # @param self The VariableInfo instance.
        # @return Whether or not we use the name to refer to the variable.
        def useVarNameForRepr(self):
            """
            Tell whether or not we use the name to refer to the variable.
            """
            return self.useVarNameForRepr_

        ##
        # @param self The VariableInfo instance
        # @return Python object representation.
        def getPythonObject(self):
            """
            Get Python object representation.
            """
            return self.pythonObject_

    ##
    # @param self The TokensGenerator to construct.
    # @param aProgramExecution Program execution call graph.
    # @param sourceType Kind of source to generate (see GeneratedSourceType).
    # @param projectName Code Cropper project name.
    def __init__(self, aProgramExecution, sourceType, projectName = None):
        """
        Constructor.
        """
        self.idsToVariableInfo_ = {}
        self.indentation_ = ""
        self.initSpaces_ = ""
        self.programExecution_ = aProgramExecution
        self.sourceType_ = sourceType
        self.projectName_ = projectName

    ##
    # @param self The TokensGenerator instance.
    # @param str A Json string.
    # @return A Python object from its Json string representation.
    def fromJsonString_(self, str):
        """
        Get a Python object from its Json string representation.
        """
        return fromJsonString(str)

    ##
    # @param self The TokensGenerator instance.
    # @param aLanguageObject Language object to search.
    # @return The variable info correspondent to a LanguageObject.
    def getVariableInfo(self, aLanguageObject):
        """
        Get the variable info correspondent to a LanguageObject.
        """
        assert self.languageObjectIsDeclared(aLanguageObject)
        return self.idsToVariableInfo_[aLanguageObject.getId()]

    ##
    # @param self The TokensGenerator instance.
    # @return Code to insert at the beginning of the generated file's main function.
    def beginMain(self):
        """
        Return code to insert at the beginning of the generated file's main function.
        """
        return ""

    ##
    # @param self The TokensGenerator instance.
    # @return Code to insert at the end of the generated file's main function.
    def endMain(self):
        """
        Return code to insert at the end of the generated file's main function.
        """
        return ""

    ##
    # @param self The TokensGenerator instance.
    # @return One indentation string, according to the language state of art.
    def getOneIndentation_(self):
        """
        Get one indentation string, according to the language state of art.
        """
        return "\t"

    ##
    # @param self The TokensGenerator instance.
    # @param level The function nesting level (it starts with 0, and increases going deep).
    def newFunctionLevel(self, level):
        """
        A new function nesting level has been reached.
        This modifies the indentation for the ALL_LEVELS code generation.
        """
        self.indentation_ = self.getInitialSpaces() + self.getOneIndentation_() * level

    ##
    # @param self The TokensGenerator instance.
    # @return Initial spaces to insert in the current line.
    def getInitialSpaces(self):
        """
        Get initial spaces to insert in the current line.
        """
        return self.initSpaces_

    ##
    # @param self The TokensGenerator instance.
    # @return Code to insert at the beginning of the generated file.
    def initialFileCode(self):
        """
        Return code to insert at the beginning of the generated file.
        """
        return ""

    ##
    # @param self The TokensGenerator instance.
    # @return Code to insert at the end of the generated file.
    def finalFileCode(self):
        """
        Return code to insert at the end of the generated file.
        """
        return ""

    ##
    # @param self The TokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @return Whether or not the LanguageObject is already declared.
    def languageObjectIsDeclared(self, aLanguageObject):
        """
        Is the LanguageObject already declared?
        """
        return aLanguageObject.getId() in self.idsToVariableInfo_

    ##
    # @param self The TokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @return Declaration code for an object, or "" if declared before.
    def declareLanguageObject(self, aLanguageObject):
        """
        Public declaration methods. VIRTUAL METHOD PATTERN: implement details in derivatives.
        Return the declaration code if the object needs to be declared,
        or an empty string otherwise.
        """
        declaration = ""
        if not aLanguageObject.getId() in self.idsToVariableInfo_:
            myLanguageType = aLanguageObject.getLanguageType()
            if myLanguageType == LanguageType.MODULE:
                varInfo = self._calculateModuleVariableInfo(aLanguageObject)
                declaration = self._declareModule(varInfo)
            elif myLanguageType == LanguageType.CLASS:
                varInfo = self._calculateClassVariableInfo(aLanguageObject)
                declaration = self._declareClass(varInfo)
            else:
                assert myLanguageType == LanguageType.INSTANCE
                varInfo = self._calculateInstanceVariableInfo(aLanguageObject)
                myType = eval(self.getObjectRepresentation(aLanguageObject.getParent()))
                declaration = self._declareInstance(varInfo, myType)
            self.idsToVariableInfo_[aLanguageObject.getId()] = varInfo
        return declaration

    ##
    # @param self The TokensGenerator instance.
    # @myObj A Python object.
    # @return Whether or not we'll use name to refer to the variable
    def _mustUseVarNameForRepr(self, myObj):
        """
        Tell whether or not we'll use name to refer to the variable. Else (for instance: basic types), use a string representation.
        """
        raise NotImplementedError("Should have implemented this")

    ##
    # @param self The TokensGenerator instance.
    # @param myObj A Python object.
    # @return Declaration code for this object.
    def _getDeclarationCodeFromObject(self, myObj):
        """
        Get the declaration code for this object.
        """
        raise NotImplementedError("Should have implemented this")

    ##
    # @param self The TokensGenerator instance.
    # @param moduleObject A Module object.
    # @return The VariableInfo for this module.
    def _calculateModuleVariableInfo(self, moduleObject):
        """
        Create the VariableInfo for this module.
        """
        assert moduleObject.getLanguageType() == LanguageType.MODULE
        assert moduleObject.getDeclarationType() == LanguageObject.DECLARATION_TYPES.FIXED_VALUE
        modName = TokensGenerator.MODULE_NAME_PREFIX + str(self.nextModuleIndex_)
        self.nextModuleIndex_ += 1
        pythonObj = self.fromJsonString_(moduleObject.getDeclarationCode())
        return TokensGenerator.VariableInfo(modName, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, False, pythonObj)
 
    ##
    # @param self The TokensGenerator instance.
    # @param classObject A Class object.
    # @return The VariableInfo for this class.
    def _calculateClassVariableInfo(self, classObject):
        """
        Create the VariableInfo for this class.
        """  
        assert classObject.getLanguageType() == LanguageType.CLASS
        assert classObject.getDeclarationType() == LanguageObject.DECLARATION_TYPES.FIXED_VALUE
        className = TokensGenerator.CLASS_NAME_PREFIX + str(self.nextClassIndex_)
        self.nextClassIndex_ += 1
        pythonObj = self.fromJsonString_(classObject.getDeclarationCode())
        declarationCodeStr = self._getDeclarationCodeFromObject(pythonObj) 
        return TokensGenerator.VariableInfo(className, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, False, pythonObj)

    ##
    # @param self The TokensGenerator instance.
    # @param instanceObject Instance object.
    # @return The VariableInfo for this instance.
    def _calculateInstanceVariableInfo(self, instanceObject):
        """
        Create the VariableInfo for this instance.
        """
        assert instanceObject.getLanguageType() == LanguageType.INSTANCE
        instanceName = TokensGenerator.INSTANCE_NAME_PREFIX + str(self.nextInstanceIndex_)
        self.nextInstanceIndex_ += 1
        
        DT = LanguageObject.DECLARATION_TYPES
        myLanguageType = instanceObject.getLanguageType()
        declarationType = instanceObject.getDeclarationType()
        jsonDeclarationCode = instanceObject.getDeclarationCode()
        pythonObj = self.fromJsonString_(jsonDeclarationCode)
        
        useVarNameForRepr = False
        
        if declarationType == DT.CONSTRUCTOR:
            useVarNameForRepr = True
        elif declarationType == DT.FIXED_VALUE:
            pythonObj = self.fromJsonString_(jsonDeclarationCode)
            useVarNameForRepr = self._mustUseVarNameForRepr(pythonObj)
        elif declarationType == DT.DUMMY:
            parentClass = instanceObject.getParent()
            assert parentClass.getLanguageType() == LanguageType.CLASS
            parentClassStr = eval(self.getObjectRepresentation(parentClass))
            pythonObj = AuxiliarClassForDummy(parentClassStr)
            declarationType = DT.FIXED_VALUE
            useVarNameForRepr = False
        
        return TokensGenerator.VariableInfo(instanceName, declarationType, useVarNameForRepr, pythonObj)

       
    #Abstract declaration methods

    ##
    # @param self The TokensGenerator instance.
    # @param moduleInfo Module information (see VariableInfo).
    # @return The module declaration code, or an empty string if the class is already declared.
    def _declareModule(self, moduleInfo):
        """
        Declare a module, if not declared before.
        """
        raise NotImplementedError("Should have implemented this")
    
    ##
    # @param self The TokensGenerator instance.
    # @param classInfo Class information (see VariableInfo).
    # @return The class declaration code, or an empty string if the class is already declared.
    def _declareClass(self, classInfo):
        """
        Declare a class, if not declared before.
        """
        raise NotImplementedError("Should have implemented this")
    
    ##
    # @param self The TokensGenerator instance.
    # @param instanceInfo Instance information (see VariableInfo).
    # @param myType Type of the instance to declare.
    # @return The instance declaration code, or an empty string if the class is already declared.
    def _declareInstance(self, instanceInfo, myType = ""):
        """
        Declare an instance, if not declared before.
        """
        raise NotImplementedError("Should have implemented this")

    ##
    # @param self The TokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @param firstCall First FunctionCall for this object.
    # @return Whether or not an object must be created with the default constructor.
    def mustDefaultConstruct(self, aLanguageObject, firstCall):
        """
        Tell whether or not an object must be created with the default constructor.
        """
        raise NotImplementedError("Should have implemented this")

    ##
    # @param self The TokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    def defaultConstruct(self, aLanguageObject):
        """
        Call the object's default constructor.
        """
        raise NotImplementedError("Should have implemented this")

    ##
    # @param self The TokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @param aCall A FunctionCall.
    # @return Whether or not the method is a constructor.
    def methodIsConstructor(self, aLanguageObject, aCall):
        """
        Tell whether or not the method is a constructor.
        """
        raise NotImplementedError("Should have implemented this")

    ##
    # @param self The TokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @return Variable name or a fixed value, depending on the object declaration type.
    def getObjectRepresentation(self, aLanguageObject):
        """
        Return Variable name or a fixed value, depending on the object declaration type.
        """
        assert aLanguageObject.getId() in self.idsToVariableInfo_
        varInfo = self.idsToVariableInfo_[aLanguageObject.getId()]
        if varInfo.useVarNameForRepr():
            return varInfo.getVarName()
        else:
            return self._getDeclarationCodeFromObject(varInfo.getPythonObject())

    ##
    # @param self The TokensGenerator instance.
    # @param returnedObject If threwException is False, the object returned by the function. If True, the exception being raised.
    # @param threwException The function has raised an exception.
    def returnedObjectFunctionPrefix(self, returnedObject, threwException):
        """
        In Unit Tests, initial code for a line that checks the function return value.
        """
        return ''

    ##
    # @param self The TokensGenerator instance.
    # @param returnedObject If threwException is False, the object returned by the function. If True, the exception being raised.
    # @param threwException The function has raised an exception.
    def returnedObjectFunctionPosfix(self, returnedObject, threwException):
        """
        In Unit Tests, final code for a line that checks the function return value.
        """
        return ''

    ##
    # @param self The PythonTokensGenerator instance.
    # @param aFunctionCall A FunctionCall.
    # @return Code for this function call, to be inserted in the generated source file.
    def methodCall(self, aFunctionCall):
        """
        Return code for this function call, to be inserted in the generated source file.
        """
        raise NotImplementedError("Should have implemented this")

    ##
    # @param self The TokensGenerator instance.
    # @param aFunctionCall A FunctionCall.
    # @param arg An Argument.
    # @param argCount Order in the arguments list for "arg".
    # @return If this argument must be skipped (for instance: "self" implicit argument in Python).
    def mustSkipArgument(self, aFunctionCall, arg, argCount):
        """
        Tell if this argument must be skipped (for instance: "self" implicit argument in Python).
        """
        raise NotImplementedError("Should have implemented this")
        
    ##
    # @param self The PythonTokensGenerator instance.
    # @return The Dummy class declaration code.
    def declareDummyClass(self):
        """
        Declare Dummy class.
        Return its declaration code.
        """
        raise NotImplementedError("Should have implemented this")

    ##
    # @param self The PythonTokensGenerator instance.
    # @return The Json module declaration code.
    def declareJsonModule(self):
        """
        Declare Json Module (simplejson library).
        """
        raise NotImplementedError("Should have implemented this")
    
    ##
    # @param self The TokensGenerator instance.
    # @return The arguments list begin mark.
    def argumentsListBegin(self):
        """
        Get the arguments list begin mark.
        """
        return "("

    ##
    # @param self The TokensGenerator instance.
    # @return The arguments list separator (',').
    def argumentsListSeparator(self):
        """
        Get the arguments list separator (',').
        """
        return ", "

    ##
    # @param self The TokensGenerator instance.
    # @return The arguments list end mark.
    def argumentsListEnd(self):
        """
        Get the arguments list end mark.
        """
        return ")"

    ##
    # @param self The TokensGenerator instance.
    # @return the sentence ending.
    def endSentence(self):
        """
        Abstract method.
        Return the sentence ending (";" for C++, for example).
        """
        raise NotImplementedError("Should have implemented this")

class PythonTokensGenerator(TokensGenerator):
    """
    Code generator for Python source files.
    """
    INSTANCE_NAME_PREFIX = "var"
    MODULE_NAME_PREFIX = "mod"
    CLASS_NAME_PREFIX = "cls"
    SPACES_PER_TAB = 4
    MAX_LENGTH_FOR_NOT_DECLARING = 50

    ##
    # @param self The PythonTokensGenerator to construct.
    # @param aProgramExecution Program execution call graph.
    # @param sourceType Kind of source to generate (see GeneratedSourceType).
    # @param projectName Code Cropper project name.
    def __init__(self, aProgramExecution, sourceType, projectName):
        """
        Constructor.
        """
        TokensGenerator.__init__(self, aProgramExecution, sourceType, projectName)
        self.nextModuleIndex_ = 0
        self.nextClassIndex_ = 0
        self.nextInstanceIndex_ = 0

    ##
    # @param self The PythonTokensGenerator instance.
    # @param str A Json string.
    # @return a Python object from its Json string representation.
    def fromJsonString_(self, str):
        """
        Get a Python object from its Json string representation.
        """
        obj = TokensGenerator.fromJsonString_(self, str)
        #Fix bug in Json: for maps, keys are translated into strings
        if isinstance(obj, dict):
            newDict = {}
            for key, value in obj.items():
                newKey = int(key)
                newDict[newKey] = value
            return newDict
        return obj

    ##
    # @param self The PythonTokensGenerator instance.
    # @return One Python indentation string.
    def getOneIndentation_(self):
        """
        Get one Python indentation string.
        """
        return " " * PythonTokensGenerator.SPACES_PER_TAB
    
    ##
    # @param self The PythonTokensGenerator instance.
    # @return Code to insert at the beginning of the generated file.
    def initialFileCode(self):
        """
        Return code to insert at the beginning of the generated file.
        """
        if self.sourceType_ == GeneratedSourceType.UNIT_TEST:
            return "import unittest\n"
        return ""

    ##
    # @param self The PythonTokensGenerator instance.
    # @return Code to insert at the end of the generated file.
    def finalFileCode(self):
        """
        Return code to insert at the end of the generated file.
        """
        if self.sourceType_ == GeneratedSourceType.UNIT_TEST:
            return """
if __name__ == '__main__':
    unittest.main()"""
        return ""

    ##
    # @param self The PythonTokensGenerator instance.
    # @return Code to insert at the beginning of the generated file's main function.
    def beginMain(self):
        """
        Return code to insert at the beginning of the generated file's main function.
        """
        if self.sourceType_ == GeneratedSourceType.UNIT_TEST:
            self.initSpaces_ = self.getOneIndentation_() * 2
            self.indentation_ = self.initSpaces_
            testCaseName = self.projectName_.replace(' ', '_') + 'Test' if self.projectName_ else "UNIT_TEST_CASE"
            return """class %s(unittest.TestCase):
    def test_main(self):
""" % testCaseName
        return ""

    ##
    # @param self The TokensGenerator instance.
    # @param moduleInfo Module information (see VariableInfo)
    # @return The module declaration code, or an empty string if the class is already declared.
    def _declareModule(self, moduleInfo):
        """
        Declare a module, if not declared before.
        """
        moduleNameStr = self._getDeclarationCodeFromObject(moduleInfo.getPythonObject())
        moduleName = eval(moduleNameStr)
        if moduleName in PythonConstants.BUILTINS_MODULE_NAMES:
            return "" 
        else:
            alias = " as " + moduleInfo.getVarName() if moduleInfo.useVarNameForRepr() else ""
            return self.indentation_ + "import " + moduleName + alias + "\n"

    ##
    # @param self The TokensGenerator instance.
    # @param classInfo Class information (see VariableInfo).    
    # @return The class declaration code, or an empty string if the class is already declared.
    def _declareClass(self, classInfo):
        """
        Declare a class, if not declared before.
        """
        return "" if not classInfo.useVarNameForRepr() else self.indentation_ + classInfo.getVarName() + " = " + self._getDeclarationCodeFromObject(classInfo.getPythonObject()) + "\n"

    ##
    # @param self The PythonTokensGenerator instance.
    # @myObj A Python object.
    # @return Whether or not we'll use name to refer to the variable.
    def _mustUseVarNameForRepr(self, myObj):
        """
        Tell whether or not we'll use name to refer to the variable. Else (for instance: basic types), use a string representation.
        """
        objType = type(myObj)
        if myObj is None:
            return False
        if isinstance(myObj, bool):
            return False
        if isinstance(myObj, (bool, int, float,)):
            return False
        if isinstance(myObj, str):
            return len(myObj) > PythonTokensGenerator.MAX_LENGTH_FOR_NOT_DECLARING
        if isinstance(myObj, (list, dict,)):
            #This is mandatory, since their construction is not trivial
            return True
        return False

    ##
    # @param self The PythonTokensGenerator instance.
    # @param myObj A Python object.
    # @return Declaration code for this object.
    def _getDeclarationCodeFromObject(self, myObj):
        """
        Get the declaration code for this object.
        """
        if myObj is None:
            return 'None'
        if isinstance(myObj, bool):
            return 'True' if myObj else 'False'
        if isinstance(myObj, (int, float, str,)):
            return repr(myObj)
        return "dummy.Dummy('" + getClassStringForDummy(myObj) + "')"

    ##
    # @param self The PythonTokensGenerator instance.
    # @param instanceInfo Instance information (see VariableInfo).
    # @param myType Type of the instance to declare.
    # @return The instance declaration code, or an empty string if the instance is already declared.
    def _declareInstance(self, instanceInfo, myType = ""):
        """
        Declare an instance, if not declared before.
        """
        mustDeclare = instanceInfo.getDeclarationType() != LanguageObject.DECLARATION_TYPES.CONSTRUCTOR and instanceInfo.useVarNameForRepr()
        if mustDeclare:
            myObj = instanceInfo.getPythonObject()
            #Tuples are translated to lists
            if isinstance(myObj, list):
                declCode = self.indentation_ + instanceInfo.getVarName() + " = ["
                childrenDeclCode = ""
                for id in myObj:
                    childLo = self.programExecution_.getLanguageObjects()[id]
                    childrenDeclCode += self.declareLanguageObject(childLo)  
                    childDecl = self.getObjectRepresentation(childLo)
                    declCode += childDecl + ", "
                if myObj:
                    declCode = declCode[:-2]
                declCode += "]\n"
                return childrenDeclCode + declCode
            if isinstance(myObj, dict):
                declCode = self.indentation_ + instanceInfo.getVarName() + " = {}\n"
                childrenDeclCode = ""
                for key, value in myObj.items():
                    keyLo = self.programExecution_.getLanguageObjects()[key]
                    valueLo = self.programExecution_.getLanguageObjects()[value]
                    childrenDeclCode += self.declareLanguageObject(keyLo)
                    childrenDeclCode += self.declareLanguageObject(valueLo)
                    keyDecl = self.getObjectRepresentation(keyLo)
                    valueDecl = self.getObjectRepresentation(valueLo)
                    declCode += self.indentation_ + instanceInfo.getVarName() + "[" + keyDecl + "] = " + valueDecl + "\n"
                return childrenDeclCode + declCode
            if objType is types.InstanceType:
                return self.indentation_ + instanceInfo.getVarName() + ' = dummy.Dummy' +  '("' + getClassStringForDummy(myObj) + '")\n'
            return self.indentation_ + instanceInfo.getVarName() + " = " + self._getDeclarationCodeFromObject(instanceInfo.getPythonObject()) + "\n"
        else:
            return ""

    ##
    # @param self The PythonTokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @param firstCall First FunctionCall for this object.
    # @return Whether or not an object must be created with the default constructor.
    def mustDefaultConstruct(self, aLanguageObject, firstCall):
        """
        Tell whether or not an object must be created with the default constructor 
        """
        if aLanguageObject.getLanguageType() == LanguageType.INSTANCE:
            #Object that don't call methods are not constructed
            if firstCall.getMethodType() != FunctionCall.MethodType.CONSTRUCTOR:
                #If first function is not __init__, call default constructor
                #Maybe an object already created is being annotated, or maybe there's no __init__
                return True
        return False

    ##
    # @param self The PythonTokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    def defaultConstruct(self, aLanguageObject):
        """
        Call the object's default constructor.
        """
        assert self.languageObjectIsDeclared(aLanguageObject)
        varInfo = self.getVariableInfo(aLanguageObject)
        parentClass = aLanguageObject.getParent()
        assert parentClass.getLanguageType() == LanguageType.CLASS
        return self.indentation_ + varInfo.getVarName() + " = " + eval(self.getObjectRepresentation(parentClass)) + "()\n"

    ##
    # @param self The PythonTokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @param aCall A FunctionCall
    # @return Whether or not the method is a constructor.
    def methodIsConstructor(self, aLanguageObject, aCall):
        """
        Tell whether or not the method is a constructor (__init__).
        """
        return aLanguageObject.getLanguageType() == LanguageType.INSTANCE and aCall.getFunctionName() ==  PythonConstants.CONSTRUCTOR_SIGNATURE

    ##
    # @param self The PythonTokensGenerator instance.
    # @param returnedObject If threwException is False, the object returned by the function. If True, the exception being raised.
    # @param threwException The function has raised an exception.
    def returnedObjectFunctionPrefix(self, returnedObject, threwException):
        """
        In Unit Tests, initial code for a line that checks the function return value.
        """
        if self.sourceType_ == GeneratedSourceType.UNIT_TEST:
            functionPrefix = "self.assert"
            if threwException:
                functionPrefix += "Raises("
                exceptionClass = returnedObject.getParent()
                representation = self.getObjectRepresentation(exceptionClass)
                #Remove quotes
                if representation.startswith("u'") or representation.startswith('u"'):
                    representation = representation[1:] 
                representation = representation.replace('"', '')
                representation = representation.replace('"', '')
                representation = representation.replace("'", '')
                functionPrefix += representation
            else:
                functionPrefix += "Equal("
                functionPrefix += self.getObjectRepresentation(returnedObject)
            functionPrefix += ", "
        else:
            functionPrefix = ""
        return self.initSpaces_ + functionPrefix 

    ##
    # @param self The PythonTokensGenerator instance.
    # @param returnedObject If threwException is False, the object returned by the function. If True, the exception being raised.
    # @param threwException The function has raised an exception.
    def returnedObjectFunctionPosfix(self, returnedObject, threwException):
        """
        In Unit Tests, final code for a line that checks the function return value.
        """
        return ")" if self.sourceType_ == GeneratedSourceType.UNIT_TEST else ""
    
    ##
    # @param self The PythonTokensGenerator instance.
    # @param aFunctionCall A FunctionCall.
    # @return Code for this function call, to be inserted in the generated source file.
    def methodCall(self, aFunctionCall):
        """
        Return code for this function call, to be inserted in the generated source file.
        """
        calleeObject = aFunctionCall.getCallee()
        calleeLanguageType = calleeObject.getLanguageType()
        
        calleeRepresentation = self.getObjectRepresentation(calleeObject)
        if calleeLanguageType in (LanguageType.MODULE, LanguageType.CLASS):
            calleeRepresentation = eval(calleeRepresentation)
            calleePrefix = ""
            #Built in classes do not need module qualification
            if calleeLanguageType == LanguageType.CLASS or calleeRepresentation not in PythonConstants.BUILTINS_MODULE_NAMES:
                calleePrefix = calleeRepresentation + "."
            return self.indentation_ + calleePrefix + aFunctionCall.getFunctionName()
        
        assert calleeLanguageType == LanguageType.INSTANCE
        methodCallStr = calleeRepresentation
        #Constructor is a special case, call Class name
        if aFunctionCall.getMethodType() == FunctionCall.MethodType.CONSTRUCTOR:
            classObject = calleeObject.getParent()
            assert classObject.getLanguageType() == LanguageType.CLASS
            className = eval(self.getObjectRepresentation(classObject)) 
            methodCallStr += " = " + className
        else:
            methodCallStr += "." + aFunctionCall.getFunctionName()
        return self.indentation_ + methodCallStr

    ##
    # @param self The PythonTokensGenerator instance.
    # @param aFunctionCall A FunctionCall.
    # @param arg An Argument.
    # @param argCount Order in the arguments list for "arg".
    # @return If this argument must be skipped (for instance: "self" implicit argument in Python).
    def mustSkipArgument(self, aFunctionCall, arg, argCount):
        """
        Tell if this argument must be skipped (for instance: "self" implicit argument in Python).
        """
        calleeObject = aFunctionCall.getCallee()
        calleeLanguageType = calleeObject.getLanguageType()
        
        #Skip "self" in instance methods or "cls" in class methods
        methodType = aFunctionCall.getMethodType()
        return True if argCount == 0 and (methodType == FunctionCall.MethodType.CLASS_METHOD or calleeLanguageType == LanguageType.INSTANCE) else False 

    ##
    # @param self The PythonTokensGenerator instance.
    # @return The Dummy class declaration code.
    def declareDummyClass(self):
        """
        Declare Dummy class.
        Return its declaration code.
        """
        return self.indentation_ + "from code_cropper import dummy\n"

    ##
    # @param self The PythonTokensGenerator instance.
    # @return The Json module declaration code.
    def declareJsonModule(self):
        """
        Declare Json Module (simplejson library).
        Return its declaration code.
        """
        return self.indentation_ + "import json\n"
    
    ##
    # @param self The PythonTokensGenerator instance.
    # @return the sentence ending.
    def endSentence(self):
        """
        Return the sentence ending.
        It's an empty string (no ';' is necessary).
        """
        return ""
    
class CppTokensGenerator(TokensGenerator):
    """
    Code generator for C++ source files.
    """
    INSTANCE_NAME_PREFIX = "var"
    MODULE_NAME_PREFIX = "mod"
    CLASS_NAME_PREFIX = "cls"
    SPACES_PER_TAB = 4
    MAX_LENGTH_FOR_NOT_DECLARING = 50

    ##
    # @param self The CppTokensGenerator to construct.
    # @param aProgramExecution Program execution call graph.
    # @param sourceType Kind of source to generate (see GeneratedSourceType).
    # @param projectName Code Cropper project name.
    def __init__(self, aProgramExecution, sourceType, projectName):
        """
        Constructor.
        """
        TokensGenerator.__init__(self, aProgramExecution, sourceType, projectName)
        self.nextModuleIndex_ = 0
        self.nextClassIndex_ = 0
        self.nextInstanceIndex_ = 0
        self.indentation_ = ""

    ##
    # @param self The CppTokensGenerator instance.
    # @return Code to insert at the beginning of the generated file.
    def initialFileCode(self):
        """
        Return code to insert at the beginning of the generated file.
        """
        return self.indentation_ + "#include <tchar.h>\n"

    ##
    # @param self The CppTokensGenerator instance.
    # @return Code to insert at the beginning of the generated file's main function.
    def beginMain(self):
        """
        Return code to insert at the beginning of the generated file's main function.
        """
        self.initSpaces_ = "\t"
        return "int _tmain(int argc, _TCHAR* argv[])\n{\n"
    ##
    # @param self The CppTokensGenerator instance.
    # @return Code to insert at the end of the generated file's main function.
    def endMain(self):
        """
        Return code to insert at the end of the generated file's main function.
        """
        self.initSpaces_ = ""
        return "}"

    ##
    # @param self The TokensGenerator instance.
    # @param moduleInfo Module information (see VariableInfo).
    # @return The module declaration code, or an empty string if the class is already declared.
    def _declareModule(self, moduleInfo):
        """
        Declare a module, if not declared before.
        """
        moduleNameStr = self._getDeclarationCodeFromObject(moduleInfo.getPythonObject())
        moduleName = eval(moduleNameStr)
        if moduleName in PythonConstants.BUILTINS_MODULE_NAMES:
            return "" 
        else:
            includeStr = moduleName
            optionalQuote = '' if includeStr.startswith("<") else '"'
            return self.indentation_ + "#include " + optionalQuote + includeStr + optionalQuote + "\n"
    
    ##
    # @param self The TokensGenerator instance.
    # @param classInfo Class information (see VariableInfo).
    # @return The class declaration code, or an empty string if the class is already declared.
    def _declareClass(self, classInfo):
        """
        Declare a class, if not declared before.
        """
        return ""

    ##
    # @param self The CppTokensGenerator instance.
    # @myObj A Python object.
    # @return Whether or not we'll use name to refer to the variable.
    def _mustUseVarNameForRepr(self, myObj):
        """
        Tell whether or not we'll use name to refer to the variable. Else (for instance: basic types), use a string representation.
        """
        objType = type(myObj)
        if objType is types.NoneType:
            return False
        if objType is types.BooleanType:
            return False
        if objType in (types.IntType, types.LongType, types.FloatType):
            return False
        if objType in (types.StringType, types.UnicodeType):
            return len(myObj) > TokensGenerator.MAX_LENGTH_FOR_NOT_DECLARING
        if objType in (types.ListType, types.DictType):
            #This is mandatory, since their construction is not trivial
            return True
        if objType is types.InstanceType:
            return False
        raise RuntimeError('Unsupported object type' + str(objType))
        return declarationCode

    ##
    # @param self The CppTokensGenerator instance.
    # @param myObj A Python object.
    # @return Declaration code for this object.
    def _getDeclarationCodeFromObject(self, myObj):
        """
        Get the declaration code for this object.
        """
        assert not self._mustUseVarNameForRepr(myObj)
        objType = type(myObj)
        if objType is types.NoneType:
            return 'NULL'
        if objType is types.BooleanType:
            return 'true' if myObj else 'false'
        if objType in (types.IntType, types.LongType, types.FloatType):
            return repr(myObj)
        if objType is types.StringType:
            return '"' + myObj + '"'
        if objType is types.UnicodeType:
            return 'u"' + repr(myObj)[2:-1] + '"'
        if objType is types.InstanceType:
            return 'Dummy("' + getClassStringForDummy(myObj) + '")'
        raise RuntimeError('Unsupported object type' + str(objType))
        return declarationCode 

    ##
    # @param self The CppTokensGenerator instance.
    # @param instanceInfo Instance information (see VariableInfo).
    # @param myType Type of the instance to declare.
    # @return The instance declaration code, or an empty string if the instance is already declared.
    def _declareInstance(self, instanceInfo, myType = ""):
        """
        Declare an instance, if not declared before.
        """
        mustDeclare = instanceInfo.getDeclarationType() != LanguageObject.DECLARATION_TYPES.CONSTRUCTOR and instanceInfo.useVarNameForRepr()
        if mustDeclare:
            myObj = instanceInfo.getPythonObject()
            assert myObj
            objType = type(myObj)
            if objType is types.ListType:
                declCode = self.indentation_ + myType + ' ' + instanceInfo.getVarName() + ";\n"
                for obj in myObj:
                    if self._mustUseVarNameForRepr(obj):
                        raise RuntimeError('std::vector only allows simple types members')
                    childValue = self._getDeclarationCodeFromObject(obj)
                    declCode += self.indentation_ + instanceInfo.getVarName() + ".push_back(" + childValue + ")" + ";\n"
                return declCode
            if objType is types.DictType:
                declCode = self.indentation_ + myType + ' ' + instanceInfo.getVarName() + ";\n"
                for key, value in myObj.items():
                    #Only simple types allowed
                    if self._mustUseVarNameForRepr(key) or self._mustUseVarNameForRepr(value):
                        raise RuntimeError('std::map only allows simple types members')
                    keyDecl = self._getDeclarationCodeFromObject(key)
                    valueDecl = self._getDeclarationCodeFromObject(value)
                    declCode += self.indentation_ + instanceInfo.getVarName() + "[" + keyDecl + "] = " + valueDecl + ";\n"
                return declCode
            if objType is types.InstanceType:
                return self.indentation_ + 'Dummy ' + instanceInfo.getVarName() + '("' + getClassStringForDummy(myObj) + '");\n'
            return self.indentation_ + myType + " " + instanceInfo.getVarName() + " = " + instanceInfo.getDeclarationCode() + "\n"
        else:
            return ""

    ##
    # @param self The CppTokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @param firstCall First FunctionCall for this object.
    # @return Whether or not an object must be created with the default constructor.
    def mustDefaultConstruct(self, aLanguageObject, firstCall):
        """
        Tell whether or not an object must be created with the default constructor.
        """
        if aLanguageObject.getLanguageType() == LanguageType.INSTANCE:
            #Object that don't call methods are not constructed
            if firstCall.getMethodType() != FunctionCall.MethodType.CONSTRUCTOR:
                #If first function is not __init__, call default constructor
                #Maybe an object already created is being annotated, or maybe there's no __init__
                return True
        return False

    ##
    # @param self The CppTokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    def defaultConstruct(self, aLanguageObject):
        """
        Call the object's default constructor.
        """
        assert self.languageObjectIsDeclared(aLanguageObject)
        varInfo = self.getVariableInfo(aLanguageObject)
        parentClass = aLanguageObject.getParent()
        assert parentClass.getLanguageType() == LanguageType.CLASS
        parentClassRepr = eval(self.getObjectRepresentation(parentClass))
        return self.indentation_ + parentClassRepr + " * " + varInfo.getVarName() + " = new " + parentClassRepr + ";\n"

    ##
    # @param self The CppTokensGenerator instance.
    # @param aLanguageObject A LanguageObject.
    # @param aCall A FunctionCall
    # @return Whether or not the method is a constructor.
    def methodIsConstructor(self, aLanguageObject, aCall):
        """
        Tell whether or not the method is a constructor (i.e.: its name equals the class').
        """
        if aLanguageObject.getLanguageType() != LanguageType.INSTANCE:
            return False
        parentClass = aLanguageObject.getParent()
        assert parentClass.getLanguageType() == LanguageType.CLASS
        parentClassRepr = eval(self.getObjectRepresentation(parentClass))
        return aLanguageObject.getLanguageType() == LanguageType.INSTANCE and aCall.getFunctionName() ==  parentClassRepr

    ##
    # @param self The CppTokensGenerator instance.
    # @param aFunctionCall A FunctionCall.
    # @return Code for this function call, to be inserted in the generated source file.
    def methodCall(self, aFunctionCall):
        """
        Return code for this function call, to be inserted in the generated source file.
        """
        calleeObject = aFunctionCall.getCallee()
        calleeLanguageType = calleeObject.getLanguageType()
        
        calleeRepresentation = self.getObjectRepresentation(calleeObject)
        if calleeLanguageType in (LanguageType.MODULE, LanguageType.CLASS):
            calleePrefix = ""
            #Built in classes do not need module qualification
            if calleeLanguageType == LanguageType.CLASS:
                calleePrefix = eval(calleeRepresentation) + "::"
            return self.indentation_ + calleePrefix + aFunctionCall.getFunctionName()
        
        assert calleeLanguageType == LanguageType.INSTANCE
        #Constructor is a special case, call new Class name
        if aFunctionCall.getMethodType() == FunctionCall.MethodType.CONSTRUCTOR:
            classObject = calleeObject.getParent()
            assert classObject.getLanguageType() == LanguageType.CLASS
            className = eval(self.getObjectRepresentation(classObject)) 
            methodCallStr = className + " * " + calleeRepresentation + " = new " + className
        #Destructor is a special case, call delete            
        elif aFunctionCall.getMethodType() == FunctionCall.MethodType.DESTRUCTOR:
            methodCallStr = "delete " + calleeRepresentation
        else:
            methodCallStr = calleeRepresentation
            methodCallStr += "->" + aFunctionCall.getFunctionName()
        return self.indentation_ + methodCallStr
    
    ##
    # @param self The CppTokensGenerator instance.
    # @param aFunctionCall A FunctionCall.
    # @param arg An Argument.
    # @param argCount Order in the arguments list for "arg".
    # @return If this argument must be skipped (for instance: "self" implicit argument in Python).
    def mustSkipArgument(self, aFunctionCall, arg, argCount):
        """
        Tell if this argument must be skipped (for instance: "self" implicit argument in Python).
		No skipping in C++ (as Python with its 'self' or 'cls' arguments.
        """
        return False 
        
    ##
    # @param self The CppTokensGenerator instance.
    # @return The Dummy class declaration code.
    def declareDummyClass(self):
        """
        Declare Dummy class.
        Return its declaration code.
        """
        return self.indentation_ + "#include <code_cropper/Dummy.h>\n"

    ##
    # @param self The CppTokensGenerator instance.
    # @return The Json module declaration code.    
    def declareJsonModule(self):
        """
        Unused.
        """
        return ""
    
    ##
    # @param self The CppTokensGenerator instance.
    # @return the sentence ending.
    def endSentence(self):
        """
        Return the sentence ending.
        It's an empty string (no ';' is necessary).
        """
        return ";"


class TokensGeneratorFactory:
    """
    Factory pattern to create a TokensGenerator, based on the programming language.
    """
    @staticmethod
    # @param aProgramExecution Program execution call graph.
    # @param sourceType Kind of source to generate (see GeneratedSourceType).
    # @param projectName Code Cropper project name.
    def createTokensGenerator(aProgramExecution, sourceType, projectName):
        language = aProgramExecution.getLanguage()
        if language == ProgramExecution.Languages.PYTHON:
            return PythonTokensGenerator(aProgramExecution, sourceType, projectName)
        if language == ProgramExecution.Languages.C_PLUS_PLUS:
            return CppTokensGenerator(aProgramExecution, sourceType, projectName)
        assert False, "Only Python or C++ TokensGenerator's are implemented"

##
# @param functionCalls: All the program calls (see call_graph.FunctionCall).
def _mustUseDummy(functionCalls):
    """
    Return if "Dummy" module must be used
    (at least one Dummy instance will be created).
    """
    useDummy = False
    for aCall in functionCalls:
        if useDummy:
            break
        #Arguments
        for anArgument in aCall.getArgsList():
            if useDummy:
                break
            argLo = anArgument.getLanguageObject()
            dt = argLo.getDeclarationType()
            if dt == LanguageObject.DECLARATION_TYPES.DUMMY:
                useDummy = True
    return useDummy

class CodeGenerator:
    """
    Generates an equivalent program, or unit test,
    starting from a Json database.
    """
    ALL_LEVELS = -1
    ##
    # @param self The CodeGenerator to construct.
    # @param callGraphStream File object with the call graph.
    # @param projectName Code Cropper project name.
    def __init__(self, callGraphStream, projectName = None):
        """
        Constructor.
        """
        aSerializer = CallGraphSerializer()
        self.programExecution_ = aSerializer.load(callGraphStream)
        self.tokensGenerator_ = None
        self.projectName_ = projectName

    ##
    # @param self The CodeGenerator.
    # @param fp File object with the input Json database.
    # @param searchLevel Function nesting level to filter. Use ALL_LEVELS to generate all the calls.
    # @param sourceType The type of equivalent code to generate (see GeneratedSourceType).
    
    def generateEquivalentProgram(self, fp, searchLevel = ProgramExecution.MIN_LEVEL, sourceType = GeneratedSourceType.MAIN_FILE):
        """
        Generate an equivalent source code for the program. It may be an equivalent program or unit test.
        And the searchLevel is a filter for function nesting level.
        The default is ProgramExecution.MIN_LEVEL (only root calls).
        Use ALL_LEVELS to get all the functions, although the equivalent program may call a nested function
        more than once, for instance:
        
        Original code:
            def f():
                print 'f'
                
            def g():
                f():
            g()
        
        Equivalent code (with searchLevel = 0):
            g()
        Equivalent code (with searchLevel = ALL_LEVELS):
            g()
                f()
        The latter is not equivalent to the original program, because f() is called twice.
        But it may be useful if the tool is used as a "logger":
        the results are more complete.
        """
        self.tokensGenerator_ = TokensGeneratorFactory.createTokensGenerator(self.programExecution_, sourceType, self.projectName_)
        fp.write(self.tokensGenerator_.initialFileCode())
        langObjects = self.programExecution_.getLanguageObjects()
        theCalls = self.programExecution_.getFunctionCalls()
        #Search in arguments use of Dummy class, include this module only if necessary
        useDummy = _mustUseDummy(theCalls)
        if useDummy:
            fp.write(self.tokensGenerator_.declareDummyClass())
            
        #Declare Modules
        for _, o in langObjects.items():
            if o.getLanguageType() == LanguageType.MODULE:
                fp.write(self.tokensGenerator_.declareLanguageObject(o))
        
        #Declare classes
        for _, o in langObjects.items():
            if o.getLanguageType() == LanguageType.CLASS:
                fp.write(self.tokensGenerator_.declareLanguageObject(o))

        fp.write('\n')
        fp.write(self.tokensGenerator_.beginMain())
        constructedObjectIds = []
        #Annotate calls. If necessary, declare objects
        previousLevel = -1
        for aCall in theCalls:
            level = aCall.getLevel()
            if searchLevel == CodeGenerator.ALL_LEVELS or searchLevel == level:
                if level != previousLevel:
                    self.tokensGenerator_.newFunctionLevel(level)
                    previousLevel = level
                callee = aCall.getCallee()
                calleeId = callee.getId()
                fp.write(self.tokensGenerator_.declareLanguageObject(callee))
                
                #Check default construction, do it only once
                if calleeId not in constructedObjectIds:
                    if self.tokensGenerator_.mustDefaultConstruct(callee, aCall):
                        fp.write(self.tokensGenerator_.defaultConstruct(callee))
                        constructedObjectIds.append(calleeId)
                
                #function will be printed after checking the arguments, in case an object declaration is needed
                methodCallStr = self.tokensGenerator_.methodCall(aCall)

                #Destructors do not have parameters
                if aCall.getMethodType() != FunctionCall.MethodType.DESTRUCTOR:
                    methodCallStr += self.tokensGenerator_.argumentsListBegin()
    
                    #Arguments
                    argsListStr = ""
                    argsList = aCall.getArgsList()
                    argsCount = len(argsList)
                    currentArg = 0 
                    for anArgument in argsList:
                        #Declare object, if necessary
                        argObject = anArgument.getLanguageObject()
                        fp.write(self.tokensGenerator_.declareLanguageObject(argObject))                    #Check skip argument for instance or class methods
                        if not self.tokensGenerator_.mustSkipArgument(aCall, argObject, currentArg):
                            argName = anArgument.getName()
                            if argName:
                                argsListStr += argName + " = "
                            argsListStr += self.tokensGenerator_.getObjectRepresentation(argObject)
                            if currentArg < argsCount - 1:
                                argsListStr += self.tokensGenerator_.argumentsListSeparator()
                        currentArg += 1
                    methodCallStr += argsListStr
                    methodCallStr += self.tokensGenerator_.argumentsListEnd()

                returnedObject = aCall.getReturnedObject()
                threwException = aCall.threwException()
                
                if returnedObject:
                    if returnedObject.getDeclarationType() != LanguageObject.DECLARATION_TYPES.CONSTRUCTOR:
                        if sourceType == GeneratedSourceType.UNIT_TEST:
                            #Declare returned object, if necessary
                            fp.write(self.tokensGenerator_.declareLanguageObject(returnedObject))
                            if threwException:
                                #For assertRaises to work, it calls its arguments
                                # -> remove the methodCallStr call, it will be
                                # done automatically by assertRaises
                                if methodCallStr.endswith('()'):
                                #Remove final "()"
                                    methodCallStr = methodCallStr[:-2]
                                else:
                                    #There are arguments
                                    initialIndex = methodCallStr.rfind('(')
                                    assert initialIndex >=0 and methodCallStr.endswith(')')
                                    methodCallStr = methodCallStr[:initialIndex] + ", " + methodCallStr[initialIndex + 1: -1]  
        
                        functionPrefix = self.tokensGenerator_.returnedObjectFunctionPrefix(returnedObject, threwException)
                        functionPosfix = self.tokensGenerator_.returnedObjectFunctionPosfix(returnedObject, threwException)
    
                    else:
                        self.tokensGenerator_.declareLanguageObject(returnedObject)
                        functionPrefix = self.tokensGenerator_.getInitialSpaces() + self.tokensGenerator_.getObjectRepresentation(returnedObject) + " = "
                        functionPosfix = ""
                else:
                    functionPrefix = ""
                    functionPosfix = ""

                if functionPrefix.strip():
                    methodCallStr = methodCallStr.lstrip()
                        
                #Check if we're in the constructor:
                if self.tokensGenerator_.methodIsConstructor(callee, aCall):
                    constructedObjectIds.append(calleeId)
                    #TODO GERVA: This is just a hack
                    language = self.programExecution_.getLanguage()
                    functionPrefix = self.tokensGenerator_.getInitialSpaces() if language == ProgramExecution.Languages.PYTHON else "" 
                    functionPosfix = ""

                methodCallStr = functionPrefix + methodCallStr + functionPosfix
                methodCallStr += self.tokensGenerator_.endSentence() + "\n"
                
                fp.write(methodCallStr)
        fp.write(self.tokensGenerator_.endMain())
        fp.write(self.tokensGenerator_.finalFileCode())
