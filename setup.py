from distutils.core import setup

setup(
    name='itrace_post',
    version='0.0dev',
    packages=['itrace_post', ],
    license='None',
    long_description="A package for processing output from the iTrace plugin."
)

setup(
    name='fluorite',
    version='0.0dev',
    packages=['fluorite', ],
    license='None',
    long_description='A package for parsing and processing '
                     'data from the FLUORITE plugin for Eclipse, '
                     'with special features for eye tracking research.'
)
