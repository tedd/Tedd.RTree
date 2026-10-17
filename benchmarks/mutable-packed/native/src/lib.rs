use geo_index::rtree::{RTreeBuilder, RTreeIndex, sort::{HilbertSort, STRSort}};
use static_aabb2d_index::{Control, StaticAABB2DIndex, StaticAABB2DIndexBuilder};

#[repr(C)]
#[derive(Clone, Copy)]
pub struct Rect { pub x: f64, pub y: f64, pub max_x: f64, pub max_y: f64 }

pub enum Index {
    Static(StaticAABB2DIndex<f64>),
    Geo(geo_index::rtree::RTree<f64>),
}

impl Index {
    pub fn build(mode: u32, boxes: &[Rect]) -> Self {
        if mode == 0 {
            let mut b = StaticAABB2DIndexBuilder::new_with_node_size(boxes.len(), 16);
            for r in boxes { b.add(r.x, r.y, r.max_x, r.max_y); }
            Index::Static(b.build().unwrap())
        } else {
            let mut b = RTreeBuilder::new_with_node_size(boxes.len() as u32, 16);
            for r in boxes { b.add(r.x, r.y, r.max_x, r.max_y); }
            Index::Geo(if mode == 2 { b.finish::<STRSort>() } else { b.finish::<HilbertSort>() })
        }
    }
}

pub struct Context {
    pub index: Index,
    pub out: Vec<u32>,
    stack: Vec<usize>,
}

impl Context {
    pub fn new(mode: u32, boxes: &[Rect]) -> Self {
        Self { index: Index::build(mode, boxes), out: Vec::with_capacity(boxes.len()), stack: Vec::with_capacity(1024) }
    }
    pub fn query(&mut self, q: Rect) {
        self.out.clear();
        match &self.index {
            Index::Static(t) => {
                let out = &mut self.out;
                t.visit_query_with_stack(q.x, q.y, q.max_x, q.max_y,
                    &mut |id| -> Control<()> { out.push(id as u32); Control::Continue }, &mut self.stack);
            },
            Index::Geo(t) => { self.out = t.search(q.x, q.y, q.max_x, q.max_y); }
        }
    }
}

#[repr(C)]
pub struct ResultView { pub ptr: *const u32, pub count: usize }

// ABI caller owns the input during create and the Context until destroy. No callbacks cross the ABI.
#[no_mangle]
pub unsafe extern "C" fn index_create(mode: u32, boxes: *const Rect, count: usize) -> *mut Context {
    let input = if count == 0 { &[] } else { std::slice::from_raw_parts(boxes, count) };
    Box::into_raw(Box::new(Context::new(mode, input)))
}

#[no_mangle]
pub unsafe extern "C" fn index_destroy(ctx: *mut Context) { drop(Box::from_raw(ctx)); }

#[no_mangle]
pub unsafe extern "C" fn index_query(ctx: *mut Context, q: Rect) { (*ctx).query(q); }

// Trivial pointer/length accessor: no allocation, synchronization, syscall, or managed callback.
#[no_mangle]
pub unsafe extern "C" fn index_result(ctx: *const Context) -> ResultView {
    ResultView { ptr: (*ctx).out.as_ptr(), count: (*ctx).out.len() }
}

// Only called for a static index with <=16 entries, after capacity reservation at creation.
#[no_mangle]
pub unsafe extern "C" fn index_query_leaf(ctx: *mut Context, q: Rect) { (*ctx).query(q); }
