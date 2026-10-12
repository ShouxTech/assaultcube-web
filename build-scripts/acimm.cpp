// Immediate-mode OpenGL (glBegin/glEnd) for the browser build.
//
// Emscripten's GL emulation writes immediate-mode attributes into a raw stream and
// assumes every vertex repeats the exact same attribute sequence. AssaultCube relies
// on real GL semantics instead (e.g. one glColor right after glBegin applies to every
// following vertex, colours change mid-primitive for coloured text). This layer keeps
// proper "current attribute" state, collects complete vertices and submits each
// primitive with client-side vertex arrays, which the emulator handles reliably.
// It also cuts the JS<->wasm call count to a few calls per primitive.
#include <GL/gl.h>
#include <string.h>
#include <vector>

namespace {
struct vtx { float x, y, z, u, v; unsigned char c[4]; };
std::vector<vtx> verts;
std::vector<unsigned short> quadidx;
GLenum curmode = GL_TRIANGLES;
bool inbegin = false;
float cu = 0, cv = 0;
unsigned char cc[4] = { 255, 255, 255, 255 };

// shadow copy of client array state so it can be restored after each primitive
struct arrayptr { GLint size; GLenum type; GLsizei stride; const void *ptr; };
enum { MAXUNITS = 8 };
bool envertex = false, encolor = false, ennormal = false, entex[MAXUNITS] = { false };
int clientunit = 0;
arrayptr pvertex = { 4, GL_FLOAT, 0, NULL }, pcolor = { 4, GL_FLOAT, 0, NULL }, pnormal = { 3, GL_FLOAT, 0, NULL }, ptex[MAXUNITS];
bool ptexinit = false;

inline unsigned char tob(float f) { return f <= 0 ? 0 : (f >= 1 ? 255 : (unsigned char)(f * 255.0f + 0.5f)); }
inline void initptex() { if(!ptexinit) { for(int i = 0; i < MAXUNITS; i++) { ptex[i].size = 4; ptex[i].type = GL_FLOAT; ptex[i].stride = 0; ptex[i].ptr = NULL; } ptexinit = true; } }

inline void setcolor(unsigned char r, unsigned char g, unsigned char b, unsigned char a)
{
    cc[0] = r; cc[1] = g; cc[2] = b; cc[3] = a;
    if(!inbegin) glColor4ub(r, g, b, a);
}

inline void addvertex(float x, float y, float z)
{
    if(!inbegin) return;
    vtx v;
    v.x = x; v.y = y; v.z = z; v.u = cu; v.v = cv;
    memcpy(v.c, cc, 4);
    verts.push_back(v);
}
}

extern "C" {

void acimm_enableclientstate(GLenum a)
{
    switch(a)
    {
        case GL_VERTEX_ARRAY: envertex = true; break;
        case GL_COLOR_ARRAY: encolor = true; break;
        case GL_NORMAL_ARRAY: ennormal = true; break;
        case GL_TEXTURE_COORD_ARRAY: entex[clientunit] = true; break;
    }
    glEnableClientState(a);
}

void acimm_disableclientstate(GLenum a)
{
    switch(a)
    {
        case GL_VERTEX_ARRAY: envertex = false; break;
        case GL_COLOR_ARRAY: encolor = false; break;
        case GL_NORMAL_ARRAY: ennormal = false; break;
        case GL_TEXTURE_COORD_ARRAY: entex[clientunit] = false; break;
    }
    glDisableClientState(a);
}

void acimm_clientactivetexture(GLenum unit)
{
    int u = (int)(unit - GL_TEXTURE0);
    if(u >= 0 && u < MAXUNITS) clientunit = u;
    glClientActiveTexture(unit);
}

void acimm_vertexpointer(GLint size, GLenum type, GLsizei stride, const void *p) { pvertex.size = size; pvertex.type = type; pvertex.stride = stride; pvertex.ptr = p; glVertexPointer(size, type, stride, p); }
void acimm_colorpointer(GLint size, GLenum type, GLsizei stride, const void *p) { pcolor.size = size; pcolor.type = type; pcolor.stride = stride; pcolor.ptr = p; glColorPointer(size, type, stride, p); }
void acimm_normalpointer(GLenum type, GLsizei stride, const void *p) { pnormal.type = type; pnormal.stride = stride; pnormal.ptr = p; glNormalPointer(type, stride, p); }
void acimm_texcoordpointer(GLint size, GLenum type, GLsizei stride, const void *p)
{
    initptex();
    arrayptr &t = ptex[clientunit];
    t.size = size; t.type = type; t.stride = stride; t.ptr = p;
    glTexCoordPointer(size, type, stride, p);
}

void acimm_begin(GLenum mode)
{
    curmode = mode;
    inbegin = true;
    verts.clear();
}

void acimm_end()
{
    inbegin = false;
    int n = (int)verts.size();
    if(n == 0) { glColor4ub(cc[0], cc[1], cc[2], cc[3]); return; }
    initptex();

    // switch client arrays over to our vertex buffer (texture unit 0 only)
    if(clientunit != 0) glClientActiveTexture(GL_TEXTURE0);
    for(int u = 1; u < MAXUNITS; u++) if(entex[u]) { glClientActiveTexture(GL_TEXTURE0 + u); glDisableClientState(GL_TEXTURE_COORD_ARRAY); }
    if(clientunit != 0 || true) glClientActiveTexture(GL_TEXTURE0);
    if(ennormal) glDisableClientState(GL_NORMAL_ARRAY);
    if(!envertex) glEnableClientState(GL_VERTEX_ARRAY);
    if(!encolor) glEnableClientState(GL_COLOR_ARRAY);
    if(!entex[0]) glEnableClientState(GL_TEXTURE_COORD_ARRAY);
    const vtx *v = &verts[0];
    glVertexPointer(3, GL_FLOAT, sizeof(vtx), &v->x);
    glColorPointer(4, GL_UNSIGNED_BYTE, sizeof(vtx), v->c);
    glTexCoordPointer(2, GL_FLOAT, sizeof(vtx), &v->u);

    switch(curmode)
    {
        case GL_QUADS:
        {
            int nq = n / 4;
            if(nq > 16000) nq = 16000;
            quadidx.resize(nq * 6);
            for(int q = 0; q < nq; q++)
            {
                unsigned short b = (unsigned short)(q * 4), *d = &quadidx[q * 6];
                d[0] = b; d[1] = b + 1; d[2] = b + 2; d[3] = b; d[4] = b + 2; d[5] = b + 3;
            }
            if(nq) glDrawElements(GL_TRIANGLES, nq * 6, GL_UNSIGNED_SHORT, &quadidx[0]);
            break;
        }
        case GL_QUAD_STRIP: glDrawArrays(GL_TRIANGLE_STRIP, 0, n); break;
        case GL_POLYGON: glDrawArrays(GL_TRIANGLE_FAN, 0, n); break;
        default: glDrawArrays(curmode, 0, n); break;
    }

    // restore the application's client array state
    if(pvertex.ptr) glVertexPointer(pvertex.size, pvertex.type, pvertex.stride, pvertex.ptr);
    if(pcolor.ptr) glColorPointer(pcolor.size, pcolor.type, pcolor.stride, pcolor.ptr);
    if(ptex[0].ptr) glTexCoordPointer(ptex[0].size, ptex[0].type, ptex[0].stride, ptex[0].ptr);
    if(!envertex) glDisableClientState(GL_VERTEX_ARRAY);
    if(!encolor) glDisableClientState(GL_COLOR_ARRAY);
    if(!entex[0]) glDisableClientState(GL_TEXTURE_COORD_ARRAY);
    if(ennormal) glEnableClientState(GL_NORMAL_ARRAY);
    for(int u = 1; u < MAXUNITS; u++) if(entex[u])
    {
        glClientActiveTexture(GL_TEXTURE0 + u);
        glEnableClientState(GL_TEXTURE_COORD_ARRAY);
        if(ptex[u].ptr) glTexCoordPointer(ptex[u].size, ptex[u].type, ptex[u].stride, ptex[u].ptr);
    }
    glClientActiveTexture(GL_TEXTURE0 + clientunit);
    glColor4ub(cc[0], cc[1], cc[2], cc[3]); // current colour persists after glEnd, as in real GL
}

void acimm_vertex2f(GLfloat x, GLfloat y) { addvertex(x, y, 0); }
void acimm_vertex2d(GLdouble x, GLdouble y) { addvertex((float)x, (float)y, 0); }
void acimm_vertex2i(GLint x, GLint y) { addvertex((float)x, (float)y, 0); }
void acimm_vertex3f(GLfloat x, GLfloat y, GLfloat z) { addvertex(x, y, z); }
void acimm_vertex3fv(const GLfloat *v) { addvertex(v[0], v[1], v[2]); }
void acimm_texcoord2f(GLfloat u, GLfloat v) { cu = u; cv = v; }
void acimm_texcoord2i(GLint u, GLint v) { cu = (float)u; cv = (float)v; }
void acimm_texcoord2fv(const GLfloat *t) { cu = t[0]; cv = t[1]; }
void acimm_color3f(GLfloat r, GLfloat g, GLfloat b) { setcolor(tob(r), tob(g), tob(b), 255); }
void acimm_color3d(GLdouble r, GLdouble g, GLdouble b) { setcolor(tob((float)r), tob((float)g), tob((float)b), 255); }
void acimm_color4f(GLfloat r, GLfloat g, GLfloat b, GLfloat a) { setcolor(tob(r), tob(g), tob(b), tob(a)); }
void acimm_color3ub(GLubyte r, GLubyte g, GLubyte b) { setcolor(r, g, b, 255); }
void acimm_color4ub(GLubyte r, GLubyte g, GLubyte b, GLubyte a) { setcolor(r, g, b, a); }
void acimm_color4ubv(const GLubyte *c) { setcolor(c[0], c[1], c[2], c[3]); }
void acimm_color3fv(const GLfloat *c) { setcolor(tob(c[0]), tob(c[1]), tob(c[2]), 255); }
void acimm_color4fv(const GLfloat *c) { setcolor(tob(c[0]), tob(c[1]), tob(c[2]), tob(c[3])); }

}

// ---------------------------------------------------------------------------------------------
// Client-array draws. The emulator re-uploads every vertex from index 0 up to first+count on
// each glDrawArrays and only handles GL_QUADS when first is a multiple of 4. We instead
// rebase the array pointers to the range actually used and merge many strips into a single
// indexed triangle draw.
namespace {
std::vector<unsigned short> batchidx;

inline int typesize(GLenum t) { switch(t) { case GL_UNSIGNED_BYTE: case GL_BYTE: return 1; case GL_SHORT: case GL_UNSIGNED_SHORT: return 2; default: return 4; } }
inline const void *offsetptr(const arrayptr &a, int base) { int st = a.stride ? a.stride : a.size * typesize(a.type); return (const char *)a.ptr + (size_t)base * st; }
inline const void *offsetnormal(const arrayptr &a, int base) { int st = a.stride ? a.stride : 3 * typesize(a.type); return (const char *)a.ptr + (size_t)base * st; }

void rebase(int base)
{
    if(envertex && pvertex.ptr) glVertexPointer(pvertex.size, pvertex.type, pvertex.stride, offsetptr(pvertex, base));
    if(encolor && pcolor.ptr) glColorPointer(pcolor.size, pcolor.type, pcolor.stride, offsetptr(pcolor, base));
    if(ennormal && pnormal.ptr) glNormalPointer(pnormal.type, pnormal.stride, offsetnormal(pnormal, base));
    bool switched = false;
    for(int u = 0; u < MAXUNITS; u++) if(entex[u] && ptex[u].ptr)
    {
        if(u != clientunit || switched) { glClientActiveTexture(GL_TEXTURE0 + u); switched = true; }
        glTexCoordPointer(ptex[u].size, ptex[u].type, ptex[u].stride, offsetptr(ptex[u], base));
    }
    if(switched) glClientActiveTexture(GL_TEXTURE0 + clientunit);
}

extern "C" void acimm_drawelements(GLenum mode, GLsizei count, GLenum type, const void *indices);
void flushbatch(int minv)
{
    if(batchidx.empty()) return;
    rebase(minv);
    acimm_drawelements(GL_TRIANGLES, (GLsizei)batchidx.size(), GL_UNSIGNED_SHORT, &batchidx[0]);
    batchidx.clear();
}
}

extern "C" {

// draw n primitives (GL_TRIANGLES / GL_TRIANGLE_STRIP / GL_TRIANGLE_FAN / GL_QUADS / GL_POLYGON) from the
// currently bound client arrays as one (or a few) indexed triangle draws
void acimm_drawbatched(GLenum mode, const GLint *first, const GLsizei *count, int n)
{
    initptex();
    batchidx.clear();
    int minv = 0, maxv = 0;
    bool open = false;
    for(int s = 0; s < n; s++)
    {
        int f = first[s], c = count[s];
        if(c < 3) continue;
        int hi = f + c - 1 > maxv ? f + c - 1 : maxv;
        if(open && (f < minv || hi - minv > 65535 || batchidx.size() > 60000))
        {
            flushbatch(minv);
            open = false;
        }
        if(!open) { minv = f; maxv = f + c - 1; open = true; }
        if(f + c - 1 > maxv) maxv = f + c - 1;
        unsigned short b = (unsigned short)(f - minv);
        switch(mode)
        {
            case GL_TRIANGLES:
                for(int k = 0; k + 2 < c; k += 3) { batchidx.push_back(b + k); batchidx.push_back(b + k + 1); batchidx.push_back(b + k + 2); }
                break;
            case GL_TRIANGLE_STRIP: case GL_QUAD_STRIP:
                for(int k = 0; k + 2 < c; k++)
                {
                    if(k & 1) { batchidx.push_back(b + k + 1); batchidx.push_back(b + k); }
                    else { batchidx.push_back(b + k); batchidx.push_back(b + k + 1); }
                    batchidx.push_back(b + k + 2);
                }
                break;
            case GL_TRIANGLE_FAN: case GL_POLYGON:
                for(int k = 1; k + 1 < c; k++) { batchidx.push_back(b); batchidx.push_back(b + k); batchidx.push_back(b + k + 1); }
                break;
            case GL_QUADS:
                for(int k = 0; k + 3 < c; k += 4)
                {
                    batchidx.push_back(b + k); batchidx.push_back(b + k + 1); batchidx.push_back(b + k + 2);
                    batchidx.push_back(b + k); batchidx.push_back(b + k + 2); batchidx.push_back(b + k + 3);
                }
                break;
        }
    }
    if(open) flushbatch(minv);
    rebase(0);
}

void acimm_drawarrays(GLenum mode, GLint first, GLsizei count)
{
    if(count <= 0) return;
    if(mode == GL_POINTS || mode == GL_LINES || mode == GL_LINE_STRIP || mode == GL_LINE_LOOP)
    {
        rebase(first);
        glDrawArrays(mode, 0, count);
        rebase(0);
        return;
    }
    acimm_drawbatched(mode, &first, &count, 1);
}

}

// ---------------------------------------------------------------------------------------------
// glDrawElements with separate (non-interleaved) client arrays: the emulator only re-strides as
// many vertices as there are *indices*, so meshes whose indices reach past that read garbage.
// Gather the referenced vertex range into one interleaved buffer ourselves instead.
namespace {
std::vector<unsigned char> gatherbuf;
std::vector<unsigned short> rebasedidx;

struct gatherattr { const arrayptr *src; int unit; int kind; int bytes; int srcstride; int offset; };

bool isinterleaved()
{
    long minp = 0x7fffffffL; int stride = -1;
    const arrayptr *arrs[3 + MAXUNITS]; int sizes[3 + MAXUNITS]; int n = 0;
    if(envertex) { arrs[n] = &pvertex; sizes[n++] = pvertex.size * typesize(pvertex.type); }
    if(encolor) { arrs[n] = &pcolor; sizes[n++] = pcolor.size * typesize(pcolor.type); }
    if(ennormal) { arrs[n] = &pnormal; sizes[n++] = 3 * typesize(pnormal.type); }
    for(int u = 0; u < MAXUNITS; u++) if(entex[u]) { arrs[n] = &ptex[u]; sizes[n++] = ptex[u].size * typesize(ptex[u].type); }
    for(int i = 0; i < n; i++)
    {
        int st = arrs[i]->stride ? arrs[i]->stride : sizes[i];
        if(stride < 0) stride = st; else if(st != stride) return false;
        if((long)arrs[i]->ptr < minp) minp = (long)arrs[i]->ptr;
    }
    for(int i = 0; i < n; i++) if((long)arrs[i]->ptr - minp + sizes[i] > stride) return false;
    return true;
}
}

extern "C" void acimm_drawelements(GLenum mode, GLsizei count, GLenum type, const void *indices)
{
    initptex();
    if(count <= 0) return;
    if(type != GL_UNSIGNED_SHORT || isinterleaved()) { glDrawElements(mode, count, type, indices); return; }
    const unsigned short *idx = (const unsigned short *)indices;
    int lo = 65535, hi = 0;
    for(int i = 0; i < count; i++) { int v = idx[i]; if(v < lo) lo = v; if(v > hi) hi = v; }
    int nv = hi - lo + 1;

    gatherattr attrs[3 + MAXUNITS]; int na = 0, stride = 0;
    #define ADDATTR(arr, u, k, b) { gatherattr &g = attrs[na++]; g.src = &(arr); g.unit = u; g.kind = k; g.bytes = b; g.srcstride = (arr).stride ? (arr).stride : b; g.offset = stride; stride += (b + 3) & ~3; }
    if(envertex) ADDATTR(pvertex, 0, 0, pvertex.size * typesize(pvertex.type));
    if(encolor) ADDATTR(pcolor, 0, 1, pcolor.size * typesize(pcolor.type));
    if(ennormal) ADDATTR(pnormal, 0, 2, 3 * typesize(pnormal.type));
    for(int u = 0; u < MAXUNITS; u++) if(entex[u]) ADDATTR(ptex[u], u, 3, ptex[u].size * typesize(ptex[u].type));
    #undef ADDATTR
    gatherbuf.resize((size_t)nv * stride + 16);
    unsigned char *dst = &gatherbuf[0];
    for(int a = 0; a < na; a++)
    {
        const gatherattr &g = attrs[a];
        const unsigned char *src = (const unsigned char *)g.src->ptr + (size_t)lo * g.srcstride;
        unsigned char *d = dst + g.offset;
        for(int v = 0; v < nv; v++, src += g.srcstride, d += stride) memcpy(d, src, g.bytes);
    }
    rebasedidx.resize(count);
    for(int i = 0; i < count; i++) rebasedidx[i] = (unsigned short)(idx[i] - lo);

    bool switched = false;
    for(int a = 0; a < na; a++)
    {
        const gatherattr &g = attrs[a];
        const void *p = dst + g.offset;
        switch(g.kind)
        {
            case 0: glVertexPointer(g.src->size, g.src->type, stride, p); break;
            case 1: glColorPointer(g.src->size, g.src->type, stride, p); break;
            case 2: glNormalPointer(g.src->type, stride, p); break;
            case 3:
                if(g.unit != clientunit || switched) { glClientActiveTexture(GL_TEXTURE0 + g.unit); switched = true; }
                glTexCoordPointer(g.src->size, g.src->type, stride, p);
                break;
        }
    }
    if(switched) glClientActiveTexture(GL_TEXTURE0 + clientunit);
    glDrawElements(mode, count, GL_UNSIGNED_SHORT, &rebasedidx[0]);
    rebase(0);
}
