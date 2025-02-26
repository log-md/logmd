<img src='demo.gif'>
<a href="https://rcsb.ai/logmd/3d090180" target="_blank">link</a>

# Try
```
pip install logmd
git clone https://github.com/log-md/logmd && cd logmd
python demo.py # assumes https://github.com/orbital-materials/orb-models is installed 
```
or
```
from logmd import LogMD
logmd = LogMD(num_workers=2)
dyn.attach(lambda: logmd(atoms), interval=4)
dyn.run(steps)
```
or
```
logmd 1crn.pdb # also works for trajectories
```
Doesn't solve your problem? <a href="https://calendly.com/alexander-mathiasen/vchat">Let us know!</a>

Like it? Buy us a <a href="https://studio.buymeacoffee.com/auth/oauth_callback?is_signup=" target="_blank">coffee!</a>
