import httpx
import multiprocessing
from multiprocessing import Queue
import time
import hashlib
import atexit
from io import StringIO
import ase.io
from openmm import unit  # type: ignore[import-untyped]
import random
import rich
from typing import Optional

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
            self.url = f"{get_fe_base_url()}/logmd/{self.project}/{self.run_id}"
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
            self.url = f"{get_fe_base_url()}/logmd/{self.run_id}"

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
        rich.print(f"{LOGMD_PREFIX}id=[blue]{self.url}[/] ✅")

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

        temp_pdb = StringIO()
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
        if not self.logged_in:
            rich.print(
                f"{LOGMD_PREFIX}[red]Not logged in. Cannot list project files.[/]"
            )
            return 0

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
