use packed_native::{Context, Index, Rect};
use std::{env, fs, hint::black_box, time::Instant};

fn measure<F: FnMut() -> u64>(name: &str, mut action: F) {
    let mut iterations = 1;
    let mut run = |n| { let start = Instant::now(); for _ in 0..n { black_box(action()); } start.elapsed().as_secs_f64()*1e6 };
    while run(iterations) < 100000.0 { iterations *= 2; }
    println!("{name},{},{iterations},NA", run(iterations) / iterations as f64);
}

fn main() {
    let args: Vec<_> = env::args().collect();
    let mode = match args[2].as_str() { "static" => 0, "geo-hilbert" => 1, "geo-str" => 2, _ => panic!("mode") };
    let text = fs::read_to_string(&args[1]).unwrap();
    let mut rows = text.lines();
    let n: usize = rows.next().unwrap().parse().unwrap();
    let rects: Vec<Rect> = rows.map(|row| {
        let v: Vec<f64> = row.split_whitespace().map(|x| x.parse().unwrap()).collect();
        Rect { x: v[0], y: v[1], max_x: v[2], max_y: v[3] }
    }).collect();
    let boxes = &rects[..n];
    let queries = &rects[n..];
    let mut context = Context::new(mode, boxes);
    for q in queries {
        context.query(*q);
        let expected: Vec<u32> = boxes.iter().enumerate().filter(|(_,b)| b.x<=q.max_x && b.max_x>=q.x && b.y<=q.max_y && b.max_y>=q.y).map(|(i,_)|i as u32).collect();
        context.out.sort_unstable();
        assert_eq!(context.out, expected, "native result-set mismatch");
    }
    measure("build", || { black_box(Index::build(mode, black_box(boxes))); n as u64 });
    for g in 0..4 {
        measure(&format!("query{g}"), || {
            let mut sum = 0;
            for i in (g..queries.len()).step_by(4) {
                context.query(queries[i]);
                for id in &context.out { sum += *id as u64 + 1; }
            }
            sum
        });
    }
    eprintln!("validated={}", queries.len());
}
