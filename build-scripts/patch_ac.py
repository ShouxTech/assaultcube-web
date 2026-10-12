#!/usr/bin/env python3
"""Apply browser (Emscripten/WebAssembly) patches to a copy of the AssaultCube source tree."""
import sys, re, pathlib

SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/root/build/acsrc/src')

def patch(fname, old, new, count=1):
    p = SRC / fname
    s = p.read_text(encoding='latin-1')
    n = s.count(old)
    if n != count:
        raise SystemExit(f'{fname}: expected {count} match(es), found {n} for:\n{old[:200]}')
    s = s.replace(old, new)
    p.write_text(s, encoding='latin-1')
    print(f'patched {fname}')

# ---------------------------------------------------------------- tools.cpp: no threads in the browser
patch('tools.cpp', '''static int sl_sem_errorcountdummy = 0;

#ifdef AC_USE_SDL_THREADS
sl_semaphore::sl_semaphore(int init, int *ecnt)''', '''static int sl_sem_errorcountdummy = 0;

#if defined(__EMSCRIPTEN__)
// browser build is single-threaded: semaphores are plain counters and never block
sl_semaphore::sl_semaphore(int init, int *ecnt) { data = (void *)(intptr_t)init; errorcount = ecnt ? ecnt : &sl_sem_errorcountdummy; }
sl_semaphore::~sl_semaphore() {}
void sl_semaphore::wait() { intptr_t v = (intptr_t)data; if(v > 0) data = (void *)(v - 1); }
int sl_semaphore::trywait() { intptr_t v = (intptr_t)data; if(v > 0) { data = (void *)(v - 1); return 0; } return 1; }
int sl_semaphore::timedwait(int howlongmillis) { return trywait(); }
int sl_semaphore::getvalue() { return (int)(intptr_t)data; }
void sl_semaphore::post() { data = (void *)((intptr_t)data + 1); }
#elif defined(AC_USE_SDL_THREADS)
sl_semaphore::sl_semaphore(int init, int *ecnt)''')

patch('tools.cpp', '''#ifdef AC_USE_SDL_THREADS
struct sl_threadinfo { int (*fn)(void *); void *data; SDL_Thread *handle; volatile char done; };''', '''#if defined(__EMSCRIPTEN__)
struct sl_threadinfo { int (*fn)(void *); void *data; volatile char done; };

void *sl_createthread(int (*fn)(void *), void *data, const char *name)
{ // no threads in the browser: background workers are simply not started
    sl_threadinfo *ti = new sl_threadinfo;
    ti->fn = fn;
    ti->data = data;
    ti->done = 1;
    return (void *) ti;
}

int sl_waitthread(void *ti) { delete (sl_threadinfo *) ti; return -1; }
void sl_detachthread(void *ti) { if(ti) delete (sl_threadinfo *) ti; }
bool ismainthread() { return true; }

#elif defined(AC_USE_SDL_THREADS)
struct sl_threadinfo { int (*fn)(void *); void *data; SDL_Thread *handle; volatile char done; };''')

# ---------------------------------------------------------------- server.cpp: run deferred auth work inline
patch('server.cpp', '''int deferredprocessingthread(void *nop)
{
    for(;;)
    {
        servinfoauth_deferred.wait();
        if(!servinfoauth_done && servinfoauths.length())''', '''static void deferredprocessingstep();
int deferredprocessingthread(void *nop)
{
    for(;;)
    {
        servinfoauth_deferred.wait();
        deferredprocessingstep();
    }
    return 0;
}

static void deferredprocessingstep()
{
    {
        if(!servinfoauth_done && servinfoauths.length())''')
patch('server.cpp', '''            servinfoauth_done = true;
        }
    }
    return 0;
}

void polldeferredprocessing()
{
    static void *deferredprocessingthread_ti = NULL;
    if(!deferredprocessingthread_ti) deferredprocessingthread_ti = sl_createthread(deferredprocessingthread, NULL);
''', '''            servinfoauth_done = true;
        }
    }
}

void polldeferredprocessing()
{
#ifdef __EMSCRIPTEN__
    if(!servinfoauth_done && servinfoauths.length()) deferredprocessingstep();
#else
    static void *deferredprocessingthread_ti = NULL;
    if(!deferredprocessingthread_ti) deferredprocessingthread_ti = sl_createthread(deferredprocessingthread, NULL);
#endif
''')

# ---------------------------------------------------------------- main.cpp: browser main loop
patch('main.cpp', '''void limitfps(int &millis, int curmillis)
{
    if(!maxfps) return;''', '''void limitfps(int &millis, int curmillis)
{
#ifdef __EMSCRIPTEN__
    return; // the browser paces frames with requestAnimationFrame
#endif
    if(!maxfps) return;''')

patch('main.cpp', '''            glGetTexImage(GL_TEXTURE_2D, 0, GL_RGB, GL_UNSIGNED_BYTE, tmpdst);''', '''#ifndef __EMSCRIPTEN__
            glGetTexImage(GL_TEXTURE_2D, 0, GL_RGB, GL_UNSIGNED_BYTE, tmpdst);
#else
            memset(tmpdst, 0, tmpdstsize);
#endif''')

patch('main.cpp', '''#define DEFAULTPROFILEPATH "profile"

int main(int argc, char **argv)''', '''#define DEFAULTPROFILEPATH "profile"

static void mainloopframe();

int main(int argc, char **argv)''')

# turn the body of the for(;;) main loop into its own function
main = (SRC / 'main.cpp').read_text(encoding='latin-1')
start_marker = '''    for(;;)
    {
        static int frames = 0;
        static float fps = 10.0f;'''
i = main.index(start_marker)
end_marker = '''        pollautodownloadresponse();
        if(onceauthed && sk)
        {
            onceauthed = false;
            afterauth();
        }
    }
'''
j = main.index(end_marker, i) + len(end_marker)
loop = main[i:j]
body = loop[len('    for(;;)\n    {\n'):-len('    }\n')]
replacement = '''#ifdef __EMSCRIPTEN__
    EM_ASM({ if(Module.onGameReady) Module.onGameReady(); });
    emscripten_set_main_loop(mainloopframe, 0, 1);
#else
    for(;;) mainloopframe();
#endif
'''
main = main[:i] + replacement + main[j:]
# hoist the statics the loop used from main() to file scope
main = main.replace('''    inmainloop = true;
    static bool onceauthed = true;
#ifdef _DEBUG
    int lastflush = 0;
#endif
''', '''    inmainloop = true;
''')
func = '''
static bool onceauthed = true;
#ifdef _DEBUG
static int lastflush = 0;
#endif
static void mainloopframe()
{
''' + body + '''}
'''
main = main.replace('''VAR(version, 1, AC_VERSION, 0);''', func + '''
VAR(version, 1, AC_VERSION, 0);''')
(SRC / 'main.cpp').write_text(main, encoding='latin-1')
print('patched main.cpp (main loop)')

# ---------------------------------------------------------------- rendergl.cpp: GL entry points under WebGL emulation
patch('rendergl.cpp', '''    if(hasext(exts, "GL_ARB_multitexture"))
    {''', '''#ifdef __EMSCRIPTEN__
    { // emulated fixed-function GL: bind entry points directly, no display lists, no MDA/stencil extensions
        extern int mdldlist;
        mdldlist = 0;
        glActiveTexture_ = glActiveTexture;
        glClientActiveTexture_ = glClientActiveTexture;
        hasMT = true;
        hasTE = true;
    }
#else
    if(hasext(exts, "GL_ARB_multitexture"))
    {''')
patch('rendergl.cpp', '''    if(hasext(exts, "GL_EXT_stencil_wrap")) hasSTW = true;''', '''    if(hasext(exts, "GL_EXT_stencil_wrap")) hasSTW = true;
#endif''')

# ---------------------------------------------------------------- platform.h: emscripten headers
patch('platform.h', '''#include <stdint.h>''', '''#include <stdint.h>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif''')

import shutil
shutil.copy('/root/build/webshim.cpp', SRC / 'webshim.cpp')
print('added webshim.cpp')

# ---------------------------------------------------------------- immediate mode layer + readback fixes
shutil.copy('/root/build/acimm.cpp', SRC / 'acimm.cpp')
shutil.copy('/root/build/acimm.h', SRC / 'acimm.h')
patch('platform.h', '''    #include "GL/glext.h"''', '''    #include "GL/glext.h"
    #ifdef __EMSCRIPTEN__
    #include "acimm.h"
    #endif''')
patch('rendergl.cpp', '''        glActiveTexture_ = glActiveTexture;
        glClientActiveTexture_ = glClientActiveTexture;''', '''        glActiveTexture_ = glActiveTexture;
        glClientActiveTexture_ = acimm_clientactivetexture;''')
patch('rendergl.cpp', '''    glReadPixels(w/2, h/2, 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT, &cursordepth);''', '''#ifdef __EMSCRIPTEN__
    cursordepth = 1.0f; // WebGL can't read the depth buffer: aim at the far plane, intersectgeometry() clips to the first wall
#else
    glReadPixels(w/2, h/2, 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT, &cursordepth);
#endif''')
patch('vertmodel.h', '''            glReadPixels(0, 0, aasize, aasize, GL_RED, GL_UNSIGNED_BYTE, pixels);''', '''#ifdef __EMSCRIPTEN__
            { // WebGL only reads RGBA
                uchar *rgba = new uchar[4*aasize*aasize];
                glReadPixels(0, 0, aasize, aasize, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
                loopi(aasize*aasize) pixels[i] = rgba[4*i];
                delete[] rgba;
            }
#else
            glReadPixels(0, 0, aasize, aasize, GL_RED, GL_UNSIGNED_BYTE, pixels);
#endif''')

patch('rendercubes.cpp', '''        if(hasMDA && !ati_mda_bug) glMultiDrawArrays_(type, strips.first.getbuf(), strips.count.getbuf(), strips.first.length()); \\
        else loopv(strips.first) glDrawArrays(type, strips.first[i], strips.count[i]); \\''', '''        acimm_drawbatched(type, strips.first.getbuf(), strips.count.getbuf(), strips.first.length()); \\''')

# ---------------------------------------------------------------- browser integration: window, quit, save, exports
patch('main.cpp', '''void setupscreen(int &useddepthbits, int &usedfsaa)
{
    if(glcontext)''', '''#ifdef __EMSCRIPTEN__
#include <emscripten/html5.h>
static void webcanvassize(int &w, int &h)
{ // the page decides the canvas size (CSS); render at that size
    double cw = 0, ch = 0;
    if(emscripten_get_element_css_size("#canvas", &cw, &ch) == EMSCRIPTEN_RESULT_SUCCESS && cw >= 1 && ch >= 1)
    {
        w = int(cw);
        h = int(ch);
    }
}
#endif

void setupscreen(int &useddepthbits, int &usedfsaa)
{
#ifdef __EMSCRIPTEN__
    if(screen && glcontext)
    { // one canvas, one WebGL context: never tear it down, just match the page size
        int w = scr_w, h = scr_h;
        webcanvassize(w, h);
        scr_w = w; scr_h = h;
        SDL_SetWindowSize(screen, w, h);
        updatescreensize();
        return;
    }
    fullscreen = 0; // the page handles fullscreen
    { int w = scr_w, h = scr_h; webcanvassize(w, h); if(w > 0 && h > 0) { scr_w = w; scr_h = h; } }
#endif
    if(glcontext)''')

patch('main.cpp', '''void setfullscreen(bool enable)
{
    if(!screen) return;''', '''void setfullscreen(bool enable)
{
#ifdef __EMSCRIPTEN__
    extern bool inmainloop;
    if(inmainloop) EM_ASM({ if(Module.setFullscreen) Module.setFullscreen(!!$0); }, enable ? 1 : 0);
    return;
#endif
    if(!screen) return;''')

patch('main.cpp', '''    if(resetcfg) deletecfg();
    else writecfg();
    savehistory();
    writemapmodelattributes();
    entropy_save();
    writeallxmaps();
    cleanup(NULL);''', '''    if(resetcfg) deletecfg();
    else writecfg();
    savehistory();
    writemapmodelattributes();
    entropy_save();
    writeallxmaps();
#ifdef __EMSCRIPTEN__
    emscripten_cancel_main_loop();
    audiomgr.soundcleanup();
    SDL_SetRelativeMouseMode(SDL_FALSE);
    EM_ASM({ if(Module.onQuit) Module.onQuit(); });
    emscripten_force_exit(0);
#endif
    cleanup(NULL);''')

patch('main.cpp', '''int setgamma(int newgamma) // replacement for SDL_SetGamma
{
    return screen ? SDL_SetWindowBrightness(screen, newgamma/100.0f) : -1;
}''', '''int setgamma(int newgamma) // replacement for SDL_SetGamma
{
#ifdef __EMSCRIPTEN__
    EM_ASM({ if(Module.canvas) Module.canvas.style.filter = $0 == 100 ? '' : 'brightness(' + ($0 / 100) + ')'; }, newgamma);
    return 0;
#else
    return screen ? SDL_SetWindowBrightness(screen, newgamma/100.0f) : -1;
#endif
}''')

patch('main.cpp', '''
static bool onceauthed = true;''', '''
#ifdef __EMSCRIPTEN__
// entry points for the web page
extern "C" EMSCRIPTEN_KEEPALIVE void ac_savestate()
{ // persist settings like a normal quit would, without quitting
    if(!inmainloop) return;
    writeinitcfg();
    writecfg();
    savehistory();
    entropy_save();
}

extern "C" EMSCRIPTEN_KEEPALIVE void ac_exec(const char *cmd)
{
    if(inmainloop) execute(cmd);
}

extern "C" EMSCRIPTEN_KEEPALIVE void ac_resize(int w, int h)
{
    if(!screen || w < 1 || h < 1) return;
    scr_w = clamp(w, SCR_MINW, SCR_MAXW);
    scr_h = clamp(h, SCR_MINH, SCR_MAXH);
    SDL_SetWindowSize(screen, scr_w, scr_h);
    updatescreensize();
}
#endif

static bool onceauthed = true;''')

patch('main.cpp', '''void mapscreenshot(const char *imagepath, bool mapshot, int fileformat, float scale, int height, int quality)''', '''static void readpixels_rgb(int w, int h, uchar *dst)
{
#ifdef __EMSCRIPTEN__
    uchar *rgba = new uchar[w * h * 4]; // WebGL only reads RGBA
    glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
    loopi(w * h) { dst[3*i] = rgba[4*i]; dst[3*i+1] = rgba[4*i+1]; dst[3*i+2] = rgba[4*i+2]; }
    delete[] rgba;
#else
    glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, dst);
#endif
}

void mapscreenshot(const char *imagepath, bool mapshot, int fileformat, float scale, int height, int quality)''')
patch('main.cpp', '''            glReadPixels(0, 0, src_w, src_h, GL_RGB, GL_UNSIGNED_BYTE, tmpsrc);''', '''            readpixels_rgb(src_w, src_h, tmpsrc);''')
patch('main.cpp', '''        else glReadPixels(0, 0, dst_w, dst_h, GL_RGB, GL_UNSIGNED_BYTE, tmpdst);''', '''        else readpixels_rgb(dst_w, dst_h, tmpdst);''')

# ---------------------------------------------------------------- graphics setting changes: apply in place, no restart dialog
patch('menus.cpp', '''void addchange(const char *desc, int type)
{
    if(!applydialog) return;''', '''void addchange(const char *desc, int type)
{
#ifdef __EMSCRIPTEN__
    // the WebGL context is fixed for the page's lifetime (anti-aliasing, stencil bits); texture settings
    // can be applied by reloading textures, which resetgl does without recreating the context here
    if(type == CHANGE_GFX && strcmp(desc, "anti-aliasing") && strcmp(desc, "stencil-buffer precision"))
    {
        static int lastreset = -1;
        extern int totalmillis;
        if(lastreset != totalmillis) { lastreset = totalmillis; addsleep(100, "resetgl", true); }
    }
    return;
#endif
    if(!applydialog) return;''')
patch('main.cpp', '''    if(vsync>=0) SDL_GL_SetSwapInterval(vsync);''', '''#ifndef __EMSCRIPTEN__ // the browser always paces frames with requestAnimationFrame
    if(vsync>=0) SDL_GL_SetSwapInterval(vsync);
#endif''')

# ---------------------------------------------------------------- page can ask whether a game menu is open
p = SRC / 'menus.cpp'
t = p.read_text(encoding='latin-1')
t += '''
#ifdef __EMSCRIPTEN__
extern "C" EMSCRIPTEN_KEEPALIVE int ac_menuopen() { return curmenu != NULL; }
#endif
'''
p.write_text(t, encoding='latin-1')
print('patched menus.cpp (ac_menuopen)')

patch('main.cpp', '''    if(msg)
    {
        #ifdef WIN32
        MessageBox(NULL, msg, "AssaultCube fatal error", MB_OK|MB_SYSTEMMODAL|MB_ICONERROR);
        #else
        printf("%s", msg);
        #endif''', '''    if(msg)
    {
        #ifdef WIN32
        MessageBox(NULL, msg, "AssaultCube fatal error", MB_OK|MB_SYSTEMMODAL|MB_ICONERROR);
        #else
        printf("%s\\n", msg);
        #endif
        #ifdef __EMSCRIPTEN__
        emscripten_cancel_main_loop();
        emscripten_force_exit(EXIT_FAILURE); // lets the page show the error instead of a frozen canvas
        #endif''')
