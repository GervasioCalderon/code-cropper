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

#Empty print for not disturbing the unit tests output
def myPrint( str ):
    pass

def add( i,  j):
    return 25 #i + j
    
def subtract( i,  j):
    return None
    
def mySubstring( str,  length ):
    return str[:length]

def processList( aList ):
    myPrint( "Entered processList" )
    for elem in aList:
        myPrint ("elem: " + repr(elem) + "\n")

def processDict( aDict ):
    myPrint( "Entered processDict" )
    for elem in aDict.items():
        key,  value = elem
        myPrint( "key: " + repr(key) + "\n" )
        myPrint( "value: " + repr(value) + "\n" )
        
def innerFunction():
    pass

def outerFunction():
    innerFunction()

def noParamsFunction():
    return MyClass()

class MyClass(object):
    def f1(self):
        myPrint( "No params" )
        return self
    def f2(self, i):
        myPrint( "i:" + repr(i) )
    def f3(self, aList):
        x = aList[0]
        myPrint( "x:" + repr(x) )
    def f4(self, aDict, anObj):
        x = aDict['x']
        y = aDict['y']
        myPrint("x: " + repr(x) + ", y:" + repr(y) )
        myPrint("anObj: "  + repr(anObj))
    def f5(self, obj1, obj2):
        myPrint("obj1: " + str(obj1) + ", obj2: " + str(obj2)) 

class ClassWithDummyParameters(object):
    def f1(self, d):
        myPrint( "Dummy parameter" )
        
class NonAnnotatedClass(object):
    pass

class ClassWithConstructor(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        myPrint( "No params" )
    def getX(self):
        return self.x
    def setX(self,x):
        self.x = x 
    def getY(self):
        return self.y
    def setY(self, y):
        self.y = y
        
class ClassWithStaticAndClassMethods(object):
    @staticmethod
    def static0():
        myPrint( "static0")
    @staticmethod
    def static1( x ):
        myPrint( "x: " + repr(x) )
    @classmethod
    def classMethod0(cls):
        myPrint( "Class is " + repr(cls) )
    @classmethod
    def classMethod1(cls,x):
        myPrint( "Class is " + repr(cls) + "x = " + str(x) )
        
def func1():
    return 1

class MyException(Exception):
    def __init__(self, i):
        self.i_ = i
    def __str__(self):
        return "'" + str(self.i_) + "' is not a valid number" 

def func2():
    raise MyException(4)
    pass
