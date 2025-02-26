from setuptools import setup

setup(name='LogMD',
      version='0.1',
      description='Log MD trajectories with `dyn.attach(logmd(atoms)). ',
      url='http://github.com/log-md/logmd',
      author='Alexander Mathiasen',
      license='MIT',
      packages=['logmd'],
      zip_safe=False,
      entry_points={
        "console_scripts": ["logmd=logmd.__main__:main"],
      },
      )