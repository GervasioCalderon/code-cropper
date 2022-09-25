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

from io import StringIO
import unittest

import os
import tempfile
import code_cropper.annotator
import code_cropper.code_generator
import MyFunctions

def myPrint(str):
    pass

class AnnotatorTestCase(unittest.TestCase):
    importMyFunctionsStr ="import MyFunctions\n\n"

    def testFunctionWithoutParams(self):
        def annotate(a):
            a.annotate(MyFunctions,  "noParamsFunction")
        def codeToRun():
            MyFunctions.noParamsFunction()
        expectedStr = AnnotatorTestCase.importMyFunctionsStr + "MyFunctions.noParamsFunction()\n"
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr)
   
    def testOneIntegerFunction(self):
        def annotate(a):
            a.annotate(MyFunctions,  "add")
        def codeToRun():
            MyFunctions.add(4,5)
        expectedStr = AnnotatorTestCase.importMyFunctionsStr + "MyFunctions.add(4, 5)\n"
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr)

    def testTwoIntegerFunctions(self):
        def annotate(a):
            a.annotate(MyFunctions,  "add")
            a.annotate(MyFunctions,  "subtract")
        def codeToRun():
            MyFunctions.add(4,5)
            MyFunctions.subtract(4,5)
        expectedStr = AnnotatorTestCase.importMyFunctionsStr + "MyFunctions.add(4, 5)\nMyFunctions.subtract(4, 5)\n"
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr)

    def testAllModuleFunctions(self):
        def annotate(a):
            a.annotate(MyFunctions)
        def codeToRun():
            MyFunctions.noParamsFunction()
            z = MyFunctions.add(1, 2)
        expectedStr = AnnotatorTestCase.importMyFunctionsStr + "MyFunctions.noParamsFunction()\nMyFunctions.add(1, 2)\n"
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr)
    
    def testGeneratedCodeIsStandarized(self):
        def annotate(a):
            a.annotate(MyFunctions,  "add")
        def codeToRun():
            MyFunctions.   add  ( 4,  5 )
        #Generated should have a standard format, with no spaces 
        expectedStr = AnnotatorTestCase.importMyFunctionsStr + "MyFunctions.add(4, 5)\n"
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr)

    def testNonAnnotatedCodeIsSkipped(self):
        def annotate(a):
            a.annotate(MyFunctions,  "add")
            a.annotate(MyFunctions,  "subtract")
        def codeToRun():
            myPrint("Hello world!")
            MyFunctions.add(4,5)
            i = 2
            myPrint(i)
            MyFunctions.subtract(4,5)
            myPrint("On the Internet nobody knows you're a dog.")

        #Non annotated code, like the print, should be skipped. Only "add" and "subtract" 
        expectedStr = AnnotatorTestCase.importMyFunctionsStr + "MyFunctions.add(4, 5)\nMyFunctions.subtract(4, 5)\n"
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr)
        
    def testInnerFunctionIsNotCalled(self):
        def annotate(a):
            a.annotate(MyFunctions,  "innerFunction")
            a.annotate(MyFunctions,  "outerFunction")
        def codeToRun():
            MyFunctions.outerFunction()

        #Non annotated code, like the print, should be skipped. Only "add" and "subtract" 
        expectedStr = AnnotatorTestCase.importMyFunctionsStr + "MyFunctions.outerFunction()\n"
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr)

    def testAnnotatedObjectAllMethods(self):
        def createObj():
            return MyFunctions.MyClass()
            
        def annotate(a, obj):
            a.annotate(obj)
            
        def codeToRun(foo):
            foo.f1()
            foo.f2(5)
            myList = [5]
            myDict = {'x': 1, 'y': 2}
            foo.f3(myList)
            foo.f4(myDict,None)
        expectedStr = """import MyFunctions

var0 = MyFunctions.MyClass()
var0 = var0.f1()
var0.f2(5)
var2 = [5]
var0.f3(var2)
var3 = {}
var3['x'] = 1
var3['y'] = 2
var0.f4(var3, None)
"""
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr, createObj)

    def testAnnotatedClassWithoutConstructor(self):
        def createObj():
            return MyFunctions.MyClass
            
        def annotate(a, cls):
            a.annotate(cls)
            
        def codeToRun(cls):
            foo = cls()
            foo.f1()
            foo.f2(5)
            myList = [5]
            myTuple = (5, 25)
            myDict = {'x': 1, 'y': 2}
            myDict2 = {'x': myDict, 'y': myTuple }
            foo.f3(myList)
            foo.f4(myDict,None)
            foo.f5(myList,myDict2)
        expectedStr = """import MyFunctions

var0 = MyFunctions.MyClass()
var0 = var0.f1()
var0.f2(5)
var2 = [5]
var0.f3(var2)
var3 = {}
var3['x'] = 1
var3['y'] = 2
var0.f4(var3, None)
var10 = [5, 25]
var9 = {}
var9['x'] = var3
var9['y'] = var10
var0.f5(var2, var9)
"""
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr, createObj)

    def testAnnotatedClassWithConstructor(self):
        def createObj():
            return MyFunctions.ClassWithConstructor
            
        def annotate(a, cls):
            a.annotate(cls)
            
        def codeToRun(cls):
            foo = cls(1,2)
            x = foo.getX()
            foo.setX(5)
            y = foo.getY()
            foo.setY(10)
            myPrint("Get rid of the warnings ;) " + repr(cls) + repr(x + y))

        expectedStr = """import MyFunctions

var0 = MyFunctions.ClassWithConstructor(1, 2)
var0.getX()
var0.setX(5)
var0.getY()
var0.setY(10)
"""
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr, createObj)

    def testAnnotatedClassWithStaticMethods(self):
        def createObj():
            return MyFunctions.ClassWithStaticAndClassMethods
            
        def annotate(a, cls):
            a.annotate(cls)
            
        def codeToRun(cls):
            cls.static0()
            cls.static1(5)

        expectedStr = """import MyFunctions

MyFunctions.ClassWithStaticAndClassMethods.static0()
MyFunctions.ClassWithStaticAndClassMethods.static1(5)
"""
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr, createObj)

    def testAnnotatedClassWithClassMethods(self):
        def createObj():
            return MyFunctions.ClassWithStaticAndClassMethods
            
        def annotate(a, cls):
            a.annotate(cls)
            
        def codeToRun(cls):
            cls.classMethod0()
            cls.classMethod1(5)

        expectedStr = """import MyFunctions

MyFunctions.ClassWithStaticAndClassMethods.classMethod0()
MyFunctions.ClassWithStaticAndClassMethods.classMethod1(5)
"""
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr, createObj)

    def testDummyClass(self):
        def createObj():
            return MyFunctions.ClassWithDummyParameters
            
        def annotate(a, cls):
            a.annotate(cls)
            
        def codeToRun(cls):
            p = MyFunctions.NonAnnotatedClass()
            foo = cls()
            foo.f1(p)
        expectedStr = """from code_cropper import dummy
import MyFunctions

var0 = MyFunctions.ClassWithDummyParameters()
var0.f1(dummy.Dummy('MyFunctions.NonAnnotatedClass'))
"""
        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr, createObj)

    def testGenerateUnitTest(self):
        def annotate(a):
            a.annotate(MyFunctions,  "func1")
            a.annotate(MyFunctions,  "func2")
        def codeToRun():
            try:
                MyFunctions.func1()
                MyFunctions.func2()
            except Exception as e:
                print(str(e))

        expectedStr = """import unittest
import MyFunctions

class UNIT_TEST_CASE(unittest.TestCase):
    def test_main(self):
        self.assertEqual(1, MyFunctions.func1())
        self.assertRaises(MyFunctions.MyException, MyFunctions.func2)

if __name__ == '__main__':
    unittest.main()"""
        

        self.__testAnnotatorFunction(codeToRun, annotate, expectedStr, sourceType = code_cropper.code_generator.GeneratedSourceType.UNIT_TEST)

    def __testAnnotatorFunction(self, codeToRun, changeAnnotatorCb, expectedStr, createObjectCb = None, sourceType = code_cropper.code_generator.GeneratedSourceType.MAIN_FILE):
        a = code_cropper.annotator.annotatorInstance()
        a.resetForNewAnnotations()
        obj = None

        if not createObjectCb is None:
            obj = createObjectCb()
            changeAnnotatorCb(a, obj)
        else:
            changeAnnotatorCb(a)

        def run_code():
            if not createObjectCb is None:
                codeToRun(obj)
            else:
                codeToRun()

        def run_annotated_code():
            dumpFilePath = os.path.join(tempfile.gettempdir(), "call_graph.json")
            with code_cropper.annotator.ProgramExecutionDumper(
                    dumpFilePath,
                    preserveOldDumpFiles=False
           ):
                run_code()
            return dumpFilePath

        dumpFilePath = run_annotated_code()
        # These repetitions test that the original functions were correctly restored.
        # No exceptions should be thrown.
        run_annotated_code()
        run_code()

        with open(dumpFilePath, 'r') as dumpFile:
            #Get equivalent program
            myCodeGenerator = code_cropper.code_generator.CodeGenerator(dumpFile)
            equiv_program_io = StringIO()
            myCodeGenerator.generateEquivalentProgram(equiv_program_io, code_cropper.annotator.ProgramExecution.MIN_LEVEL, sourceType)
            equiv_program_str = equiv_program_io.getvalue()
            equiv_program_io.close()
        
        self.assertEqual(equiv_program_str, expectedStr)

if __name__ == '__main__':
    unittest.main()
