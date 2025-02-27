import httpx
import multiprocessing
from multiprocessing import Queue
import time 
import hashlib 
import atexit
from io import StringIO
import ase.io
from openmm import unit
import ase.io
from io import StringIO

class LogMD:
    def __init__(self, num_workers=3, template='', interval=100):
        self.frame_num = 0
        self.interval = interval
        if template != '': self.template = ase.io.read(template) # for openmm

        # Upload using multiple processes
        self.upload_queue = Queue()
        self.status_queue = Queue()
        self.num_workers = num_workers
        self.upload_processes = []
        
        for _ in range(self.num_workers):
            process = multiprocessing.Process(
                target=self.upload_worker_process,
                args=(self.upload_queue, self.status_queue)
            )
            process.start()
            self.upload_processes.append(process)
        
        # Generate sha hash.
        self.run_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]
        self.url = 'https://rcsb.ai/logmd/' + self.run_id
        
        # Print init message with run id. 
        print(f'\033[90m[\033[32mlogmd\033[90m] \033[90mid=\033[34m{self.run_id}\033[90m\033[0m 🚀')
        print(f'\033[90m[\033[32mlogmd\033[90m] \033[90murl=\033[34m{self.url}\033[90m\033[0m 🚀')
        
        # Cleanup asynch processes when python exists. 
        atexit.register(self.cleanup)

    def cleanup(self):
        print(f'\033[90m[\033[32mlogmd\033[90m] finishing uploads (if >5s open issue https://github.com/log-md/logmd)')

        # Send termination signal to all worker processes
        for _ in range(self.num_workers):
            self.upload_queue.put(None)
        for process in self.upload_processes:
            process.join()
        print(f'\033[90m[\033[32mlogmd\033[90m] id=\033[34mhttps://rcsb.ai/logmd/{self.run_id}\033[0m ✅')

    @staticmethod
    def upload_worker_process(upload_queue: Queue, status_queue: Queue):
        """Worker process that handles uploads"""
        client = httpx.Client(timeout=180)  
        
        while True:
            item = upload_queue.get()  
            if item is None:  break
            atom_string, frame_num, run_id, energy = item
            
            #url = "https://alexander-mathiasen--logmd-upload-frame-dev.modal.run"
            url = "https://alexander-mathiasen--logmd-upload-frame.modal.run"
            data = {
                "user_id": "user123",
                "run_id": run_id,
                "frame_num": frame_num,
                "energy": str(energy),
                "file_contents": atom_string
            }

            response = client.post(url, json=data)
            status_queue.put((frame_num, response.status_code))
        
        client.close()

    # for openmm
    def describeNextReport(self, simulation):
        steps = self.interval 
        return (steps, True, True, True, False)
    # for openmm
    def report(self, simulation, state):
        """ Method openmm calls: simulation.reporters.append(LogMD(template='1crn.pdb', interval=100)). """
        self.template.positions = state.getPositions(asNumpy=True).value_in_unit(unit.angstrom) 
        self.__call__(self.template)

    # for ase 
    def __call__(self, atoms):
        """Method ASE calls:  dyn.attach(logmd) """
        self.frame_num += 1
        
        if atoms.calc is not None: energy = float(atoms.get_potential_energy())
        else: energy = 0

        temp_pdb = StringIO()
        ase.io.write(temp_pdb, atoms, format='proteindatabank')
        atom_string = temp_pdb.getvalue()
        temp_pdb.close()

        self.upload_queue.put((atom_string, self.frame_num, self.run_id, energy))
