import fs from 'node:fs';
import {performance} from 'node:perf_hooks';

import Flatbush from './flatbush/index.js';

const rows = fs.readFileSync(process.argv[2], 'utf8').trim().split(/\r?\n/);
const n = Number(rows.shift()), bounds = rows.splice(0, n).map(r => r.split(' ').map(Number)),
      queries = rows.map(r => r.split(' ').map(Number));
function build()
{
    const t = new Flatbush(n, 16, Float64Array);
    for (const b of bounds)
        t.add(...b);
    t.finish();
    return t;
}
const tree = build();
let sink;
for (const q of queries)
{
    const expected = [];
    for (let i = 0; i < n; i++)
    {
        const b = bounds[i];
        if (b[0] <= q[2] && b[2] >= q[0] && b[1] <= q[3] && b[3] >= q[1])
            expected.push(i);
    }
    const actual = tree.search(...q).sort((a, b) => a - b);
    if (actual.length !== expected.length || actual.some((v, i) => v !== expected[i]))
        throw Error('result mismatch');
}
function measure(op, fn)
{
    let iterations = 1, us;
    function run()
    {
        const t = performance.now();
        for (let i = 0; i < iterations; i++)
            sink = fn();
        return (performance.now() - t) * 1000;
    }
    do
    {
        us = run();
        if (us < 100000)
            iterations *= 2;
    } while (us < 100000);
    us = run();
    console.log(`${op},${us / iterations},${iterations}`);
}
measure('build', build);
for (let g = 0; g < 4; g++)
    measure(`query${g}`, () => {
        let sum = 0;
        for (let j = g; j < queries.length; j += 4)
            for (const id of tree.search(...queries[j]))
                sum += id + 1;
        return sum;
    });
console.error(`validated=${queries.length};sink=${typeof sink}`);
