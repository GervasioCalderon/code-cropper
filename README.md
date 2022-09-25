# Code Cropper

Code Cropper is an open-source software tool that extracts behavior from live Python running code, generating a program/unit-test equivalent to the original, but only with the functions and/or classes selected by the user. It dumps the program execution as a Json database, to be extracted later with a code generator.

It can be used for automated generation of unit tests from real code execution, logging, and many other code-inspection use cases.

## Example

We have this program in Python:

```python
# Module utils.py
def launchGUI():
    print('Please wait. Launching GUI.')
    print('This might take several minutes.')

def dummy_function():
    print('LOL')

def critical_function():
    print('WARNING! This is critical.')

class ImportantClass:
    def __init__(self):
        print('This class is important.')

    def important_function(self, i):
        print('This function is really important.')

class DummyClass:
    def __init__(self):
        print('This class is just a joke.')

    def dummy_function(self, i):
        print('LOL')


import os
def my_os_path_join(a, b):
    print(os.path.join(a, b))

# module main.py
import utils
from utils import ImportantClass, DummyClass, my_os_path_join

def main():
    my_os_path_join('/etc/', 'hosts')
    i = 1
    a = ImportantClass()
    utils.dummy_function()
    utils.dummy_function()
    utils.launchGUI()
    i += 4
    utils.critical_function()
    b = DummyClass()
    utils.critical_function()
    b.dummy_function(i)
    a.important_function(i)

if __name__ == "__main__":
    main()
```

If we want to isolate only the important functions and classes, code_cropper is the solution:

```python
import code_cropper.annotator
import code_cropper.code_generator
from io import StringIO

import utils
from utils import ImportantClass, DummyClass, my_os_path_join
import os

def main():
    my_annotator = code_cropper.annotator.annotatorInstance()
    my_annotator.resetForNewAnnotations()
    my_annotator.annotate(utils, 'critical_function')
    my_annotator.annotate(os.path, 'join')
    my_annotator.annotate(ImportantClass)
    JSON_RUNNING = "my_running.json"
    with code_cropper.annotator.ProgramExecutionDumper(JSON_RUNNING) as my_dumper:
        my_os_path_join('/etc/', 'hosts')
        i = 1
        a = ImportantClass()
        utils.dummy_function()
        utils.dummy_function()
        utils.launchGUI()
        i += 4
        utils.critical_function()
        b = DummyClass()
        utils.critical_function()
        b.dummy_function(i)
        a.important_function(i)
    #my_running.json does contain now the execution limited to the important classes and functions.
    #Generate equivalent program and unit test
    def generate_equiv_code(source_type):
        with open(JSON_RUNNING, 'r') as dumpFile:
            #Get equivalent program
            my_code_generator = code_cropper.code_generator.CodeGenerator(dumpFile)
            equiv_program_io = StringIO()
            my_code_generator.generateEquivalentProgram(equiv_program_io,
                                                        code_cropper.annotator.ProgramExecution.MIN_LEVEL, source_type)
            equiv_program_str = equiv_program_io.getvalue()
            equiv_program_io.close()
            print(equiv_program_str)
    #Generate equivalent program and unit test
    print('--------------------')
    print('EQUIVALENT PROGRAM:')
    generate_equiv_code(code_cropper.code_generator.GeneratedSourceType.MAIN_FILE)
    print('--------------------')
    print('EQUIVALENT UNIT TEST:')
    generate_equiv_code(code_cropper.code_generator.GeneratedSourceType.UNIT_TEST)

if __name__ == "__main__":
    main()
```

Output for the sample is this:

```python
This class is important.
LOL
LOL
Please wait. Launching GUI.
This might take several minutes.
WARNING! This is critical.
This class is just a joke.
WARNING! This is critical.
LOL
This function is really important.
--------------------
EQUIVALENT PROGRAM:
import posixpath
import utils

posixpath.join('/etc/', 'hosts')
var2 = utils.ImportantClass()
utils.critical_function()
utils.critical_function()
var2.important_function(5)

--------------------
EQUIVALENT UNIT TEST:
import unittest
import posixpath
import utils

class UNIT_TEST_CASE(unittest.TestCase):
    def test_main(self):
        self.assertEqual('/etc/hosts', posixpath.join('/etc/', 'hosts'))
        var3 = utils.ImportantClass()
        self.assertEqual(None, utils.critical_function())
        self.assertEqual(None, utils.critical_function())
        self.assertEqual(None, var3.important_function(5))

if __name__ == '__main__':
    unittest.main()
```

Id est: the equivalent code could be sent to a new Python file to:
 * analyze the parameters;
 * simplify the original code;
 * generate an automatic Unit Test

And there was no need to have access to the source code of the functions/classes (we could even annotate a standard library function `os.path.join`). This is because we're decorating in runtime with the help of `getattr/setattr`, replacing any function in runtime by another function that executes the same code but it also saves the function calls/args.

## Json database for running
The Json database generated (in the example, file in "/tmp/my_running.json") contains all the information needed to reproduce the program execution. It uses a hierarchy module -> class -> function, and all these "objects" are represented in the Database, being the model normalized. Every object (a module, class or function) has a unique id, and it is registered only once. This is the Json generated from the example:

```json
{
    "callGraph": [
        {
            "arguments": {
                "args": [
                    4,
                    5
                ],
                "kargs": {}
            },
            "calleeId": 1,
            "funcName": "join",
            "id": 1,
            "level": 0,
            "methodType": "method",
            "returnedObject": 6,
            "threwException": false
        },
        {
            "arguments": {
                "args": [
                    9
                ],
                "kargs": {}
            },
            "calleeId": 9,
            "funcName": "__init__",
            "id": 2,
            "level": 0,
            "methodType": "constructor",
            "returnedObject": 11,
            "threwException": false
        },
        {
            "arguments": {
                "args": [],
                "kargs": {}
            },
            "calleeId": 7,
            "funcName": "critical_function",
            "id": 3,
            "level": 0,
            "methodType": "method",
            "returnedObject": 11,
            "threwException": false
        },
        {
            "arguments": {
                "args": [],
                "kargs": {}
            },
            "calleeId": 7,
            "funcName": "critical_function",
            "id": 4,
            "level": 0,
            "methodType": "method",
            "returnedObject": 11,
            "threwException": false
        },
        {
            "arguments": {
                "args": [
                    9,
                    13
                ],
                "kargs": {}
            },
            "calleeId": 9,
            "funcName": "important_function",
            "id": 5,
            "level": 0,
            "methodType": "method",
            "returnedObject": 11,
            "threwException": false
        }
    ],
    "language": "Python",
    "languageObjects": [
        {
            "declarationCode": "posixpath",
            "declarationType": "FIXED_VALUE",
            "id": 1,
            "languageTypeId": 1,
            "parentId": 0
        },
        {
            "declarationCode": "builtins",
            "declarationType": "FIXED_VALUE",
            "id": 2,
            "languageTypeId": 1,
            "parentId": 0
        },
        {
            "declarationCode": "str",
            "declarationType": "FIXED_VALUE",
            "id": 3,
            "languageTypeId": 2,
            "parentId": 2
        },
        {
            "declarationCode": "/etc/",
            "declarationType": "FIXED_VALUE",
            "id": 4,
            "languageTypeId": 3,
            "parentId": 3
        },
        {
            "declarationCode": "hosts",
            "declarationType": "FIXED_VALUE",
            "id": 5,
            "languageTypeId": 3,
            "parentId": 3
        },
        {
            "declarationCode": "/etc/hosts",
            "declarationType": "FIXED_VALUE",
            "id": 6,
            "languageTypeId": 3,
            "parentId": 3
        },
        {
            "declarationCode": "utils",
            "declarationType": "FIXED_VALUE",
            "id": 7,
            "languageTypeId": 1,
            "parentId": 0
        },
        {
            "declarationCode": "utils.ImportantClass",
            "declarationType": "FIXED_VALUE",
            "id": 8,
            "languageTypeId": 2,
            "parentId": 7
        },
        {
            "declarationCode": null,
            "declarationType": "CONSTRUCTOR",
            "id": 9,
            "languageTypeId": 3,
            "parentId": 8
        },
        {
            "declarationCode": "NoneType",
            "declarationType": "FIXED_VALUE",
            "id": 10,
            "languageTypeId": 2,
            "parentId": 2
        },
        {
            "declarationCode": null,
            "declarationType": "FIXED_VALUE",
            "id": 11,
            "languageTypeId": 3,
            "parentId": 10
        },
        {
            "declarationCode": "int",
            "declarationType": "FIXED_VALUE",
            "id": 12,
            "languageTypeId": 2,
            "parentId": 2
        },
        {
            "declarationCode": 5,
            "declarationType": "FIXED_VALUE",
            "id": 13,
            "languageTypeId": 3,
            "parentId": 12
        }
    ],
    "languageTypes": [
        {
            "id": 0,
            "name": "None"
        },
        {
            "id": 1,
            "name": "Module"
        },
        {
            "id": 2,
            "name": "Class"
        },
        {
            "id": 3,
            "name": "Instance"
        }
    ]
}
```

## Implementation

Tested in this environment:
 * Python 3.8.10
 * Ubuntu 20.04.05 LTS

It uses:
 * metaprogramming libraries, such as inspect and types;
 * Json format for storing the call graph;
 * multithreading queues, to decouple calls to the original function from the call graph storing.

## Future work

This is the remaining work:
 * add lint/pep8 and fix all warnings;
 * make indentation configurable (tabs or spaces)
 * test with heavy load;
 * use Kafka or similar methods to decouple the logging from the execution, making it less CPU/memory consuming;
 * other small fixes/enhancements in https://github.com/GervasioCalderon/code-cropper/issues.
 
And some ideas to improve its capabilities:
 * simplify the annotation invocations, for instance: annotate all classes and functions of a module recursively;
 * implement a mockyfier, reading from the Json file to mimic a previous execution;
 * add profiling capabilities.
