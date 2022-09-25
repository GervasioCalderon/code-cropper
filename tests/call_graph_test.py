# This file is part of Code Cropper
# The tool has been designed and developed by Eng. Gervasio Calderon
# 
# Copyright (c) 2022, Core Security Technologies
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

from code_cropper.call_graph import LanguageType
from code_cropper.call_graph import LanguageObject
from code_cropper.call_graph import InvalidParentException
from code_cropper.call_graph import Argument
from code_cropper.call_graph import FunctionCall
from code_cropper.call_graph import DuplicatedLanguageObjectIdException
from code_cropper.call_graph import ProgramExecution

import unittest

class CallGraphTestCase(unittest.TestCase):
    def testLanguageType(self):
        self.assertEqual(LanguageType.asString(LanguageType.NONE), "None")
        self.assertEqual(LanguageType.asString(LanguageType.MODULE), "Module")
        self.assertEqual(LanguageType.asString(LanguageType.CLASS), "Class")
        self.assertEqual(LanguageType.asString(LanguageType.INSTANCE), "Instance")
 
        self.assertTrue(LanguageType.isValidParent(LanguageType.NONE, LanguageType.MODULE))
        self.assertTrue(LanguageType.isValidParent(LanguageType.MODULE, LanguageType.CLASS))
        self.assertTrue(LanguageType.isValidParent(LanguageType.CLASS, LanguageType.INSTANCE))
        
        self.assertFalse(LanguageType.isValidParent(LanguageType.INSTANCE, LanguageType.MODULE))
        self.assertFalse(LanguageType.isValidParent(LanguageType.INSTANCE, LanguageType.MODULE))
        self.assertFalse(LanguageType.isValidParent(LanguageType.INSTANCE, LanguageType.CLASS))
        self.assertFalse(LanguageType.isValidParent(LanguageType.INSTANCE, LanguageType.INSTANCE))
        self.assertFalse(LanguageType.isValidParent(LanguageType.MODULE, LanguageType.MODULE))
        self.assertFalse(LanguageType.isValidParent(LanguageType.MODULE, LanguageType.INSTANCE))
        self.assertFalse(LanguageType.isValidParent(LanguageType.CLASS, LanguageType.MODULE))
        self.assertFalse(LanguageType.isValidParent(LanguageType.CLASS, LanguageType.CLASS))
        
    def testLanguageObject(self):
        mod = LanguageObject(1, LanguageType.MODULE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "mod1.mod2")
        self.assertEqual(mod.getId(), 1)
        self.assertEqual(mod.getLanguageType(), LanguageType.MODULE)
        self.assertEqual(mod.getDeclarationType(), LanguageObject.DECLARATION_TYPES.FIXED_VALUE)
        self.assertEqual(mod.getDeclarationCode(), "mod1.mod2")
        self.assertEqual(mod.getParent(), None)
        
        def moduleWithParentModule(mod):
            mod2 = LanguageObject(2, LanguageType.MODULE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "mod2", mod)
        
        self.assertRaises(InvalidParentException, moduleWithParentModule, mod)
        
        def parentlessClass():
            aClass = LanguageObject(3, LanguageType.CLASS, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "AClass")
        
        self.assertRaises(InvalidParentException, parentlessClass)
        
        #Parent should be ok, no InvalidParentException raised
        aClass = LanguageObject(2, LanguageType.CLASS, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "AClass", mod)
        
        self.assertEqual(aClass.getId(), 2)
        self.assertEqual(aClass.getLanguageType(), LanguageType.CLASS)
        self.assertEqual(aClass.getDeclarationType(), LanguageObject.DECLARATION_TYPES.FIXED_VALUE)
        self.assertEqual(aClass.getDeclarationCode(), "AClass")
        self.assertEqual(aClass.getParent(), mod)
        
        def instanceWithModuleParent(mod):
            anInstance = LanguageObject(3, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "'Gerva'", mod)
        
        self.assertRaises(InvalidParentException, instanceWithModuleParent, mod)
        
        #Class parent is ok for an instance
        anInstance = LanguageObject(3, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, '"Gerva"',  aClass)
        
        self.assertEqual(anInstance.getId(), 3)
        self.assertEqual(anInstance.getLanguageType(), LanguageType.INSTANCE)
        self.assertEqual(anInstance.getDeclarationCode(), '"Gerva"')
        self.assertEqual(anInstance.getParent(), aClass)
    
    def testArgument(self):
        mod = LanguageObject(1, LanguageType.MODULE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "mod1.mod2")
        arg = Argument(mod)
        self.assertEqual(arg.getLanguageObject(), mod)
        self.assertEqual(arg.getName(), None)
        
        arg2 = Argument(mod, "Gerva")
        self.assertEqual(arg2.getName(), "Gerva")
        
    def testFunctionCall(self):
        start = time.time()
        
        mod = LanguageObject(1, LanguageType.MODULE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "mod1.mod2")
        cls =  LanguageObject(2, LanguageType.CLASS, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "AClass", mod)
        obj =  LanguageObject(3, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "5", cls)
        obj2 =  LanguageObject(4, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, '"Gerva"', cls)
        
        argsList = []
        argsList.append(Argument(obj))
        argsList.append(Argument(obj2, "paramName"))
        
        MT = FunctionCall.MethodType
        aCall = FunctionCall(1, mod, "fun", MT.METHOD, argsList, 1)
        aCall2 = FunctionCall(2, mod, "fun2", MT.METHOD, argsList, 2)

        self.assertEqual(aCall.getId(), 1)
        self.assertEqual(aCall.getCallee(), mod)
        self.assertEqual(aCall.getFunctionName(), "fun")
        self.assertEqual(aCall.getArgsList(), argsList)
        self.assertEqual(aCall.getLevel(), 1)
        self.assertEqual(aCall.getReturnedObject(), None)
        self.assertEqual(aCall.threwException(), False)
        self.assertEqual(aCall.getTotalTime(), None)
        self.assertEqual(aCall2.getId(), 2)
        
        finish = time.time()
        totalTime = finish - start
        aCall3 = FunctionCall(3, mod, "fun3", MT.METHOD, argsList, 0, obj2, True, totalTime)
        self.assertEqual(aCall3.getReturnedObject(), obj2)
        self.assertEqual(aCall3.threwException(), True)
        self.assertEqual(aCall3.getTotalTime(), totalTime)
        
    def testProgramExecution(self):
        
        myProgramExecution = ProgramExecution("Python")
                
        theLanguageTypes = myProgramExecution.getLanguageTypes()
        self.assertEqual(LanguageType.NONE, theLanguageTypes[LanguageType.NONE])
        self.assertEqual(LanguageType.MODULE, theLanguageTypes[LanguageType.MODULE])
        self.assertEqual(LanguageType.CLASS, theLanguageTypes[LanguageType.CLASS])
        self.assertEqual(LanguageType.INSTANCE, theLanguageTypes[LanguageType.INSTANCE])
        
        mod = LanguageObject(1, LanguageType.MODULE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "mod1.mod2.mod3")
        myProgramExecution.addLanguageObject(mod)
        
        cls =  LanguageObject(2, LanguageType.CLASS, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "Class1", mod)
        myProgramExecution.addLanguageObject(cls)
        
        #test duplicated id
        def languageObjectWithDuplicatedId(aProgramExecution, cls):
            obj =  LanguageObject(2, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "5", cls)
            aProgramExecution.addLanguageObject(obj)
                    
        self.assertRaises(DuplicatedLanguageObjectIdException, languageObjectWithDuplicatedId, myProgramExecution, cls)
        
        obj =  LanguageObject(3, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "5", cls)
        myProgramExecution.addLanguageObject(obj)
        obj2 =  LanguageObject(4, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.FIXED_VALUE, "25", cls)
        myProgramExecution.addLanguageObject(obj2)
        obj3 =  LanguageObject(5, LanguageType.INSTANCE, LanguageObject.DECLARATION_TYPES.CONSTRUCTOR, "", cls)
        myProgramExecution.addLanguageObject(obj3)
        
        argsList = []
        argsList.append(Argument(obj))
        argsList.append(Argument(obj2, "paramName"))
        
        MT = FunctionCall.MethodType
        aCall = FunctionCall(1, mod, "fun", MT.METHOD, argsList, 0)
        aCall2 = FunctionCall(2, cls, "cls_fun", MT.CLASS_METHOD, argsList, 1)
        aCall3 = FunctionCall(3, obj3, "__init__", MT.CONSTRUCTOR, argsList, 0)
        aCall4 = FunctionCall(4, obj3, "obj_fun", MT.METHOD, argsList, 0)
        
        myProgramExecution.addFunctionCall(aCall)
        myProgramExecution.addFunctionCall(aCall2)
        myProgramExecution.addFunctionCall(aCall3)
        
        self.assertEqual(myProgramExecution.getLanguage(), "Python")
        theLanguageObejcts = myProgramExecution.getLanguageObjects()
        
        self.assertEqual(theLanguageObejcts[1], mod)
        self.assertEqual(theLanguageObejcts[2], cls)
        self.assertEqual(theLanguageObejcts[3], obj)
        self.assertEqual(theLanguageObejcts[4], obj2)
        self.assertEqual(theLanguageObejcts[5], obj3)
        
        theCalls = myProgramExecution.getFunctionCalls()
        self.assertEqual(theCalls[0], aCall)
        self.assertEqual(theCalls[1], aCall2)
        self.assertEqual(theCalls[2], aCall3)

if __name__ == '__main__':
    unittest.main()
