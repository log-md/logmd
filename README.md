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
> logmd 1crn.pdb # also works for trajectories
```
Doesn't solve your problem? <a href="https://calendly.com/alexander-mathiasen/vchat">Let us know!</a>

Like it? Buy us a <a href="https://studio.buymeacoffee.com/auth/oauth_callback?is_signup=" target="_blank">coffee!</a>


## What about Gromacs/OpenMM/CHARMM/... ? 
We currently only support [Atomic Simulation Environment (ASE)](https://wiki.fysik.dtu.dk/ase/). [Vote here](https://github.com/log-md/logmd/issues/1) to let us know which backend to support.  

## Use-cases
We built `logmd` for the two use-cases below. If there's a use-case we're missing, [let's chat!](https://calendly.com/alexander-mathiasen/vchat) 

### Case 1: 
Inspect/share trajectory while simulation runs - just click/share the link `logmd` prints. 
```
from logmd import LogMD
logmd = LogMD(num_workers=2)
dyn.attach(lambda: logmd(atoms), interval=4)
dyn.run(steps)
```

### Case 2: 
Document/visualize fixing of pdb before running simulation. Example: I want to simulate '1crn.pdb' but need to add missing residues, hydrogens, water, pH and so on. To document everything, I run `logmd watch 1crn.pdb` which stores all versions of `1crn.pdb` as a trajectory.  
```
>logmd watch 1crn.pdb # from terminal
```
