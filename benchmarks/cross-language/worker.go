package main

import (
	"bufio"
	"fmt"
	"github.com/tidwall/rtree"
	"os"
	"sort"
	"time"
)

type Rect struct{ x, y, X, Y float64 }

var bounds, queries []Rect
var sink any

func build() *rtree.RTreeG[int] {
	t := new(rtree.RTreeG[int])
	for i, b := range bounds {
		t.Insert([2]float64{b.x, b.y}, [2]float64{b.X, b.Y}, i)
	}
	return t
}
func search(t *rtree.RTreeG[int], q Rect, out []int) []int {
	out = out[:0]
	t.Search([2]float64{q.x, q.y}, [2]float64{q.X, q.Y}, func(_, _ [2]float64, id int) bool { out = append(out, id); return true })
	return out
}
func measure(op string, fn func() any) {
	iterations := 1
	run := func() float64 {
		start := time.Now()
		for i := 0; i < iterations; i++ {
			sink = fn()
		}
		return float64(time.Since(start).Nanoseconds()) / 1000
	}
	us := run()
	for us < 100000 {
		iterations *= 2
		us = run()
	}
	us = run()
	fmt.Printf("%s,%.12g,%d\n", op, us/float64(iterations), iterations)
}
func main() {
	f, e := os.Open(os.Args[1])
	if e != nil {
		panic(e)
	}
	defer f.Close()
	r := bufio.NewReader(f)
	var n int
	fmt.Fscan(r, &n)
	bounds = make([]Rect, n)
	for i := range bounds {
		b := &bounds[i]
		if _, e = fmt.Fscan(r, &b.x, &b.y, &b.X, &b.Y); e != nil {
			panic(e)
		}
	}
	for {
		var q Rect
		if _, e = fmt.Fscan(r, &q.x, &q.y, &q.X, &q.Y); e != nil {
			break
		}
		queries = append(queries, q)
	}
	t := build()
	out := []int{}
	for _, q := range queries {
		expected := []int{}
		for i, b := range bounds {
			if b.x <= q.X && b.X >= q.x && b.y <= q.Y && b.Y >= q.y {
				expected = append(expected, i)
			}
		}
		out = search(t, q, out)
		sort.Ints(out)
		if len(out) != len(expected) {
			panic("result length")
		}
		for i := range out {
			if out[i] != expected[i] {
				panic("result ID")
			}
		}
	}
	measure("build", func() any { return build() })
	for g := 0; g < 4; g++ {
		group := g
		measure(fmt.Sprintf("query%d", g), func() any {
			var sum int64
			for j := group; j < len(queries); j += 4 {
				out = search(t, queries[j], out)
				for _, id := range out {
					sum += int64(id + 1)
				}
			}
			return sum
		})
	}
	fmt.Fprintf(os.Stderr, "validated=%d\n", len(queries))
}
