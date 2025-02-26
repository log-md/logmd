#!/usr/bin/env python

from . import *
import io
from tqdm import tqdm 

def from_terminal(file_path):
    logmd_obj = LogMD()
    content = open(file_path, 'r').read()
    model_count = content.count('MODEL')

    if model_count <= 1: 
        atoms = ase.io.read(file_path)
        logmd_obj(atoms)
    else: 
        models = content.split('MODEL')
        for model in tqdm(models[1:]):  # Skip the first split part as it is before the first MODEL
            buffer = io.StringIO('MODEL' + model)
            # Ensure buffer content is a string
            buffer_content = buffer.getvalue()
            if isinstance(buffer_content, bytes):
                buffer_content = buffer_content.decode('utf-8')  # Decode bytes to string
            atoms = ase.io.read(io.StringIO(buffer_content), format='proteindatabank')  # Specify the correct format if needed
            logmd_obj(atoms)

            time.sleep(0.2)

def watch_from_terminal(file_path):
    import hashlib
    hash = '' 
    logmd_obj = LogMD()
    while True:
        new_hash = hashlib.sha256(open(file_path, "rb").read()).hexdigest()
        if new_hash != hash:
            print(f'found change in {file_path}, uploading...')
            hash = new_hash
            logmd_obj(ase.io.read(file_path))
        time.sleep(0.5)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: logmd <file_path> # uploads file")
        print("Usage: logmd watch <file_path> # uploads file when changed ")
        sys.exit(1)
    
    command = sys.argv[1]
    file_path = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]

    if command == "watch" and file_path:
        watch_from_terminal(file_path)
    elif file_path:
        from_terminal(file_path)
    else:
        print("Usage: logmd <command> <file_path>")
        sys.exit(1)