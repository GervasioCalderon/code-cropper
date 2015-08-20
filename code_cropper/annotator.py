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
KEY MODULE. It's the interface between the code and the classes that store the graph call.
It allows to "annotate" a function, i.e.: replace it with another one that has the same behavior,
but it also stores its data and parameters in a memory representation of the call graph,
to persist it later in a Database.
'''
import sys
import types
import inspect
import json
from cStringIO import StringIO

from threading import Thread
from Queue import Queue

import file_utils
from serialization import CallGraphSerializer
from serialization import asJsonString
from call_graph import LanguageType
from call_graph import LanguageObject
from call_graph import FunctionCall
from call_graph import ProgramExecution
from call_graph import Argument
from serialization import CallGraphSerializer
from python_language import PythonConstants

##
# @param obj Python "object" (it may be a module, class, or instance) whose functions we're annotating.
# @return None for modules, obj.__class__ for instances, obj if it's a class.
def _getClassForAnnotatedObj(obj):
    '''
    Return the "class" for an Python "object" (function holder: it may be a module, class, or instance).
    '''
    if inspect.ismodule(obj):
        return None
    if inspect.isclass(obj):
        return obj
    return obj.__class__

##
# @param cls A Python class.
# @return A dict { functionName -> attribute kind }, see function documentation for the values.
def _getClassMethodsType(cls):
    '''
    Get the kind of attribute for all of these class members, i.e.: one of these strings:
           'class method'    created via classmethod()
           'static method'   created via staticmethod()
           'property'        created via property()
           'method'          any other flavor of method
           'data'            not a method
    '''
    ret = {}
    for methTuple in inspect.classify_class_attrs(cls):
        ret[methTuple[0]] = methTuple[1]
    return ret

##
# @param annotatedObj Python "object" (it may be a module, class, or instance) whose functions we're annotating.
# @param funcName annotatedObj's function to query.
# @return Attribute kind for the function, see function documentation for the values.
def _getInspectMethodType(annotatedObj, funcName):
    '''
    Get the kind of attribute for this function, i.e.: one of these strings:
           'class method'    created via classmethod()
           'static method'   created via staticmethod()
           'property'        created via property()
           'method'          any other flavor of method
    '''
    methodsType = None
    methodType = 'method'
    cls = _getClassForAnnotatedObj(annotatedObj)
    if cls is not None:
        methodsType = _getClassMethodsType(cls)
        methodType = methodsType[funcName]
    return methodType

##
# @param obj Python "object" (it may be a module, class, or instance) whose functions we're annotating.
# @param funcName obj's function to query.
# @return The suitable FunctionCall.MethodType for the function, see function documentation for the values.
def _getFunctionCallMethodType(obj, funcName):
    '''
    Get 'code_cropper' method type for an objet's function.
    Get the 'inspect' module method type, and then translate it to FunctionCall.MethodType.
    There's a special type 'Constructor' for the object's constructor (__init__)
    This is the mapping:
        Inspect's 'static method' -> FunctionCall.MethodType.STATIC_METHOD
        Inspect's 'class method'  -> FunctionCall.MethodType.CLASS_METHOD
        Inspect's 'property'      -> FunctionCall.MethodType.PROPERTY
        Inspect's 'method'        -> FunctionCall.MethodType.METHOD
        Constructor (__init__)    -> FunctionCall.MethodType.CONSTRUCTOR
    '''
    MT = FunctionCall.MethodType
    imt = _getInspectMethodType(obj, funcName)
    if imt == 'static method':
        return MT.STATIC_METHOD
    if imt == 'class method':
        return MT.CLASS_METHOD
    if imt == 'property':
        return MT.PROPERTY
    assert imt == 'method'
    if funcName == PythonConstants.CONSTRUCTOR_SIGNATURE:
        return MT.CONSTRUCTOR
    return MT.METHOD

##
# @param obj Python "object" (it may be a module, class, or instance) whose functions we're annotating.
# @return call_graph.LanguageType (MODULE, CLASS, INSTANCE) for the parameter object.  
def _getLanguageType(obj):
    '''
    Get LanguageType (MODULE, CLASS, INSTANCE) for a Python object.
    '''
    if inspect.ismodule(obj):
        return LanguageType.MODULE
    if inspect.isclass(obj):
        return LanguageType.CLASS
    return LanguageType.INSTANCE

class AnnotatorThread(Thread):
    '''
    Thread class to annotate the functions. It may work in a multi-threaded
    environment, because it uses Python threading queues.
    '''
    #Constants
    class Containers:
        '''
        Type of container. Language Objects and Function Calls are stored separately.
        '''
        LANGUAGE_OBJECTS, FUNCTION_CALLS = range(2)
    
    class QueueInfo:
        '''
        Indices in the item data stored in the queue.
        Each one represents different information for function calls.
        '''
        class MessageTypes:
            '''
            Type of queue message.
            '''
            ENTER_FUNCTION, EXIT_FUNCTION, END_ANNOTATION = range(3)
        #Index in Queue item list
        MESSAGE_TYPE,\
        INDEX_OBJ,\
        INDEX_FUNC_NAME,\
        INDEX_FUNC_CALL,\
        INDEX_ANNOTATION_ID,\
        INDEX_ARGS,\
        INDEX_KARGS,\
        INDEX_THREW,\
        INDEX_RETURNED_OBJ = range(9)

    ##
    # @param self The AnnotatorThread to construct.
    # @param aProgramExecution ProgramExecution instance where the Call Graph will be stored.
    # @param callGraphQueue Message queue for other threads to inform about function calls to store.
    def __init__(self, aProgramExecution, callGraphQueue):
        '''
        Constructor.
        '''
        Thread.__init__(self)
        self.nextIdsMap_ = {}
        self.nextIdsMap_[AnnotatorThread.Containers.LANGUAGE_OBJECTS] = 1
        self.nextIdsMap_[AnnotatorThread.Containers.FUNCTION_CALLS] = 1
        self.annotationIdToFuncCall_ = {}
        self.pythonIdToLanguageObjectId_ = {} 
        self.programExecution_ = aProgramExecution
        self.callGraphQueue_ = callGraphQueue
        self.currentFunctionLevel_ = ProgramExecution.MIN_LEVEL - 1
        self.annotationEnded_ = False

    ##
    # @param self The AnnotatorThread instance.
    def run(self):
        '''
        "Almost infinite" loop for processing the queue messages.
        It may only be broken with an "END_ANNOTATION" message.
        '''
        while not self.annotationEnded_:
            item = self.callGraphQueue_.get()
            self._processQueueItem(item)
            self.callGraphQueue_.task_done()

    ##
    # @param self The AnnotatorThread instance.
    # @param item Queue item to process.
    def _processQueueItem(self, item):
        '''
        Process queue item. It's a dict mapping QueueInfo constants to custom data.
        The most important data is MESSAGE_TYPE, to indicate begin or end of annotations, or function process.
        '''
        msgType = item[AnnotatorThread.QueueInfo.MESSAGE_TYPE]
        
        #Special message for commanding this thread to terminate
        if msgType == AnnotatorThread.QueueInfo.MessageTypes.END_ANNOTATION:
            self.annotationEnded_ = True
            return
        
        if msgType == AnnotatorThread.QueueInfo.MessageTypes.ENTER_FUNCTION:
            self.currentFunctionLevel_ += 1 
            obj = item[AnnotatorThread.QueueInfo.INDEX_OBJ]
            annotationId = item[AnnotatorThread.QueueInfo.INDEX_ANNOTATION_ID]
            funcName = item[AnnotatorThread.QueueInfo.INDEX_FUNC_NAME]
            methodType = _getFunctionCallMethodType(obj, funcName)
            args = item[AnnotatorThread.QueueInfo.INDEX_ARGS]
            kargs = item[AnnotatorThread.QueueInfo.INDEX_KARGS]
            
            lo = self._declareObjectAndParents(obj, isCallee = True)
            argsList = []
            for arg in args:
                argLanguageObject = self._declareObjectAndParents(arg, isCallee = False)
                argsList.append(Argument(argLanguageObject))
            
            for argName, karg in kargs.items():
                argLanguageObject = self._declareObjectAndParents(karg, isCallee = False)
                argsList.append(Argument(argLanguageObject, argName))
    
            newFunctionCallId = self._getNewId(AnnotatorThread.Containers.FUNCTION_CALLS)
            aCall = FunctionCall(newFunctionCallId, lo, funcName, methodType, argsList, self.currentFunctionLevel_)
            self.programExecution_.addFunctionCall(aCall)
            self.annotationIdToFuncCall_[annotationId] = aCall
        else:
            assert msgType == AnnotatorThread.QueueInfo.MessageTypes.EXIT_FUNCTION
            annotationId = item[AnnotatorThread.QueueInfo.INDEX_ANNOTATION_ID]
            funcCall = self.annotationIdToFuncCall_[annotationId]
            threwException = item[AnnotatorThread.QueueInfo.INDEX_THREW]
            returnedObject = item[AnnotatorThread.QueueInfo.INDEX_RETURNED_OBJ]
            returnedObjectLo = self._declareObjectAndParents(returnedObject, isCallee = False)
            funcCall.setReturnedObject(returnedObjectLo)
            funcCall.setThrewException(threwException)
            self.currentFunctionLevel_ -= 1

    ##
    # @param self The AnnotatorThread instance.
    # @param obj Python "object" (module, class, or instance) to declare.
    # @param isCallee Obj is the callee, i.e.: the receiver of the message (the function call).
    # @return The newly declared LanguageObject.
    def _declareObjectAndParents(self, obj, isCallee):
        '''
        Recursive function to get a LanguageObject. If not previously declared,
        "declare" a Python object (module, class or instance),
        but declaring first its parent (and here is where the recursion appears).
        For containers:
            * declare children.
            * replace original container for a container of language object id's.      
        '''
        ##
        # @param obj Python "object" (module, class, or instance) to declare
        # @param objType Obj's object type returned by type() function.
        def getPythonUniqueId(obj, objType):
            '''
            Get a unique id for the object, to identify it in the containers.
            We use id's for instances, and str for all other objects (classes, modules, native types, etc.)
            We cannot use ID for every object, because garbage collector may free the memory after returning from a function.
            For instance:
                def f():
                    i = 5
                    vector = [1, i]
                    annotatedFunction(i, vector)
                f()
                f()
                After the first call, the garbage collector may free the memory for i and vector,
                hence: were we to use id() to identify objects, arguments for annotatedFunction() from the first and second call to f()
                may be recognized as different, when they are logically the same.
            '''
            if objType is types.InstanceType:
                return "ID:" + str(id(obj))
            else:
                return "ST:" + str(obj)
            
        objToDeclare = obj
        objType = type(obj)
        if objType is types.TupleType:
            auxList = []
            for child in obj:
                #Recursive call
                childLo = self._declareObjectAndParents(child, False)
                auxList.append(childLo.getId())
            objToDeclare = tuple(auxList)
        elif objType is types.ListType:
            objToDeclare = []
            for child in obj:
                #Recursive call
                childLo = self._declareObjectAndParents(child, False)
                objToDeclare.append(childLo.getId())
        elif objType is types.DictType:
            objToDeclare = {}
            for key, value in obj.items():
                #Recursive calls
                keyLo = self._declareObjectAndParents(key, False)
                valueLo = self._declareObjectAndParents(value, False)
                objToDeclare[keyLo.getId()] = valueLo.getId()

        #Declare current obj, if not declared before
        pythonId = getPythonUniqueId(objToDeclare, objType)
        if self.pythonIdToLanguageObjectId_.has_key(pythonId):
            return self.programExecution_.getLanguageObjects()[self.pythonIdToLanguageObjectId_[pythonId]]

        #obj
        objType = _getLanguageType(obj)
        declarationType, declarationCode = self._getDeclarationInfo(pythonId, objToDeclare, objType, isCallee)
        
        parentLo = None
        if self._hasParent(obj, objType):
            parent = self._getParent(obj, objType)
            parentLo = self._declareObjectAndParents(parent, isCallee = False) 
        #Recursive call
        newId = self._getNewId(AnnotatorThread.Containers.LANGUAGE_OBJECTS)
        lo =  LanguageObject(newId, objType, declarationType, declarationCode, parentLo)
        self.programExecution_.addLanguageObject(lo)
        self.pythonIdToLanguageObjectId_[pythonId] = newId
        return lo

    ##
    # @param self The AnnotatorThread instance.
    # @param containerType Container type (for Language objects or Function calls).
    # @return The new id for the containerType.
    def _getNewId(self, containerType):
        '''
        Get a new id to be used for a new LanguageObject or FunctionCall,
        according to the containerType (Containers.LANGUAGE_OBJECTS or Containers.FUNCTION_CALLS).
        '''
        newId = self.nextIdsMap_[containerType]
        self.nextIdsMap_[containerType] += 1
        return newId

    ##
    # @param self The AnnotatorThread instance.
    # @param pythonId Unique id to identify Python objects.
    # @param obj Object to declare.
    # @param objType Obj's object type returned by type() function.
    # @param isCallee Is the callee, i.e.: the receiver of the message (the function call).
    # @return A tuple (declarationType, declarationCode) for this object.
    def _getDeclarationInfo(self, pythonId, obj, objType, isCallee ):
        '''
        Returns a tuple declarationType, declarationCode with information to declare obj parameter.
        For declarationType values, see LanguageObject.DECLARATION_TYPES enum.
        The declarationCode is a string with the object representation.
        For instance: for obj == 5 -> (FIXED_VALUE, "5")
                          obj == int class -> (FIXED_VALUE, "int")
                          obj == instance -> (CONSTRUCTOR, "None")
        NOTE: For constructor, declarationCode doesn't matter, because the object will be declared
        with the constructor notation: var1 = MyClass()
        But for the FIXED_VALUE's, this code is used to declare:
            var2 = 5 ("5" is read from declarationCode).
        '''
        #It has not been declared before
        assert not self.pythonIdToLanguageObjectId_.has_key( pythonId )

        DT = LanguageObject.DECLARATION_TYPES
        #Default values
        declarationType = DT.FIXED_VALUE
        objToDump = None
        if objType == LanguageType.MODULE:
            objToDump = obj.__name__
        elif objType == LanguageType.CLASS:
            moduleName = obj.__module__
            modulePrefix = "" if moduleName == PythonConstants.BUILTINS_MODULE_NAME else moduleName + "." 
            objToDump = modulePrefix + obj.__name__
        else:
            assert objType == LanguageType.INSTANCE
            if isCallee:
                #We always annotate __main__ function
                declarationType = DT.CONSTRUCTOR
            else:
                objToDump = obj
        #TODO GERVA: Object rules configurables
        #Argument. We have two options
        # If it's an object to annotate, it should have been annotated before
        # Otherwise, try (in this precedence order):
        # * JSON (Fixed value)
        # * Dummy object
        ok = True
        try:
            declarationCode = asJsonString(objToDump)
        except:
            declarationType = DT.DUMMY
            declarationCode = asJsonString('Dummy')
        return declarationType, declarationCode
    
    ##
    # @param self The AnnotatorThread instance.
    # @param obj Python "object" (module, class, or instance).
    # @param objType Obj's object type returned by type() function.
    # @return The obj's parent, or None if it's a module/
    def _getParent(self, obj, objType):
        '''
        Python objects do have a hierarchical structure:
            Module 
              |
            Class
              |
            Instance
        This function returns the parent for any object (None for the "root" modules).
        '''
        assert self._hasParent(obj, objType)
        if objType == LanguageType.CLASS:
            return sys.modules[obj.__module__]
        return obj.__class__

    ##
    # @param self The AnnotatorThread instance.
    # @param obj Python "object" (module, class, or instance).
    # @param objType Obj's object type returned by type() function.
    # @return True if the object has parent, i.e.: it's not a module (see documentation for _getParent()).
    def _hasParent(self, obj, objType):
        '''
        Return whether or not the object has parent, i.e.: it's not a module.
        '''
        return objType != LanguageType.MODULE
    
class Annotator:
    '''
    Interface for the calling programmer code to annotate the functions, i.e.:
    replace them with a similar code that stores the function call in a container,
    to persist it later in a database. 
    It may work in a multi-threaded environment, because it calls AnnotatorThread class,
    that uses Python threading queues.
    It implements the "with" statement interface (RAII pattern in Python).
    '''
    activeAnnotators = False
    ##
    # @param self The Annotator instance to construct.
    def __init__(self):
        '''
        Constructor.
        '''
        self.oldFuncs = {}
        self.funcsToAnnotate = []
        self.callGraphQueue_ = Queue()
        self.programExecution_ = None
        self.annotatorThread_ = None

    ##
    # @param self The Annotator instance.
    # @param obj Python "object" (module, class, or instance).
    # @param *methodNames If None, annotate all obj's methods, else only the ones contained in *methodNames.
    def annotate(self, obj, *methodNames):
        '''
            Annotate an obj's methods (with an optional methodNames filter).
        '''
        if methodNames:
            for methodName in methodNames:
                self._annotateMethod(obj,methodName)
        else:
            objDict = inspect.getmembers(obj,inspect.isroutine)
            for name, _ in objDict:
                self._annotateMethod(obj,name)

    ##
    # @param self The Annotator instance.
    def __enter__(self):
        '''
        Entry point for the "with" sentence. It starts the annotations.
        '''
        self.startAnnotations()

    ##
    # @param self The Annotator instance.
    def startAnnotations(self):
        '''
        Start an annotations process. Replace the functions stored in self.funcsToAnnotate
        with a new function returned by annotatedFunction() method.
        Use the Python native getattr() and setattr() methods to get and replace
        the functions for an object.
        '''
        if Annotator.activeAnnotators:
            #Limit instances number to 1
            raise Exception('Only one annotator instance allowed.') 
        Annotator.activeAnnotators = True
        try:
            #Functions
            for objAndFuncName in self.funcsToAnnotate:
                obj, funcName = objAndFuncName
                fun = getattr( obj, funcName )
                theLanguageType = _getLanguageType(obj)
                methodType = _getInspectMethodType( obj, funcName )
                
                newFun = annotatedFunction(self, obj, fun)
                if methodType == 'static method':
                    newFun = staticmethod( newFun )
                elif methodType == 'class method':
                    newFun = classmethod( newFun )
                elif methodType == 'method' and theLanguageType == LanguageType.INSTANCE:
                    newFun = types.MethodType(newFun, obj, obj.__class__)
                setattr(obj, funcName, newFun )
                #Backup old and new functions, in order to restore them later
                self.oldFuncs[objAndFuncName] = (fun, methodType)
            return self
        except Exception, e:
            self.restoreFunctions()
            raise e

    ##
    # @param self The Annotator instance.
    def __exit__(self, _, __, ___):
        '''
        Exit point for the "with" sentence. It finishes the annotations.
        '''
        self.finishAnnotations()

    ##
    # @param self The Annotator instance.
    def finishAnnotations(self):
        '''
        Finish the annotations process, by sending an "End Process" message to AnnotatorThread.
        Finally, restore the original functions.
        '''
        try:
            Annotator.activeAnnotators = False
            item = {}
            item[AnnotatorThread.QueueInfo.MESSAGE_TYPE] = AnnotatorThread.QueueInfo.MessageTypes.END_ANNOTATION
            self.callGraphQueue_.put( item )

            #Wait for the thread to process all messages
            self.annotatorThread_.join()
            
        finally:
            self.restoreFunctions()

    ##
    # @param self The Annotator instance.
    # @param annotationId Annotation id: it'll be necessary later in the "end function" message, to know which function is ending. 
    # @param obj Python "object" (it may be a module, class, or instance) whose functions we're annotating
    # @param funcName Function name 
    # @param *args Arguments list.
    # @param **kwargs Named arguments.
    def functionStarted(self, annotationId, obj, funcName, *args, **kwargs):
        '''
        Send a "Function started" message to the queue, to start this function annotations.
        '''
        item = {}
        item[AnnotatorThread.QueueInfo.MESSAGE_TYPE] = AnnotatorThread.QueueInfo.MessageTypes.ENTER_FUNCTION
        item[AnnotatorThread.QueueInfo.INDEX_OBJ] = obj
        item[AnnotatorThread.QueueInfo.INDEX_ANNOTATION_ID] = annotationId
        item[AnnotatorThread.QueueInfo.INDEX_FUNC_NAME] = funcName
        item[AnnotatorThread.QueueInfo.INDEX_ARGS] = args
        item[AnnotatorThread.QueueInfo.INDEX_KARGS] = kwargs
        self.callGraphQueue_.put( item )

    ##
    # @param self The Annotator instance.
    # @param annotationId Annotation id: to identify the function.
    # @param threwException The function has raised an exception.
    # @param returnedObject If threwException is False, the object returned by the function. If True, the exception being raised.
    def functionEnded(self, annotationId, threwException, returnedObject):
        '''
        Send a "Function ended" message to the queue. Pass also the "returned object" (or exception) information.
        '''
        #TODO GERVA: in multi-threading, use thread id, obj and funcName to identify which function really ended
        item = {}
        item[AnnotatorThread.QueueInfo.MESSAGE_TYPE] = AnnotatorThread.QueueInfo.MessageTypes.EXIT_FUNCTION
        item[AnnotatorThread.QueueInfo.INDEX_ANNOTATION_ID] = annotationId
        item[AnnotatorThread.QueueInfo.INDEX_THREW] = threwException
        item[AnnotatorThread.QueueInfo.INDEX_RETURNED_OBJ] = returnedObject
        self.callGraphQueue_.put( item )

    ##
    # @param self The Annotator instance.
    def resetForNewAnnotations(self):
        '''
        Reset function to start new annotations.
        '''
        self.oldFuncs = {}
        self.funcsToAnnotate = []
        self.callGraphQueue_ = Queue()
        self.programExecution_ = ProgramExecution( ProgramExecution.Languages.PYTHON )
        self.annotatorThread_ = AnnotatorThread(self.programExecution_, self.callGraphQueue_)
        self.annotatorThread_.start()

    ##
    # @param self The Annotator instance.  
    def restoreFunctions(self):
        '''
        After the annotations process has completed, restore the original functions.
        '''
        for objAndFuncName in self.funcsToAnnotate:
            obj, funcName = objAndFuncName
            oldFun, methodType = self.oldFuncs[objAndFuncName]
            #Restore old function
            try:
                if methodType == 'static method':
                    #Otherwise, it'll remain unbouned, and get this annoying message:
                    #"TypeError: unbound method newFunction() must be called with ... instance as first argument (got nothing instead)"
                    oldFun = staticmethod( oldFun )

                setattr(obj, funcName, oldFun )
            except Exception, e:
                print 'restoreFunctions exception: ' + str(e)

    ##
    # @param self The Annotator instance.
    # @param obj Python "object" (it may be a module, class, or instance) whose functions we're annotating.
    # @param functionName Function name.
    def _annotateMethod(self, obj, functionName):
        '''
        Add a function to a container, to be annotated later.
        '''
        self.funcsToAnnotate.append( (obj,  functionName) )

    ##
    # @param self The Annotator instance.
    # @param dumpFileName File where the call graph database will be dumped.
    # @param preserveOldDumpFiles If True (default), it does not overwrite old dump files -it uses index numbers in the filename, as (1), to generate a new name-.
    def dumpProgramExecution(self, dumpFileName, preserveOldDumpFiles):
        '''
        Serialize the call graph into a database (Json file indicated in "dumpFileName" parameter).
        '''
        aSerializer = CallGraphSerializer()
        #Get a valid file path, to avoid overwriting:
        #This allows having a number of different executions for a given set of annotations
        if preserveOldDumpFiles:
            dumpFileName = file_utils.getUniqueDumpFileName(dumpFileName)
        with open(dumpFileName, 'w') as jsonFileOut:
            aSerializer.dump(self.programExecution_, jsonFileOut)

class Annotation:
    '''
    RAII idiom implemented with the 'with' statement.
    It represents an annotation for a function call.
    In the __exit__(), it tells the annotator that the function has ended.
    '''
    ##
    # @param self The Annotation instance
    # @param theAnnotator Annotator instance that will process the "end function" message.
    def __init__(self, theAnnotator):
        '''
        Constructor.
        '''
        self.annotator_ = theAnnotator
        self.threwException_ = False
        self.returnedObject_ = None
        self.functionCall_ = None

    ##
    # @param self The Annotation instance.
    def __enter__(self):
        '''
        Entry point for the "with" sentence. It just passes: the important
        function is __exit__().
        '''
        return self

    ##
    # @param self The Annotation instance.
    # @param threwException The function has raised an exception.
    # @param returnedObject If threwException is False, the object returned by the function. If True, the exception being raised.
    def setFunctionReturnedInfo(self, threwException, returnedObject):
        '''
        Set information after a function returns, whether it has raised exception or not.
        '''
        self.threwException_ = threwException
        self.returnedObject_ = returnedObject

    ##
    # @param self The ProgramExecutionDumper instance.
    # @param type Exception type, if an exception has been raised.
    # @param value Exception value, if an exception has been raised.
    # @param tb Traceback, if an exception has been raised.
    def __exit__(self, type, value, tb):
        '''
        Exit point for the "with" sentence. It tells the annotator instance
        that the function has just ended.
        '''    
        self.annotator_.functionEnded(id(self), self.threwException_, self.returnedObject_)

##
# @param theAnnotator Annotator instance that will handle the annotations.
# @param annotatedObj Python "object" (it may be a module, class, or instance) whose functions we're annotating.
# @param f Function to be annotated.
def annotatedFunction(theAnnotator, annotatedObj, f):
    '''
    THE MOST IMPORTANT FUNCTION: for any given function 'f', it returns an equivalent
    function that calls the original, but it also stores this call in the call graph,
    to later allow its dumping in a database.
    '''
    ##
    # @param *args Arguments list for the original 'f' function, redirected to this replacement method.
    # @param **kwargs Named arguments for the original 'f' function, redirected to this replacement method.
    def newFunction( *args, **kwargs ):
        '''
        KEY FUNCTION: it replaces the original 'f' function. It calls it, but also
        annotates it in "theAnnotator".
        '''
        ann = Annotation( theAnnotator )
        with ann:
            callee = annotatedObj
            theLanguageType = _getLanguageType(annotatedObj)
            inspectMethodType = _getInspectMethodType(annotatedObj, f.__name__)
            
            # Special case: annotating a class, if it's not a class or static method:
            # Use self (1st argument) as the callee
            if theLanguageType == LanguageType.CLASS and not(inspectMethodType == 'class method' or inspectMethodType == 'static method'):
                callee = args[0]

            theAnnotator.functionStarted( id(ann), callee, f.__name__, *args, **kwargs )
            
            #Skip extra first arg (cls or self) before running
            if (inspectMethodType == 'class method') or (theLanguageType == LanguageType.INSTANCE and inspectMethodType == 'method'):
                args = tuple( list(args)[1:] )

            threwException = False
            ret = None
            try:
                ret = f( *args, **kwargs )
            except Exception, e:
                threwException = True
                ret = e
            ann.setFunctionReturnedInfo(threwException, ret)
            if threwException:
                raise ret
            return ret
    return newFunction

annotatorInstance_ = Annotator()

##
# @return: The ONLY Annotator instance.
def annotatorInstance():
    '''
    Return the ONLY Annotator instance (Singleton Pattern).
    '''
    return annotatorInstance_

class ProgramExecutionDumper:
    '''
    RAII idiom implemented with the 'with' statement.
    In the __enter__() point, it tells the annotator instance to enter the annotations process,
    and in the __exit__(), it tells it to exit, and later it dumps the results in a database.
    '''
    ##
    # @param self The ProgramExecutionDumper instance to construct.
    # @param dumpFileName File where the call graph database will be dumped.
    # @param preserveOldDumpFiles If True (default), it does not overwrite old dump files -it uses index numbers in the filename, as (1), to generate a new name-.
    def __init__(self, dumpFileName, preserveOldDumpFiles = True):
        '''
        Constructor.
        '''
        self.dumpFileName_ = dumpFileName
        self.preserveOldDumpFiles_ = preserveOldDumpFiles

    ##
    # @param self The ProgramExecutionDumper instance.
    def __enter__(self):
        '''
        Entry point for the "with" sentence. It tells the annotator instance to enter the annotation process.
        '''
        annotatorInstance().__enter__()
    
    ##
    # @param self The ProgramExecutionDumper instance.
    # @param type Exception type, if an exception has been raised.
    # @param value Exception value, if an exception has been raised.
    # @param tb Traceback, if an exception has been raised.
    def __exit__(self, type, value, tb):
        '''
        Exit point for the "with" sentence. It tells the annotator instance to exit the annotation process,
        and dumps the call graph in a database.
        '''
        annotatorInstance().__exit__(type, value, tb)
        annotatorInstance().dumpProgramExecution(self.dumpFileName_, self.preserveOldDumpFiles_)
