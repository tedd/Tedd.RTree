"""Reprofile the frozen candidate using the inspected owned-catalog DotNetLab driver."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib

repo=Path(__file__).resolve().parents[2]
root=Path('D:/Workspaces/AI/rtree-binary-20261019').resolve()
assert root==Path('D:/Workspaces/AI/rtree-binary-20261019').resolve()
destination=repo/'Research/2026-10-19-binary-packed/dotnetlab'
text=(repo/'benchmarks/specialization/profile.py').read_text()
text=text.replace("worker = root / 'proposal-caller'","worker = root / 'final-caller'")
text=text.replace('Immutable flat bounds and payload arrays use integer ranges instead of node objects; fully contained subtrees copy one owned contiguous range.',
    'PackedKeyEncoding vectorizes normalization and Hilbert keys; scalar recursive traversal has an explicit NoInlining boundary and contiguous contained-subtree copying.')
text=text.replace('Complete materialized queries improve through fewer collector visits and copies while preserving exact geometry and owned immutable storage.',
    'Construction activity can remain in key generation and sorting; query activity can remain in traversal and consumption. Samples do not establish instruction-level causes or per-call costs.')
destination.mkdir(exist_ok=True)
(destination/'driver-sha256.txt').write_text(hashlib.sha256(text.encode()).hexdigest()+'\n')
(root/'owned-profile-driver.py').write_text(text,encoding='utf8')
sys.argv=[str(root/'owned-profile-driver.py'),str(root),str(destination),'packed']
exec(compile(text,str(root/'owned-profile-driver.py'),'exec'),globals())
