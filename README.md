# Code Cropper

Code Cropper is an open-source software tool that extracts behavior from live Python running code, generating a program/unit-test equivalent to the original, but only with the functions and/or classes selected by the user. It dumps the program execution as a Json database, to be extracted later with a code generator.

It can be used for automated generation of unit tests from real code execution, logging, and many other code-inspection use cases.

## Example

We have this program in Python:

```python
def launchGUI():
    print 'Please wait. Launching GUI.'
    print 'This might take several minutes.'
    
def dummy_function():
    print 'LOL'

def critical_function():
    print 'WARNING! This is critical.'

class ImportantClass(object):
    def __init__(self):
        print 'This class is important.'

    def important_function(self, i):
        print 'This function is really important.'

class DummyClass(object):
    def __init__(self):
        print 'This class is just a joke.'

    def dummy_function(self, i):
        print 'LOL'

def main():
    i = 1
    a = ImportantClass()
    dummy_function()
    dummy_function()
    launchGUI()
    i += 4
    critical_function()
    b = DummyClass()
    critical_function()
    b.dummy_function(i)
    a.important_function(i)

if __name__ == "__main__":
    main()
```

If we want to isolate only the important functions and classes, code_cropper is the solution:

```python
import sys
import code_cropper.annotator
import code_cropper.code_generator
from cStringIO import StringIO

def launchGUI():
    print 'Please wait. Launching GUI.'
    print 'This might take several minutes.'
    
def dummy_function():
    print 'LOL'

def critical_function():
    print 'WARNING! This is critical.'

class ImportantClass(object):
    def __init__(self):
        print 'This class is important.'

    def important_function(self, i):
        print 'This function is really important.'

class DummyClass(object):
    def __init__(self):
        print 'This class is just a joke.'

    def dummy_function(self, i):
        print 'LOL'

def main():
    current_module = sys.modules[__name__]
    my_annotator = code_cropper.annotator.annotatorInstance()
    my_annotator.resetForNewAnnotations()
    my_annotator.annotate(current_module, 'critical_function')
    my_annotator.annotate(ImportantClass)
    JSON_RUNNING = "/tmp/my_running.json"
    with code_cropper.annotator.ProgramExecutionDumper(JSON_RUNNING) as my_dumper:
        i = 1
        a = ImportantClass()
        dummy_function()
        dummy_function()
        launchGUI()
        i += 4
        critical_function()
        b = DummyClass()
        critical_function()
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
            print equiv_program_str
    #Generate equivalent program and unit test
    print '--------------------'
    print 'Equivalent program:'
    generate_equiv_code(code_cropper.code_generator.GeneratedSourceType.MAIN_FILE)
    print '--------------------'
    print 'Equivalent unit test:'
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
Equivalent program:
import __main__

var0 = __main__.ImportantClass()
__main__.critical_function()
__main__.critical_function()
var0.important_function(5)

--------------------
Equivalent unit test:
import unittest
import __main__

class UNIT_TEST_CASE(unittest.TestCase):
    def test_main(self):
        var0 = __main__.ImportantClass()
        self.assertEquals(None, __main__.critical_function())
        self.assertEquals(None, __main__.critical_function())
        self.assertEquals(None, var0.important_function(5))

if __name__ == '__main__':
    unittest.main()
```

Id est: the equivalent code could be sent to a new Python file to:
 * analyze the parameters;
 * simplify the original code;
 * generate an automatic Unit Test.

## Json database for running
The Json database generated (in the example, file in "/tmp/my_running.json") contains all the information needed to reproduce the program execution. It uses a hierarchy module -> class -> function, and all these "objects" are represented in the Database, being the model normalized. Every object (a module, class or function) has a unique id, and it is registered only once. This is the Json generated from the example:

```json
{
    "callGraph": [
        {
            "arguments": {
                "args": [
                    3
                ],
                "kargs": {}
            },
            "calleeId": 3,
            "funcName": "__init__",
            "id": 1,
            "level": 0,
            "methodType": "constructor",
            "returnedObject": 6,
            "threwException": false
        },
        {
            "arguments": {
                "args": [],
                "kargs": {}
            },
            "calleeId": 1,
            "funcName": "critical_function",
            "id": 2,
            "level": 0,
            "methodType": "method",
            "returnedObject": 6,
            "threwException": false
        },
        {
            "arguments": {
                "args": [],
                "kargs": {}
            },
            "calleeId": 1,
            "funcName": "critical_function",
            "id": 3,
            "level": 0,
            "methodType": "method",
            "returnedObject": 6,
            "threwException": false
        },
        {
            "arguments": {
                "args": [
                    3,
                    8
                ],
                "kargs": {}
            },
            "calleeId": 3,
            "funcName": "important_function",
            "id": 4,
            "level": 0,
            "methodType": "method",
            "returnedObject": 6,
            "threwException": false
        }
    ],
    "language": "Python",
    "languageObjects": [
        {
            "declarationCode": "__main__",
            "declarationType": "FIXED_VALUE",
            "id": 1,
            "languageTypeId": 1,
            "parentId": 0
        },
        {
            "declarationCode": "__main__.ImportantClass",
            "declarationType": "FIXED_VALUE",
            "id": 2,
            "languageTypeId": 2,
            "parentId": 1
        },
        {
            "declarationCode": null,
            "declarationType": "CONSTRUCTOR",
            "id": 3,
            "languageTypeId": 3,
            "parentId": 2
        },
        {
            "declarationCode": "__builtin__",
            "declarationType": "FIXED_VALUE",
            "id": 4,
            "languageTypeId": 1,
            "parentId": 0
        },
        {
            "declarationCode": "NoneType",
            "declarationType": "FIXED_VALUE",
            "id": 5,
            "languageTypeId": 2,
            "parentId": 4
        },
        {
            "declarationCode": null,
            "declarationType": "FIXED_VALUE",
            "id": 6,
            "languageTypeId": 3,
            "parentId": 5
        },
        {
            "declarationCode": "int",
            "declarationType": "FIXED_VALUE",
            "id": 7,
            "languageTypeId": 2,
            "parentId": 4
        },
        {
            "declarationCode": 5,
            "declarationType": "FIXED_VALUE",
            "id": 8,
            "languageTypeId": 3,
            "parentId": 7
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

It uses:
 * metaprogramming libraries, such as inspect and types;
 * Json format for storing the call graph;
 * multithreading queues, to decouple calls to the original function from the call graph storing.

## Future work

This is the remaining work:
 * migrate to Python 3;
 * add lint/pep8 and fix all warnings;
 * test with heavy load;
 * use Kafka or similar methods to decouple the logging from the execution, making it less CPU/memory consuming;
 * other small fixes/enhancements in https://github.com/GervasioCalderon/code-cropper/issues.
 
And some ideas to improve its capabilities:
 * simplify the annotation invocations, for instance: annotate all classes and functions of a module recursively;
 * implement a mockyfier, reading from the Json file to mimic a previous execution;
 * add profiling capabilities.
