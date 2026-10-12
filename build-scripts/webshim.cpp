// Browser build shims for fixed-function GL calls that Emscripten's GL emulation does not provide.
#include <GL/gl.h>
extern "C" {
// display lists are disabled in the browser build (mdldlist = 0); these are never reached
GLuint glGenLists(GLsizei range) { return 0; }
void glNewList(GLuint list, GLenum mode) {}
void glEndList(void) {}
void glCallList(GLuint list) {}
void glDeleteLists(GLuint list, GLsizei range) {}
}
