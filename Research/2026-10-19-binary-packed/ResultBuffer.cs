using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace Tedd.RTree;

// Used only when T has no references. The list is exclusively owned by this query.
// The span tracks its managed array across GC; capacity changes always reacquire it.
internal ref struct ResultBuffer<T>
{
    private readonly List<T> _list;
    private readonly int _initial;
    private Span<T> _buffer;
    private int _position;

    internal ResultBuffer(List<T> list)
    {
        _list=list;_initial=list.Count;_position=_initial;_buffer=default;
    }
    internal readonly int Appended=>_position-_initial;

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    internal void Add(T item)
    {
        if((uint)_position>=(uint)_buffer.Length)Grow(1);
        _buffer[_position++]=item;
    }

    internal void AddRange(ReadOnlySpan<T> values)
    {
        if(values.Length==0)return;
        if(values.Length>_buffer.Length-_position)Grow(values.Length);
        values.CopyTo(_buffer.Slice(_position));_position+=values.Length;
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private void Grow(int additional)
    {
        // EnsureCapacity copies List.Count elements, so publish already written entries first.
        Commit();
        _list.EnsureCapacity(checked(_position+additional));
        CollectionsMarshal.SetCount(_list,_list.Capacity);
        _buffer=CollectionsMarshal.AsSpan(_list);
    }

    internal void Commit()
    {
        _buffer=default;
        if(_position!=_list.Count)CollectionsMarshal.SetCount(_list,_position);
    }
}
