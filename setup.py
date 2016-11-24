import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open(os.path.join(os.path.dirname(__file__), "code_cropper/VERSION"), 'r') as vf:
    the_version = vf.read().strip()

setup(
    name = "code_cropper",
    version = the_version,
    packages=["code_cropper"],
    author='Gervasio Calderon',
    author_email='gervicalder@gmail.com',
    tests_require = 'nose',
    test_suite = 'tests',
    package_data={
        # Export VERSION, for use in the client code.
        '': ['VERSION']
    },
    zip_safe=False
)
