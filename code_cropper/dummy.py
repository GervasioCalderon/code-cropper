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
Based on Null object, from Dinu C. Gherman, August 2001
This is used for dummy parameters. It's better than None, because it does not throw exceptions when
its methods are called.
"""
class Dummy:
    """
    Dummy class to represent parameters that we don't know how to create.
    Unlike "None", it does not break after receiving a call: it just passes.
    """
    ##
    # @param self The Dummy instance to constructor.
    # @param *args Arguments list.
    # @param **kwargs Named arguments.
    def __init__(self, *args, **kwargs):
        """
        Constructor.
        """
        return None

    ##
    # @param self The Dummy instance.
    # @param *args Arguments list.
    # @param **kwargs Named arguments.
    def __call__(self, *args, **kwargs):
        """
        Object calling
        """
        return self

    ##
    # @param self The Dummy instance.
    # @param mname Attribute name.
    def __getattr__(self, mname):
        """
        Attribute handling.
        """
        return self

    ##
    # @param self The Dummy instance.
    # @param name Attribute name
    # @param value Attribute value to set.
    def __setattr__(self, name, value):
        """
        Set an attribute.
        """
        return self

    # @param self The Dummy instance.
    # @param name Attribute name to delete.
    def __delattr__(self, name):
        """
        Delete attribute.
        """
        return self

    # @param self The Dummy instance.
    # @return The instance representation.
    def __repr__(self):
        """
        Instance representation.
        """
        return "<Dummy>"

    # @param self The Dummy instance.
    # @return A string representation for the instance. 
    def __str__(self):
        """
        String representation.
        """
        return "Dummy"
