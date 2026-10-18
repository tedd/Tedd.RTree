"""Render version-scoped capability differences alongside actual selected-fixture medians."""
import html
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
capabilities = json.loads((root/'site/assets/index-capabilities.json').read_text(encoding='utf8'))

def claim(results, size, distribution):
    selected = [r for r in results if r['size']==size and r['distribution']==distribution]
    value = lambda library, operation: next(r['medianUs'] for r in selected if r['library']==library and r['operation']==operation)
    query_winners = [r for r in capabilities['indexes'] if not r['insertAfterBuild'] and value('candidate','queries') < value(r['id'],'queries')]
    both_winners = [r for r in query_winners if value('candidate','build') < value(r['id'],'build')]
    winners = both_winners or query_winners
    fixture = f'{size:,} {distribution} 2D rectangles'
    if not winners:
        return f'{fixture}: compare the measured times above. Tedd.RTree supports individual inserts, removals and moves after bulk loading.'
    names = [r['label'].removesuffix(' (Rust)').removesuffix(' (C#)') for r in winners]
    libraries = names[0] if len(names)==1 else ', '.join(names[:-1])+' and '+names[-1]
    metric = 'construction and 64-query medians' if both_winners else '64-query medians'
    return f'{fixture}: Tedd.RTree has lower measured {metric} than {libraries}, while supporting individual inserts, removals and moves after bulk loading. Those compared indexes do not accept new inserts after construction.'

def render(results):
    out = ['''      <div class="comparison-capabilities" id="index-capabilities">
        <div class="capability-summary">
          <p class="eyebrow">Speed with individual updates</p>
          <h3>Fast queries. Mutable data.</h3>
          <p id="comparison-capability-claim" aria-live="polite">'''+html.escape(claim(results,100000,'uniform'))+'''</p>
        </div>
        <div class="results-panel"><div class="results-heading"><h3>Capabilities beyond the timing charts</h3><p>Listed index versions · source links in each row</p></div><div class="table-scroll"><table class="capability-results"><caption>Construction, updates and geometry supported by the compared indexes</caption><thead><tr><th scope="col">Index / version</th><th scope="col">Changes after construction</th><th scope="col">Dimensions</th><th scope="col">Coordinates</th><th scope="col">Construction API</th></tr></thead><tbody>''']
    for r in capabilities['indexes']:
        own = ' class="comparison-ours"' if r['id']=='candidate' else ''
        out.append(f'<tr{own}><th scope="row"><a href="{html.escape(r["source"],quote=True)}">{html.escape(r["label"])}</a><small>{html.escape(r["version"])}</small></th>'+''.join(f'<td>{html.escape(r[k])}</td>' for k in ('changes','dimensions','coordinates','construction'))+'</tr>')
    out += ['''</tbody></table></div></div>
        <p class="capability-note">Tedd.RTree provides native 2D and 3D APIs for all four coordinate types, including exact <code>long</code> geometry. <a href="#model">ConcurrentRTree</a> supports immediate changes under a reader/writer lock; SnapshotRTree publishes complete replacement batches with lock-free readers. <a href="#generic-benchmarks">See the separate 3D measurements</a>.</p>
        <p class="capability-note">The timing charts measure the original 2D <code>double</code> API. This table covers the named indexes, rather than every index in their wider libraries. Mutable competitors can implement moves through removal and reinsertion. NTS STRtree supports removals and concurrent read-only queries, but no inserts after construction. Capability differences do not establish performance for unmeasured workloads.</p>
        <div class="evidence-links"><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/INDEX-CAPABILITIES.md">Capability sources and scope ↗</a></div>
      </div>
''']
    return '\n'.join(out)
