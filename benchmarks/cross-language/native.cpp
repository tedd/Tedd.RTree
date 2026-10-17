#define _USE_MATH_DEFINES
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef TIDWALL
extern "C"
{
#include "rtree.h"
}
#elif defined(BOOST_TREE)
#include <boost/geometry/algorithms/detail/disjoint/box_box.hpp>
#include <boost/geometry/geometries/box.hpp>
#include <boost/geometry/geometries/point_xy.hpp>
#include <boost/geometry/index/rtree.hpp>
#include <boost/geometry/strategies/index/cartesian.hpp>
#include <boost/geometry/strategies/relate/cartesian.hpp>
#else
#include "RTree.h"
#endif
struct Rect
{
    double x, y, X, Y;
};
static std::vector<Rect> bounds, queries;
static volatile uint64_t sink;
#ifdef TIDWALL
struct Index
{
    rtree *tree;
    Index() : tree(rtree_new())
    {
        if (!tree)
            throw std::bad_alloc();
        for (size_t i = 0; i < bounds.size(); i++)
        {
            auto b = bounds[i];
            double lo[] = {b.x, b.y}, hi[] = {b.X, b.Y};
            if (!rtree_insert(tree, lo, hi, reinterpret_cast<void *>(i + 1)))
                throw std::bad_alloc();
        }
    }
    ~Index()
    {
        rtree_free(tree);
    }
    void search(Rect b, std::vector<int> &out)
    {
        double lo[] = {b.x, b.y}, hi[] = {b.X, b.Y};
        rtree_search(
            tree, lo, hi,
            [](const double *, const double *, const void *data, void *ctx) {
                static_cast<std::vector<int> *>(ctx)->push_back(int(reinterpret_cast<uintptr_t>(data) - 1));
                return true;
            },
            &out);
    }
};
#elif defined(BOOST_TREE)
namespace bg = boost::geometry;
namespace bgi = bg::index;
using Box = bg::model::box<bg::model::d2::point_xy<double>>;
using Item = std::pair<Box, int>;
static std::vector<Item> items;
Box box(Rect b)
{
    return Box({b.x, b.y}, {b.X, b.Y});
}
struct IdOutput
{
    std::vector<int> *out;
    IdOutput &operator*()
    {
        return *this;
    }
    IdOutput &operator++()
    {
        return *this;
    }
    IdOutput operator++(int)
    {
        return *this;
    }
    IdOutput &operator=(const Item &item)
    {
        out->push_back(item.second);
        return *this;
    }
};
struct Index
{
    bgi::rtree<Item, bgi::rstar<16>> tree;
    Index() : tree(items.begin(), items.end())
    {
    }
    void search(Rect b, std::vector<int> &out)
    {
#ifdef BOOST_QUERY
        tree.query(bgi::intersects(box(b)), IdOutput{&out});
#else
        for (auto it = tree.qbegin(bgi::intersects(box(b))); it != tree.qend(); ++it)
            out.push_back(it->second);
#endif
    }
};
#else
struct Index
{
    RTree<int, double, 2, double, 16, 8> tree;
    Index()
    {
        for (size_t i = 0; i < bounds.size(); i++)
        {
            auto b = bounds[i];
            double lo[] = {b.x, b.y}, hi[] = {b.X, b.Y};
            tree.Insert(lo, hi, (int)i);
        }
    }
    void search(Rect b, std::vector<int> &out)
    {
        double lo[] = {b.x, b.y}, hi[] = {b.X, b.Y};
        tree.Search(lo, hi, [&out](const int &id) {
            out.push_back(id);
            return true;
        });
    }
};
#endif
template <class F> void measure(const char *op, F action)
{
    size_t iterations = 1;
    double us;
    auto run = [&]() {
        auto t = std::chrono::steady_clock::now();
        for (size_t i = 0; i < iterations; i++)
            sink = action();
        return std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now() - t).count();
    };
    do
    {
        us = run();
        if (us < 100000)
            iterations *= 2;
    } while (us < 100000);
    us = run();
    std::printf("%s,%.12g,%zu\n", op, us / iterations, iterations);
}
int main(int argc, char **argv)
{
    std::ifstream f(argv[1]);
    int n;
    f >> n;
    if (!f || n < 0)
        throw std::runtime_error("fixture");
    bounds.resize(n);
    for (auto &b : bounds)
        f >> b.x >> b.y >> b.X >> b.Y;
    Rect q;
    while (f >> q.x >> q.y >> q.X >> q.Y)
        queries.push_back(q);
#ifdef BOOST_TREE
    for (int i = 0; i < n; i++)
        items.push_back({box(bounds[i]), i});
#endif
    Index tree;
    std::vector<int> out;
    for (auto q : queries)
    {
        std::vector<int> expected;
        for (int i = 0; i < n; i++)
        {
            auto b = bounds[i];
            if (b.x <= q.X && b.X >= q.x && b.y <= q.Y && b.Y >= q.y)
                expected.push_back(i);
        }
        out.clear();
        tree.search(q, out);
        std::sort(out.begin(), out.end());
        if (out != expected)
            throw std::runtime_error("result mismatch");
    }
    measure("build", [] {
        Index t;
        __asm__ __volatile__("" : : "r"(&t) : "memory");
        return bounds.size();
    });
    for (int g = 0; g < 4; g++)
    {
        std::string label = "query" + std::to_string(g);
        measure(label.c_str(), [&] {
            uint64_t sum = 0;
            for (size_t j = g; j < queries.size(); j += 4)
            {
                out.clear();
                tree.search(queries[j], out);
                for (int id : out)
                    sum += id + 1;
            }
            return sum;
        });
    }
    std::fprintf(stderr, "validated=%zu;sink=%llu\n", queries.size(), (unsigned long long)sink);
}
