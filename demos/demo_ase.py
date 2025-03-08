# Download 1crn.pdb 
import urllib.request
pdb_url = "https://files.rcsb.org/download/1crn.pdb"
urllib.request.urlretrieve(pdb_url, "1crn.pdb")

# demo with ASE (atomic simulation environment)
from logmd import LogMD
from ase.calculators.lj import LennardJones
from ase.md.langevin import Langevin
import ase


# Attach logger and run simulation
atoms = ase.io.read("1crn.pdb")[:642]  # remove water
atoms.calc = LennardJones()
dyn = Langevin(
    atoms, 0.003 / ase.units.fs, temperature_K=300, friction=0.002 * ase.units.fs
)
logmd = LogMD()
dyn.attach(lambda: logmd(atoms), interval=4)
dyn.run(64)