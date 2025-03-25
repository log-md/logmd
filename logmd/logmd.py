import httpx
import multiprocessing
from multiprocessing import Queue
import requests
import time
import hashlib
import atexit
import io 
import ase.io
from openmm import unit  # type: ignore[import-untyped]
import random
import rich
from typing import Optional
import base64
from tqdm import tqdm
import zipfile

from logmd.constants import LOGMD_PREFIX, eV_to_K
from logmd.data_models import LogMDToken
from logmd.utils import is_dev, get_fe_base_url, get_run_id, get_upload_url
from logmd.auth import load_token


class LogMD:
    def __init__(
        self,
        num_workers: int = 3,
        project: str = "",
        template: str = "",
        interval: int = 100,
    ):
        """
        LogMD logs ase.Atoms objects to rscb.ai.

        Usage:


        ```python
        from logmd import LogMD

        # ... setup simulation ...

        logmd = LogMD()
        dyn.attach(lambda: logmd(atoms), interval=4)
        dyn.run(steps)
        ```

        Args:
            num_workers: number of worker processes to use for uploading.
            project: project name.
            template: template pdb file.
            interval: interval of logging.
        """
        t0 = time.time()
        self.frame_num: int = 0
        self.interval: int = interval
        self.project: str = project
        self.token: Optional[LogMDToken] = None

        if template != "":
            template_or_templates = ase.io.read(template)  # for openmm
            if isinstance(template_or_templates, list):
                self.template = template_or_templates[0]
            else:
                self.template = template_or_templates

        # if no project => log publicly, no need to log-in.
        if self.project != "":
            self.load_or_create_token()

        # Upload using multiple processes
        self.upload_queue = Queue()
        self.status_queue = Queue()
        self.num_workers = num_workers
        self.upload_processes = []

        for _ in range(self.num_workers):
            process = multiprocessing.Process(
                target=self.upload_worker_process,
                args=(self.upload_queue, self.status_queue, self.token, self.project),
            )
            process.start()
            self.upload_processes.append(process)

        self.num = self.num_files() + 1

        # If logged-in use <adjective>-<noun>-<num> as name.
        if self.logged_in:
            self.run_id = get_run_id(self.num)
            self.url = f"{get_fe_base_url()}/{self.project}/{self.run_id}"
        # if not logged in, store publicly, use sha256 hash to remove collision.
        else:
            # pr[collision]~1/16^10=1e-12
            # E[draws to get collision]~sqrt(pr[collision])~1e-5    (birthday paradox)
            # => we have to check...
            self.run_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:10]
            while (
                httpx.head(f"https://logmd.b-cdn.net/public/{self.run_id}/").status_code
                == 200
            ):
                self.run_id = hashlib.sha256(
                    str(time.time() + random.random()).encode()
                ).hexdigest()[:10]
            self.url = f"{get_fe_base_url()}/{self.run_id}"

        # Print init message with run id.
        rich.print(f"{LOGMD_PREFIX}Load_time=[blue]{time.time() - t0:.2f}s[/] 🚀")
        rich.print(f"{LOGMD_PREFIX}Url=[blue][link={self.url}]{self.url}[/link][/] 🚀")

        # Cleanup asynch processes when python exists.
        atexit.register(self.cleanup)

    @property
    def logged_in(self) -> bool:
        return self.token is not None

    def load_or_create_token(self) -> None:
        """
        Load or create a token. This is the analogy of `logmd login` in the CLI.
        """
        self.token = load_token()

    def cleanup(self) -> None:
        rich.print(
            f"{LOGMD_PREFIX}Finishing uploads (if >5s open issue [link=https://github.com/log-md/logmd]https://github.com/log-md/logmd[/link] )"
        )

        # Send termination signal to all worker processes
        for _ in range(self.num_workers):
            self.upload_queue.put(None)
        for process in self.upload_processes:
            process.join()
        rich.print(f"{LOGMD_PREFIX}Url=[blue]{self.url}[/] ✅")

    @staticmethod
    def upload_worker_process(
        upload_queue: Queue, status_queue: Queue, token: LogMDToken, project: str
    ) -> None:
        """Worker process that handles uploads"""
        client = httpx.Client(timeout=180)

        while True:
            item = upload_queue.get()
            if item is None:
                break
            atom_string, frame_num, run_id, data_dict = item

            url = get_upload_url()
            data = {
                "user_id": "public" if token is None else token.email,
                "run_id": run_id,
                "frame_num": str(frame_num),
                "file_contents": atom_string,
                "token": None if token is None else token.token,
                "project": project,
                "data_dict": data_dict,
            }
            response = client.post(url, json=data)
            status_queue.put((frame_num, response.status_code))
        client.close()

    # for openmm
    def describeNextReport(self, simulation):
        """
        FIXME: according to openmm docs, this should return a dict of
        http://docs.openmm.org/latest/api-python/generated/openmm.app.checkpointreporter.CheckpointReporter.html?highlight=describenextreport
        """
        steps = self.interval
        return (steps, True, True, True, False)

    # for openmm
    def report(self, simulation, state) -> None:
        """
        Method openmm calls:
        simulation.reporters.append(LogMD(template='1crn.pdb', interval=100)).
        http://docs.openmm.org/latest/api-python/generated/openmm.app.checkpointreporter.CheckpointReporter.html?highlight=describenextreport#openmm.app.checkpointreporter.CheckpointReporter.report
        """
        self.template.positions = state.getPositions(asNumpy=True).value_in_unit(
            unit.angstrom
        )
        self.__call__(self.template)

    @staticmethod
    def mdanalysis(u, fun=None, display_notebook=False):
        """ Example: 
        ```
            import MDAnalysis as mda
            import LogMD
            u=mda.Universe('topology.pdb', 'samples.xtc')
            LogMD.mdanalysis(u)
        ```
        """
        url = 'https://alexander-mathiasen--logmd-upload-single-file-dev.modal.run' if is_dev() else 'https://alexander-mathiasen--logmd-upload-single-file.modal.run'
        
        atoms = ase.io.read(u.filename)
        output_buffer = io.StringIO()


        for frame_idx in tqdm(range(len(u.trajectory)), desc="Processing frames"):
            u.trajectory[frame_idx]
            atoms.positions = u.atoms.positions

            header = ""
            if fun is not None:
                data_dict = fun(atoms)
                for key, value in data_dict.items():
                    header += f"{key}={value}\n"

            output_buffer.write(header)  # Write header before atoms
            ase.io.write(output_buffer, atoms, format='proteindatabank')
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as zip_file:
            zip_file.writestr('trajectory_analysis.pdb', output_buffer.getvalue().encode('utf-8'))
        
        base64_encoded = base64.b64encode(zip_buffer.getvalue()).decode('ascii')
        
        def data_generator():
            import json
            json_str = json.dumps({"file_contents": base64_encoded}).encode('utf-8')
            total_size = len(json_str)
            chunk_size = min(4096, total_size // 100)
            
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Uploading") as pbar:
                for i in range(0, total_size, chunk_size):
                    chunk = json_str[i:i+chunk_size]
                    pbar.update(len(chunk))
                    yield chunk

        try:
            client = httpx.Client(timeout=6000)
            response = client.post(url, content=data_generator(), headers={"Content-Type": "application/json"})
            client.close()
            
            if response.status_code == 200:
                url = f"{get_fe_base_url()}/{response.json().get('run_id', '')}"
                rich.print(f"{LOGMD_PREFIX}Url=[blue][link={url}]{url}[/link][/] ✅")
            else:
                rich.print(f"{LOGMD_PREFIX}[red]Upload failed: {response.status_code} - {response.text}[/]")
        except Exception as e:
            rich.print(f"{LOGMD_PREFIX}[red]Error during upload: {str(e)}[/]")

        if display_notebook:
            from IPython.display import display
            display(LogMD.display_notebook(url))

        return url

    # for ase
    def __call__(self, atoms, dyn=None, data_dict=None):
        """
        Method ASE calls:
        logmd = LogMD()
        dyn.attach(logmd)
        """
        if data_dict is None:
            data_dict = {}

        self.frame_num += 1

        if atoms.calc is not None:
            energy = float(atoms.get_potential_energy())
        else:
            energy = 0

        if dyn is not None:
            simulation_time, temperature = dyn.get_time(), dyn.temp * eV_to_K
            data_dict.update(
                {
                    "simulation_time": f"{simulation_time} [ps]",
                    "temperature": f"{temperature} [K]",
                }
            )

        temp_pdb = io.StringIO()
        ase.io.write(temp_pdb, atoms, format="proteindatabank")
        atom_string = temp_pdb.getvalue()
        temp_pdb.close()

        data_dict.update(
            {
                "energy": f"{energy} [eV]",
            }
        )
        self.upload_queue.put((atom_string, self.frame_num, self.run_id, data_dict))

    def num_files(self) -> int:
        """Returns the number of files in the current project."""
        if not self.logged_in: return 0

        if is_dev():
            url = "https://alexander-mathiasen--logmd-list-project-dev.modal.run"  # Replace with the actual URL
        else:
            url = "https://alexander-mathiasen--logmd-list-project.modal.run"  # Replace with the actual URL

        assert self.token is not None, (
            "Should not happen. self.logged_in === self.token is not None"
        )
        data = {
            "user_id": self.token.email,
            "token": self.token.token,
            "project": self.project,
        }

        try:
            response = httpx.post(url, json=data)
            if response.status_code == 200:
                result = response.json()
                if "projects" in result:
                    return len(result["projects"])
                else:
                    rich.print(
                        f"{LOGMD_PREFIX}[red]Error: {result.get('error', 'Unknown error')}[/]"
                    )
            else:
                rich.print(
                    f"{LOGMD_PREFIX}[red]Failed to list project files with status `[blue]{response.status_code}[/]`: `[blue]{response.text}[/]`"
                )
        except Exception as e:
            rich.print(
                f"{LOGMD_PREFIX}[red]Error while listing project files: `[dim]{str(e)}[/]`"
            )

        return 0

    def notebook(self, width=1000, height=600):
        from IPython.display import display
        from IPython.display import IFrame
        iframe = IFrame(f"{self.url}", width=width, height=height)
        display(iframe)
        return iframe

    @staticmethod
    def display_notebook(url, width=1000, height=600):
        from IPython.display import IFrame
        return IFrame(f"{url}", width=width, height=height)

    @staticmethod
    def run(dyn, steps=100, notebook=False):
        import inspect
        import dill 

        url = "https://alexander-mathiasen--orb-run-md-dev.modal.run"
        headers = {'Content-Type': 'application/json'}
        current_file_code = inspect.getsource(inspect.getmodule(inspect.stack()[1].frame))

        dyn.atoms.calc = None # remove calculator, can be 100MB NN. 
        payload = {
            "code": current_file_code,
            "dyn": base64.b64encode(dill.dumps(dyn)).decode('utf-8'),
            "steps": steps
        }

        response = requests.post(url, json=payload, headers=headers, verify=False, stream=True)
        pbar = tqdm(range(steps))
        for num, line in enumerate(response.iter_lines()):
            print(line.decode())
            if num == 0: 
                url = line.decode()
            if line:
                pass 
                #pbar.set_description(f'[logmd] url={url} {line.decode()}')
                #pbar.update(1)
        pbar.close()