use static_aabb2d_index::{Control, StaticAABB2DIndex, StaticAABB2DIndexBuilder};
use std::{env, fs, hint::black_box, time::Instant};

type Rect = [f64; 4];

fn build(bounds: &[Rect]) -> StaticAABB2DIndex<f64> {
    let mut builder = StaticAABB2DIndexBuilder::new_with_node_size(bounds.len(), 16);
    for b in bounds {
        builder.add(b[0], b[1], b[2], b[3]);
    }
    builder.build().unwrap()
}

fn search(tree: &StaticAABB2DIndex<f64>, q: Rect, out: &mut Vec<usize>, stack: &mut Vec<usize>) {
    out.clear();
    tree.visit_query_with_stack(q[0], q[1], q[2], q[3], &mut |id| -> Control<()> {
        out.push(id);
        Control::Continue
    }, stack);
}

fn measure<F: FnMut() -> u64>(op: &str, mut action: F) {
    let mut iterations = 1u64;
    let mut run = |n| {
        let start = Instant::now();
        for _ in 0..n { black_box(action()); }
        start.elapsed().as_secs_f64() * 1e6
    };
    let mut us = run(iterations);
    while us < 100000.0 {
        iterations *= 2;
        us = run(iterations);
    }
    us = run(iterations);
    println!("{op},{},{iterations}", us / iterations as f64);
}

fn main() {
    let args: Vec<_> = env::args().collect();
    let text = fs::read_to_string(&args[1]).unwrap();
    let mut lines = text.lines();
    let n: usize = lines.next().unwrap().parse().unwrap();
    let rects: Vec<Rect> = lines.map(|s| {
        s.split_whitespace().map(|v| v.parse().unwrap()).collect::<Vec<_>>().try_into().unwrap()
    }).collect();
    let bounds = &rects[..n];
    let queries = &rects[n..];
    let tree = build(bounds);
    let mut out = Vec::new();
    let mut stack = Vec::new();
    for q in queries {
        let expected: Vec<_> = bounds.iter().enumerate().filter(|(_, b)| {
            b[0] <= q[2] && b[2] >= q[0] && b[1] <= q[3] && b[3] >= q[1]
        }).map(|(i, _)| i).collect();
        search(&tree, *q, &mut out, &mut stack);
        out.sort_unstable();
        assert_eq!(out, expected, "result mismatch");
    }
    measure("build", || { black_box(build(black_box(bounds))); n as u64 });
    for g in 0..4 {
        measure(&format!("query{g}"), || {
            let mut sum = 0u64;
            for j in (g..queries.len()).step_by(4) {
                search(&tree, queries[j], &mut out, &mut stack);
                for id in &out { sum += *id as u64 + 1; }
            }
            sum
        });
    }
    eprintln!("validated={}", queries.len());
}
