use std::{env,fs,hint::black_box,time::Instant};
use rstar::{RTree,RTreeObject,AABB};
use geo_index::rtree::{RTreeBuilder,RTreeIndex,sort::{HilbertSort,STRSort}};
type Rect=[f64;4];
#[derive(Clone)] struct Item{b:Rect,id:u32}
impl RTreeObject for Item{type Envelope=AABB<[f64;2]>;fn envelope(&self)->Self::Envelope{aabb(self.b)}}
fn aabb(b:Rect)->AABB<[f64;2]>{AABB::from_corners([b[0],b[1]],[b[2],b[3]])}
enum Index{Star(RTree<Item>),Geo(geo_index::rtree::RTree<f64>)}
fn build(mode:&str,items:&[Item])->Index{if mode=="rstar"{Index::Star(RTree::bulk_load(items.to_vec()))}else{let mut b=RTreeBuilder::new_with_node_size(items.len() as u32,16);for i in items{b.add(i.b[0],i.b[1],i.b[2],i.b[3]);}Index::Geo(if mode=="geo-str"{b.finish::<STRSort>()}else{b.finish::<HilbertSort>()})}}
fn search(t:&Index,q:Rect,out:&mut Vec<u32>){out.clear();match t{Index::Star(t)=>{out.extend(t.locate_in_envelope_intersecting(aabb(q)).map(|i|i.id));},Index::Geo(t)=>{*out=t.search(q[0],q[1],q[2],q[3]);}}}
fn measure<F:FnMut()->u64>(op:&str,mut action:F){let mut iterations=1u64;let mut run=|n|{let start=Instant::now();for _ in 0..n{black_box(action());}start.elapsed().as_secs_f64()*1e6};let mut us=run(iterations);while us<100000.0{iterations*=2;us=run(iterations);}us=run(iterations);println!("{op},{},{iterations}",us/iterations as f64);}
fn main(){let args:Vec<_>=env::args().collect();let text=fs::read_to_string(&args[1]).unwrap();let mut lines=text.lines();let n:usize=lines.next().unwrap().parse().unwrap();let rects:Vec<Rect>=lines.map(|s|{let v:Vec<f64>=s.split_whitespace().map(|s|s.parse().unwrap()).collect();v.try_into().unwrap()}).collect();let items:Vec<Item>=rects[..n].iter().enumerate().map(|(i,b)|Item{b:*b,id:i as u32}).collect();let queries=&rects[n..];let t=build(&args[2],&items);let mut out=Vec::new();for q in queries{let expected:Vec<u32>=items.iter().filter(|i|i.b[0]<=q[2]&&i.b[2]>=q[0]&&i.b[1]<=q[3]&&i.b[3]>=q[1]).map(|i|i.id).collect();search(&t,*q,&mut out);out.sort_unstable();assert_eq!(out,expected,"result mismatch");}measure("build",||{black_box(build(&args[2],black_box(&items)));n as u64});for g in 0..4{measure(&format!("query{g}"),||{let mut sum=0u64;for j in (g..queries.len()).step_by(4){search(&t,queries[j],&mut out);for id in &out{sum+=*id as u64+1;}}sum});}eprintln!("validated={}",queries.len());}
