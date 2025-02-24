import ase 
from orb_models.forcefield import pretrained
from ase.md.langevin import Langevin  
from orb_models.forcefield.calculator import ORBCalculator
from tqdm import tqdm 

device = 'cuda'
orbff = pretrained.orb_d3_v2(device=device)

atoms = ase.io.read('1crn.pdb')
atoms.set_cell([30, 30, 30])
atoms.set_pbc([True, True, True])  
atoms.calc = calc = ORBCalculator(orbff, device=device) 

friction = 0.01 / ase.units.fs  
timestep = 0.5 * ase.units.fs
temperature_K = 300 
steps = 64

pbar = tqdm(total=steps, desc="MD Simulation")
dyn = Langevin(atoms, timestep, temperature_K=temperature_K, friction=friction)
dyn.attach(lambda: pbar.update(1), interval=1)

from logmd import LogMD
logmd = LogMD(num_workers=2)
dyn.attach(lambda: logmd(atoms), interval=4)
dyn.run(steps)