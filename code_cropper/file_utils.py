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
File-related utilities.
"""
import os

##
# @param dumpFileName File where the call graph database will be dumped.
# @return A unique file name as similar to dumpFileName as possible (add (1), (2), etc. to avoid repetition).
def getUniqueDumpFileName(dumpFileName):
    """
    Get a unique file name for a Json database.
    Add "(1)", "(2)", etc. to the file name, to avoid repetition.
    """
    ##
    # @param fileName File name to split.
    # @return A tuple (basename, extension) after splitting the fileName.   
    def getBasenameAndExtension(fileName):
        """
        Returns a tuple (basename, extension) after splitting the fileName.
        """
        extIndex = filename.rfind('.')
        if extIndex == -1:
            basename = filename
            extension = ""
        else:
            basename = fileName[:extIndex]
            extension = filename[extIndex:]
        return basename, extension
        
    uniqueDumpFileName = dumpFileName
    folder = os.path.dirname(dumpFileName)
    filename = os.path.basename(dumpFileName)
    basename, extension = getBasenameAndExtension(filename)

    exists = True
    while exists:
        exists = os.path.exists(uniqueDumpFileName)
        filename = os.path.basename(uniqueDumpFileName)
        basename, extension = getBasenameAndExtension(filename)
        if exists:
            addSeparators = False
            leftSep = basename.rfind("(")
            rightSep = basename.rfind(")")
            if leftSep == -1 or rightSep < leftSep:
                addSeparators = True
            else:
                currentIndexStr = basename[leftSep + 1: rightSep]
                try:
                    currentIndex = int(currentIndexStr);
                    currentIndex += 1
                    basename = basename[:leftSep + 1] + str(currentIndex) + basename[rightSep:]
                except ValueError:
                    addSeparators = True
            if addSeparators:
                basename += "(1)"
            uniqueDumpFileName = os.path.join(folder, basename + extension)
    return uniqueDumpFileName