from setuptools import setup

setup(name='LogMD',
      version='0.1',
      description='Log MD trajectories with `dyn.attach(LogMd()(atoms)). ',
      url='http://github.com/log-md/logmd',
      author='Alexander Mathiasen',
      license='MIT',
      packages=['logmd'],
      zip_safe=False)