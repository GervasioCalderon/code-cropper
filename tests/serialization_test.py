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

import os
import time
from copy import deepcopy
import traceback
import tempfile
import json

from code_cropper.call_graph import LanguageType
from code_cropper.call_graph import LanguageObject
from code_cropper.call_graph import InvalidParentException
from code_cropper.call_graph import Argument
from code_cropper.call_graph import FunctionCall
from code_cropper.call_graph import DuplicatedLanguageObjectIdException
from code_cropper.call_graph import ProgramExecution
from code_cropper.serialization import CallGraphSerializer
from code_cropper.serialization import asJsonString

import unittest

class CallGraphTestCase(unittest.TestCase):

    def testSerialization(self):
        myProgramExecution = self.__createSampleProgramExecution__()
        aSerializer = CallGraphSerializer()
        
        fileName = os.path.join(tempfile.gettempdir(), "call_graph.json")
        
        with open(fileName, "w") as fp:
            aSerializer.dump(myProgramExecution, fp)
            
        with open(fileName, "r") as fp:
            loadedProgramExecution = aSerializer.load(fp)
        
        self.__compareProgramExecutions__(myProgramExecution, loadedProgramExecution)

    def __createSampleProgramExecution__(self):
        myProgramExecution = ProgramExecution("Python")
        
        mod = LanguageObject(1, LanguageType.MODULE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, asJsonString('mod1.mod2.mod3'))
        myProgramExecution.addLanguageObject(mod)
        
        cls =  LanguageObject(2, LanguageType.CLASS, LanguageObject.DECLARATION_TYPES.CONSTRUCTOR, asJsonString('Class1'), mod)
        myProgramExecution.addLanguageObject(cls)

        obj =  LanguageObject(3, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, asJsonString(5), cls)
        myProgramExecution.addLanguageObject(obj)
        obj2 =  LanguageObject(4, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, asJsonString(25), cls)
        myProgramExecution.addLanguageObject(obj2)
        obj3 =  LanguageObject(5, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.CONSTRUCTOR, asJsonString('Gerva'), cls)
        myProgramExecution.addLanguageObject(obj3)
        
        argsList = []
        argsList.append(Argument(obj))
        argsList.append(Argument(obj2, "paramName"))
        
        MT = FunctionCall.MethodType
        aCall3 = FunctionCall(3, obj3, "__init__", MT.CONSTRUCTOR, argsList, 2, obj2)
        aCall4 = FunctionCall(4, obj3, "obj_fun", MT.METHOD, argsList, 1, obj3, True)
        
        myProgramExecution.addFunctionCall(aCall3)
        myProgramExecution.addFunctionCall(aCall4)
        
        return myProgramExecution
    
    def __compareLanguageObjects(self, obj1, obj2):
        bothNone = obj1 is None and obj2 is None
        self.assertTrue(bothNone or obj1.getId() == obj2.getId())

        
    def __compareProgramExecutions__(self, programExec1, programExec2):
        #Compare languages
        self.assertEqual(programExec1.getLanguage(), programExec2.getLanguage())

        #Compare LanguageObjects
        langObjects1 = programExec1.getLanguageObjects()
        langObjects2 = programExec2.getLanguageObjects()
        
        #Use an auxiliary set to hold languageObject2's keys
        #Inside langObjects1 cycle, all keys should be removed from the set if both dicts are equal
        
        langObjectKeys2 = deepcopy(langObjects2)
        
        for id, langObject in langObjects1.items():
            self.assertTrue(id in langObjectKeys2)
            langObject2 = langObjects2[id]
            self.__compareLanguageObjects(langObject, langObject2)
            del langObjectKeys2[id]

        #Ensure both containers have the same size
        self.assertTrue(not langObjectKeys2)

        #Compare CallGraph's
        calls = programExec1.getFunctionCalls()
        calls2 = programExec2.getFunctionCalls()
           
        #Compare calls array. Order is important, so we assume it's possible to compare element by element
        length = len(calls)
        self.assertEqual(length, len(calls2))
        for i in range(length):
            call1 = calls[i]
            call2 = calls2[i]
            #This is similar to language objects parents' comparison above:
            #Compare just the id's.
            #Objects from the container must be equal, so any difference should have been detected above
            self.__compareLanguageObjects(call1.getCallee(), call2.getCallee()) 
            self.assertEqual(call1.getFunctionName(), call2.getFunctionName())
            self.assertEqual(call1.getMethodType(), call2.getMethodType())
            #Compare arguments
            argsList1 = call1.getArgsList()
            argsList2 = call2.getArgsList()
            
            #This is similar to calls array. Order does matter, so we assume it's possible to compare element by element
            argsLenght = len(argsList1)
            self.assertEqual(argsLenght, len(argsList2))
            for j in range(argsLenght):
                self.__compareLanguageObjects(argsList1[j].getLanguageObject(), argsList2[j].getLanguageObject())
                self.assertEqual(argsList1[j].getName(), argsList2[j].getName())
                
            self.assertEqual(call1.getLevel(), call2.getLevel())
            self.__compareLanguageObjects(call1.getReturnedObject(), call2.getReturnedObject())
            self.assertEqual(call1.threwException(), call2.threwException())
            self.assertEqual(call1.getTotalTime(), call2.getTotalTime())

    def __compareLanguageObjects(self, langObject1, langObject2):
            bothNone = langObject1 is None and langObject2 is None
            if not bothNone:
                #Both none => OK
                self.assertEqual(langObject1.getId(), langObject2.getId())
                self.assertEqual(langObject1.getLanguageType(), langObject2.getLanguageType())
                self.assertEqual(langObject1.getDeclarationType(), langObject2.getDeclarationType())
                self.assertEqual(langObject1.getDeclarationCode(), langObject2.getDeclarationCode())
                #To compare parents:
                # Compare Id's
                # Parents must be in the container, so they're compared another time in this very cycle
                parent1 = langObject1.getParent()
                parent2 = langObject2.getParent()
                bothNone = parent1 is None and parent2 is None
                self.assertTrue(bothNone or parent1.getId() == parent2.getId())

if __name__ == '__main__':
    unittest.main()
