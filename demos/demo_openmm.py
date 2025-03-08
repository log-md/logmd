# Download 1crn.pdb 
import urllib.request
pdb_url = "https://files.rcsb.org/download/1crn.pdb"
urllib.request.urlretrieve(pdb_url, "1crn.pdb")

# Demo with OpenMM
from openmm.app import *
from openmm import *
from openmm.unit import *

pdb = PDBFile("1crn.pdb")
forcefield = ForceField("amber99sb.xml", "tip3p.xml")
integrator = LangevinIntegrator(300 * kelvin, 1 / picosecond, 0.002 * picoseconds)
simulation = Simulation(pdb.topology, forcefield.createSystem(pdb.topology), integrator)
simulation.context.setPositions(pdb.positions)

from logmd import LogMD

simulation.reporters.append(LogMD(template="1crn.pdb", interval=100))

simulation.step(1000)