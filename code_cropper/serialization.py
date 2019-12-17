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
'''
Module that serializes/deserializes a Call Graph into a Json database.
It uses simplejson library.
'''
import types
from cStringIO import StringIO
import json
from call_graph import LanguageType
from call_graph import LanguageObject
from call_graph import InvalidParentException
from call_graph import Argument
from call_graph import FunctionCall
from call_graph import DuplicatedLanguageObjectIdException
from call_graph import ProgramExecution

##
# @param obj Python object to dump.
# @return The Json representation for this object.
def asJsonString(obj):
    '''
    Get the Json representation for this object.
    '''
    io = StringIO()
    json.dump(obj, io, sort_keys=True, indent=CallGraphSerializer.JSON.INDENT)
    return io.getvalue()

##
# @param str Json representation for an object.
# @return The Python object whose Json representation is 'str' parameter.
def fromJsonString(str):
    '''
    Get the Python object correspondent to a Json representation.
    '''
    return json.loads(str)


class CallGraphLoadException(Exception):
    '''
    Exception class for an error loading a Call Graph in memory.
    '''
    ##
    # @param self The CallGraphLoadException instance to construct.
    # @param msg Exception's error message
    def __init__(self, msg):
        '''
        Constructor.
        '''
        self.msg_ = msg

    # @param self The CallGraphLoadException instance.
    # @return A string representation for the exception.
    def __str__(self):
        '''
        String representation.
        '''
        return self.msg_ 


class CallGraphSerializer(object):
    '''
    Serializes a Call Graph in a Json database, with the help of simplejson module.
    '''
    class JSON(object):
        '''
        Json-related constants.
        '''
        #For json pretty-printing
        INDENT = 4
        
        #String constants
        #Global
        ID = 'id'
        NAME = 'name'
        
        #LanguageObject
        LANGUAGE_TYPE_ID = 'languageTypeId'
        DECLARATION_TYPE = 'declarationType'
        DECLARATION_CODE =  'declarationCode'
        PARENT_ID = 'parentId'
        
        #Argument
        ARGS = 'args'
        KARGS = 'kargs'
        IS_CONST = "isConst";
        ARG_TYPE = "argType";
        
        #FunctionCall
        CALLEE_ID = 'calleeId'
        FUNC_NAME = 'funcName'
        METHOD_TYPE = 'methodType'
        RETURN_ID = 'returnId'
        THREW_EXCEPTION = 'threwException'
        LEVEL = 'level'
        RETURNED_OBJECT = 'returnedObject'
        THREW_EXCEPTION = 'threwException'
        TOTAL_TIME = 'totalTime'
        ARGUMENTS = 'arguments'
        
        #ProgramExecution
        LANGUAGE = 'language'
        LANGUAGE_TYPES = 'languageTypes'
        LANGUAGE_OBJECTS = 'languageObjects'
        CALL_GRAPH = 'callGraph'

    ##
    # @param self The CallGraphSerializer instance.
    # @param aProgramExecution A program Call Graph to dump.
    # @param fp File object where the Json database will be dumped.
    def dump(self, aProgramExecution, fp):
        '''
        Dump a ProgramExecution in a Json database file.
        '''
        progExecMap = self.__dumpProgramExecutionAsJsonMap(aProgramExecution)
        json.dump(progExecMap, fp, sort_keys=True, indent=CallGraphSerializer.JSON.INDENT)

    ##
    # @param self The CallGraphSerializer instance.
    # @param fp File object where the Json database is stored.
    # @return A ProgramExecution (call graph) that represents the database previously stored in a Json database.
    def load(self, fp):
        '''
        Load a ProgramExecution from a Json database file, and return it.
        '''
        progExecMap = json.load(fp)
        return self.__loadProgramExecutionFromJsonMap(progExecMap)

    ##
    # @param self The CallGraphSerializer instance.
    # @param aProgramExecution A program Call Graph to dump.
    # @return A "Json-compliant" Python dict with the ProgramExecution data. Storing it in a Json file is straight-forward.
    def __dumpProgramExecutionAsJsonMap(self, aProgramExecution):
        '''
        Translate a ProgramExecution class to a "Json-compliant" format, i.e.:
        a Python dict (simplejson forces the object to dump to be a native type, not a custom class)
        with the same information.
        '''
        ##
        # @param obj LanguageObject, or None
        # @return Obj's LanguageObject id, or 0 if obj is None.         
        def getOptionalObjectId( obj ):
            '''
            Return LanguageObject id, or 0 if obj is None.
            '''
            return 0 if obj is None else obj.getId()

        JSON = CallGraphSerializer.JSON
        progExecMap = {}
        progExecMap[JSON.LANGUAGE] = aProgramExecution.getLanguage()
        
        progExecMap[JSON.LANGUAGE_TYPES] = []
        ltArray = progExecMap[JSON.LANGUAGE_TYPES]
        myLanguageTypes = aProgramExecution.getLanguageTypes()
        for lt in myLanguageTypes:
            ltArray.append( { JSON.ID: lt, JSON.NAME: LanguageType.asString( lt) } )
        
        langObjects = aProgramExecution.getLanguageObjects()
        progExecMap[JSON.LANGUAGE_OBJECTS] = []
        loArray = progExecMap[JSON.LANGUAGE_OBJECTS]
        for oId, o in langObjects.items():
            loMap = {}
            assert oId == o.getId()
            loMap[JSON.ID] = oId
            loMap[JSON.LANGUAGE_TYPE_ID] = o.getLanguageType()
            loMap[JSON.DECLARATION_TYPE] = o.getDeclarationType()
            loMap[JSON.DECLARATION_CODE] = fromJsonString(o.getDeclarationCode())
            parent = o.getParent()
            loMap[JSON.PARENT_ID] = getOptionalObjectId(parent)
            loArray.append(loMap)

        theCalls = aProgramExecution.getFunctionCalls()
        
        progExecMap[JSON.CALL_GRAPH] = []
        callGraph = progExecMap[JSON.CALL_GRAPH]
    
        for aCall in theCalls:
            callMap = {}
            callMap[JSON.ID] = aCall.getId()
            callMap[JSON.CALLEE_ID] = aCall.getCallee().getId()
            callMap[JSON.FUNC_NAME] = aCall.getFunctionName()
            callMap[JSON.METHOD_TYPE] = aCall.getMethodType()
            callMap[JSON.LEVEL] = aCall.getLevel()
            callMap[JSON.RETURNED_OBJECT] = getOptionalObjectId(aCall.getReturnedObject())
            callMap[JSON.THREW_EXCEPTION] = aCall.threwException()
            totalTime = aCall.getTotalTime()
            if totalTime:
                callMap[JSON.TOTAL_TIME] = totalTime
            #Arguments
            callMap[JSON.ARGUMENTS] = {}
            argsList = []
            kargsMap = {}
            for anArgument in aCall.getArgsList():
                theId = anArgument.getLanguageObject().getId()
                theName = anArgument.getName()
                if anArgument.getName() is None:
                    argsList.append(theId)
                else:
                    kargsMap[theName] = theId
            callMap[JSON.ARGUMENTS][JSON.ARGS] = argsList
            callMap[JSON.ARGUMENTS][JSON.KARGS] = kargsMap
            callGraph.append(callMap)

        return progExecMap

    ##
    # @param self The CallGraphSerializer instance.
    # @param progExecMap A Python dict with a call graph previously loaded from a Json database.
    # @return A newly-created ProgramExecution instance that represents the call graph stored in progExecMap.
    def __loadProgramExecutionFromJsonMap(self, progExecMap):
        '''
        Load a new ProgramExecution class from a "Json-compliant" dict.
        '''
        ##
        # @param aProgramExecution Program execution that holds the LanguageObject searched.
        # @id Id for the LanguageObject being serched (or 0 for a "None" object).
        # @return The LanguageObject searching for id, or None if id is 0.
        def getLanguageObjectFromId(aProgramExecution, id ):
            '''
            Return the LanguageObject searching for id, or None if id is 0.
            '''
            return None if id is 0 else aProgramExecution.getLanguageObjects()[id]
        
        JSON = CallGraphSerializer.JSON
        language = progExecMap[JSON.LANGUAGE]
        myProgramExecution = ProgramExecution(progExecMap[JSON.LANGUAGE])
        #LanguageType map is already loaded, verify it has the same values
        
        langTypesMap = progExecMap[JSON.LANGUAGE_TYPES]
        langTypes = []
        for lt in langTypesMap:
            ltId = lt[JSON.ID]
            if LanguageType.asString(ltId) != lt[JSON.NAME]:
                raise CallGraphLoadException("Invalid LanguageType pair. Id: " + str(ltId) + ", name:'" + lt[JSON.NAME] + "'")
            langTypes.append(ltId)
        if sorted(myProgramExecution.getLanguageTypes()) != sorted(langTypes):
            raise CallGraphLoadException("Invalid LanguageType's: " + str(langTypes))
        
        langObjectsArray = progExecMap[JSON.LANGUAGE_OBJECTS]
        for lo in langObjectsArray:
            parent = getLanguageObjectFromId(myProgramExecution, lo[JSON.PARENT_ID])
            myLo = LanguageObject (lo[JSON.ID], lo[JSON.LANGUAGE_TYPE_ID], lo[JSON.DECLARATION_TYPE], asJsonString(lo[JSON.DECLARATION_CODE]), parent)
            myProgramExecution.addLanguageObject(myLo)

        myCalls = progExecMap[JSON.CALL_GRAPH]
        for callMap in myCalls:
            callId = callMap[JSON.ID]
            callee = getLanguageObjectFromId(myProgramExecution, callMap[JSON.CALLEE_ID])
            funcName = callMap[JSON.FUNC_NAME]
            methodType = callMap[JSON.METHOD_TYPE]
            level = callMap[JSON.LEVEL]
            returnedObject = getLanguageObjectFromId(myProgramExecution, callMap[JSON.RETURNED_OBJECT] if callMap.has_key(JSON.RETURNED_OBJECT) else 0)
            threwException = callMap[JSON.THREW_EXCEPTION] if callMap.has_key(JSON.THREW_EXCEPTION) else False 
            totalTime = callMap[JSON.TOTAL_TIME] if callMap.has_key(JSON.TOTAL_TIME) else None
            
            args = callMap[JSON.ARGUMENTS][JSON.ARGS]
            argsList = []
            
            #TODO GERVA: UNIFICAR
            if language == ProgramExecution.Languages.PYTHON:
                for arg in args:
                    argObj = Argument(getLanguageObjectFromId(myProgramExecution, arg))
                    argsList.append(argObj)
                kargsMap = callMap[JSON.ARGUMENTS][JSON.KARGS]
                for argName, objId in kargsMap.items():
                    argObj = Argument(getLanguageObjectFromId(myProgramExecution, objId), argName)
                    argsList.append(argObj)
            else:
                assert language == ProgramExecution.Languages.C_PLUS_PLUS
                for arg in args:
                    argLoId = arg[JSON.ID]
                    argValueType = arg[JSON.ARG_TYPE]
                    argIsConst = arg[JSON.IS_CONST]
                    argObj = Argument(getLanguageObjectFromId(myProgramExecution, argLoId), None, argValueType, argIsConst)
                    argsList.append(argObj)
        
            func = FunctionCall(callId, callee, funcName, methodType, argsList, level, returnedObject, threwException, totalTime)
            myProgramExecution.addFunctionCall(func)
        
        return myProgramExecution
