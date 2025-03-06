# demo with ASE (atomic simulation environment)
from logmd import LogMD
from ase.calculators.lj import LennardJones
from ase.md.langevin import Langevin
import ase
import numpy as np 

atoms = ase.io.read('1crn.pdb')[:642] # remove water 
atoms.calc = LennardJones()
dyn = Langevin(atoms, 0.003/ase.units.fs, temperature_K=300, friction=0.002*ase.units.fs)
logmd = LogMD()

def log():
    # get sulfur atoms 
    sulfur_indices = [i for i, atom in enumerate(atoms) if atom.symbol == 'S']
    sulfurs = atoms[sulfur_indices]
    # compute distance of "sulfur bridges" 
    S_bridge1 = np.linalg.norm(sulfurs[0].position - sulfurs[5].position)
    S_bridge3 = np.linalg.norm(sulfurs[1].position - sulfurs[4].position)
    S_bridge2 = np.linalg.norm(sulfurs[2].position - sulfurs[3].position)
    
    logmd(atoms, dyn, 
          data_dict={
              "S_bridge1": f"{S_bridge1} [A]",
              "S_bridge2": f"{S_bridge2} [A]",
              "S_bridge3": f"{S_bridge3} [A]"
              }
    )

dyn.attach(log, interval=4)
dyn.run(64)