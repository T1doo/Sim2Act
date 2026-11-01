from setuptools import setup,Extension
from pathlib import Path
import subprocess,hashlib
p=Path('/workspace/scratch/graph-97-component-build-20261101');p.mkdir(exist_ok=True)
s=p/'_cold_graph_structure.c';s.write_bytes(subprocess.check_output(['git','show','97f4c0af7932c21cb21b6498b642b1639ab050ca:src/sim2act/_cold_graph_structure.c'],cwd='/workspace/Sim2Act'))
setup(name='component-only',ext_modules=[Extension('_cold_graph_structure',[str(s)],define_macros=[('SIM2ACT_GRAPH_SOURCE_SHA','"'+hashlib.sha256(s.read_bytes()).hexdigest()+'"')])])
