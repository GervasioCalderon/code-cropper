#Code Cropper

Code Cropper is an open-source software tool that extracts behavior from live Python running code, generating a program equivalent to the original, but only with the functions and/or classes selected by the user. It dumps the program execution as a Json database, to be extracted later with a code generator.

##Example

We have this program in Python

```python
def launchGUI():
    print 'Please wait. Launching GUI.'
    print 'This might take several minutes.'
    
def dummy_function():
    print 'LOL'

def critical_function():
    print 'WARNING! This is critical.'

class ImportantClass:
    def __init__(self):
        print 'This class is important.'

    def important_function(self, i):
        print 'This function is really important.'

class DummyClass:
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

class ImportantClass:
    def __init__(self):
        print 'This class is important.'

    def important_function(self, i):
        print 'This function is really important.'

class DummyClass:
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
    def setUp(self):
        unittest.TestCase.setUp(self)

    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def test_main(self):
        var0 = __main__.ImportantClass()
        self.assertEquals(None, __main__.critical_function())
        self.assertEquals(None, __main__.critical_function())
        self.assertEquals(None, var0.important_function(5))

if __name__ == '__main__':
    unittest.main()
```

Id est: the equivalent code could be sent to a new Python file to:
 * analyzed the parameters;
 * simplify the original code;
 * generate an automatic Unit Test.

##Implementation

It uses:
 * metaprogramming libraries, such as inspect and types;
 * Json format for storing the call graph;
 * multithreading queues, to decouple calls to the original function from the call graph storing.

##Future work

This is the remaining work:
 * generate an egg;
 * kill the annotator thread in case of exceptions;
 * make it work for classes inhereted from Object;
 * test with heavy load.

And some ideas to improve its capabilities:
 * simplify the annotation invocations, for instance: annotate all classes and functions of a module recursively.
 * implement a mockyfier, reading from the Json file to mimic a previous execution.
