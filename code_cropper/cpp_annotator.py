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
Annotator for C++ sources. It uses SourceCodeParser and a compiler environment.
'''
import os
import shutil
from source_code_parser import SourceCodeParser
from call_graph import ProgramExecution

bkpExtension = ".bra_bkp"

##
# @fileName A file name.
# @return The correspondent backup file name.
def getBackupFileName(fileName):
    '''
    Return the correspondent backup file name.
    '''
    return fileName + bkpExtension 

##
# @param fname File to touch.
# @param times A tuple (access time, modified time) to set to the file.
def touch(fname, times = None):
    '''
    From "Stack Overflow" page.
    Mark a file as modified by changing its timestamp.
    '''
    fhandle = file(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close()


class CppAnnotator:
    '''
    Annotator for C++ classes. It's the C++ counterpart of annotator.Annotator.
    As Annotator, it follows the "with" syntax (RAII idiom for Python):
    inside the "with" scope, the C++ functions are annotated to
    generate a call-graph database. This is the code flow to get this effect:
    
    * Create a CppAnnotator.
    * call annotateMainFile():
        * this backs up the main file name, to be annotated later.
    * call annotateFunctions() or similar annotation functions:
        * this saves these functions in a container, to be annotated later.
    * with myCppAnnotator... this calls __enter__(), where:
        * annotations actually take place:
          * main file and functions from the containers are modified,
          saving a backup for each one of them.
        * build the compiler solution. This generates a new EXE.
    * call the EXE inside the with (for example, using os.system()).
        * this EXE will generate the annotations (remember the annotations and build above).
    * exit the with clause:
        * restore the backups for all the modified files.
        * "touch" the files, to force the compiler to build them.
        * build the solution. This generates an EXE without annotations.
    '''
    activeAnnotators = False
    
    
    ##
    # @param self The CppAnnotator instance to construct.
    # @param mainFilePath The program's main file path.
    # @param mainFunction The program's main function.
    # @param buildSolutionCmd Command to build the solution.
    # @param keepBackupFiles Keep annotated files after restoring the original (at the __exit__() function).
    def __init__(self, mainFilePath, mainFunction, buildSolutionCmd, keepBackupFiles = False):
        '''
        Constructor.
        '''
        self.buildSolutionCmd = buildSolutionCmd
        self.keepBackupFiles = keepBackupFiles
        self.sourceCodeParser = SourceCodeParser(ProgramExecution.Languages.C_PLUS_PLUS, mainFilePath, mainFunction)
        self.filesToAnnotate = []
        self.functionsToAnnotate = []
        self.classesToAnnotate = []
        self.mainFilePath = mainFilePath
        self.dumpFileName = ""
        self.oldFiles = []

    # @param self The CppAnnotator instance.
    # @param dumpFileName File where the call graph database will be dumped.
    def annotateMainFile(self, dumpFileName ):
        '''
        Mark main file to be annotated at __enter__().
        '''
        self.dumpFileName = dumpFileName

    ##
    # @param self The CppAnnotator instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param headerToInclude Header to include.
    def annotateFile(self, originalFileName, headerToInclude):
        '''
        Mark a C++ source file to be annotated __enter__().
        '''
        self.filesToAnnotate.append((originalFileName, headerToInclude))
 
    ##
    # @param self The CppAnnotator instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param headerToInclude Header to include.
    # @param functionNames Function names to filter.
    def annotateFunctions(self, originalFileName, headerToInclude, functionNames = []):
        '''
        Mark a C++ source file to be annotated __enter__(),
        filtering by functions.
        '''
        self.functionsToAnnotate.append((originalFileName, headerToInclude, functionNames))

    ##
    # @param self The CppAnnotator instance.
    # @param originalFileName File name of the original (unprocessed) file name.
    # @param headerToInclude Header to include.
    # @param classNames Class names to filter.
    def annotateClasses(self, originalFileName, headerToInclude, classNames = []):
        '''
        Mark a C++ source file to be annotated __enter__(),
        filtering by classes.
        '''        
        self.classesToAnnotate.append((originalFileName, headerToInclude, classNames))

    ##
    # @param self The CppAnnotator instance.
    def __enter__(self):
        '''
        Entry point for the "with" sentence. It annotates the files, and builds the solution.
        The new EXE will generate the Json database.
        '''
        if CppAnnotator.activeAnnotators:
            #Limit instances number to 1
            raise RuntimeError('Cpp annotators number should limit to 1.')
        CppAnnotator.activeAnnotators = True
        self._resetForNewAnnotations()
        try:
            #Backup main old file, in order to restore it later
            mainBackupFileName = getBackupFileName(self.mainFilePath)
            shutil.copyfile(self.mainFilePath, mainBackupFileName)
            self.oldFiles.append(self.mainFilePath)
            self.sourceCodeParser.annotateMainFile(self.dumpFileName)
            
            #Merge 3 containers in one, and iterate it
            originalFileNameToInfo = {}
            for myFile in self.filesToAnnotate:
                originalFileName, headerToInclude = myFile
                myInfo = [headerToInclude, None, None]
                originalFileNameToInfo[originalFileName] = myInfo

            for myClass in self.classesToAnnotate:
                originalFileName, headerToInclude, classNames = myClass
                if originalFileNameToInfo.has_key(originalFileName):
                    myInfo = originalFileNameToInfo[originalFileName]
                else:
                    myInfo = [headerToInclude, None, None]
                    originalFileNameToInfo[originalFileName] = myInfo
                myInfo[1] = classNames
            
            for myFunction in self.functionsToAnnotate:
                originalFileName, headerToInclude, functionNames = tuple(myFunction)
                if originalFileNameToInfo.has_key(originalFileName):
                    myInfo = originalFileNameToInfo[originalFileName]
                else:
                    myInfo = [headerToInclude, None, None]
                    originalFileNameToInfo[originalFileName] = myInfo
                myInfo[2] = functionNames
            
            for originalFileName, fileInfo in originalFileNameToInfo.items():
                headerToInclude, classNames, functionNames = fileInfo 
                #Backup old files, in order to restore them later
                backupFileName = getBackupFileName(originalFileName)
                shutil.copyfile(originalFileName, backupFileName)
                self.oldFiles.append(originalFileName)
                if classNames is None and functionNames is None:
                    self.sourceCodeParser.annotateFile(backupFileName, originalFileName, headerToInclude)
                else:
                    if classNames is not None:
                        self.sourceCodeParser.annotateCppClasses(backupFileName, originalFileName, headerToInclude, classNames)
                    if functionNames is not None and classNames is None:
                        self.sourceCodeParser.annotateCppFunctions(backupFileName, originalFileName, headerToInclude, functionNames)
            self.buildSolution_()
            return self
        except Exception, e:
            print str(e)
            self.restoreSourcesForSolution_()
            raise e

    ##
    # @param self The CppAnnotator instance.
    # @param type Exception type, if an exception has been raised.
    # @param value Exception value, if an exception has been raised.
    # @param tb Traceback, if an exception has been raised.
    def __exit__(self, type, value, tb):
        '''
        Exit point for the "with" sentence. It restores the backup source files,
        "touches" them to update their timestamps, and builds the solution.
        The new EXE will not generate the annotations.
        '''
        CppAnnotator.activeAnnotators = False
        self.restoreSourcesForSolution_()
        self.buildSolution_()

    ##
    # @param self The CppAnnotator instance.
    def _resetForNewAnnotations(self):
        '''
        Code to reset annotations.
        Unused for now.
        '''
        pass
       
    ##
    # @param self The CppAnnotator instance.
    def restoreSourcesForSolution_(self):
        '''
        Restore the backup source files, and "touch" them to 
        update their timestamps (a later solution building will force
        rebuilding for them).
        '''
        for fileName in self.oldFiles:
            if self.keepBackupFiles:
                shutil.copyfile(getBackupFileName(fileName), fileName)
            else:
                shutil.move(getBackupFileName(fileName), fileName)
            touch(fileName)

    ##
    # @param self The CppAnnotator instance.
    def buildSolution_(self):
        '''
        External call to the compiler to build the solution.
        It "touches" the main file first, to force rebuilding it.
        '''
        touch(self.mainFilePath)
        os.system(self.buildSolutionCmd)
        pass