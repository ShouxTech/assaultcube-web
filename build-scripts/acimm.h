// Browser build: route immediate-mode GL and client-array state through acimm.cpp
#pragma once
#ifdef __cplusplus
extern "C" {
#endif
void acimm_enableclientstate(GLenum a); void acimm_disableclientstate(GLenum a); void acimm_clientactivetexture(GLenum unit);
void acimm_vertexpointer(GLint size, GLenum type, GLsizei stride, const void *p); void acimm_colorpointer(GLint size, GLenum type, GLsizei stride, const void *p);
void acimm_normalpointer(GLenum type, GLsizei stride, const void *p); void acimm_texcoordpointer(GLint size, GLenum type, GLsizei stride, const void *p);
void acimm_begin(GLenum mode); void acimm_end(void);
void acimm_vertex2f(GLfloat x, GLfloat y); void acimm_vertex2d(GLdouble x, GLdouble y); void acimm_vertex2i(GLint x, GLint y);
void acimm_vertex3f(GLfloat x, GLfloat y, GLfloat z); void acimm_vertex3fv(const GLfloat *v);
void acimm_texcoord2f(GLfloat u, GLfloat v); void acimm_texcoord2i(GLint u, GLint v); void acimm_texcoord2fv(const GLfloat *t);
void acimm_color3f(GLfloat r, GLfloat g, GLfloat b); void acimm_color3d(GLdouble r, GLdouble g, GLdouble b); void acimm_color4f(GLfloat r, GLfloat g, GLfloat b, GLfloat a);
void acimm_color3ub(GLubyte r, GLubyte g, GLubyte b); void acimm_color4ub(GLubyte r, GLubyte g, GLubyte b, GLubyte a); void acimm_color4ubv(const GLubyte *c);
void acimm_color3fv(const GLfloat *c); void acimm_color4fv(const GLfloat *c);
void acimm_drawbatched(GLenum mode, const GLint *first, const GLsizei *count, int n); void acimm_drawarrays(GLenum mode, GLint first, GLsizei count); void acimm_drawelements(GLenum mode, GLsizei count, GLenum type, const void *indices);
#ifdef __cplusplus
}
#endif
#define glEnableClientState acimm_enableclientstate
#define glDisableClientState acimm_disableclientstate
#define glClientActiveTexture acimm_clientactivetexture
#define glVertexPointer acimm_vertexpointer
#define glColorPointer acimm_colorpointer
#define glNormalPointer acimm_normalpointer
#define glTexCoordPointer acimm_texcoordpointer
#define glBegin acimm_begin
#define glEnd acimm_end
#define glVertex2f acimm_vertex2f
#define glVertex2d acimm_vertex2d
#define glVertex2i acimm_vertex2i
#define glVertex3f acimm_vertex3f
#define glVertex3fv acimm_vertex3fv
#define glTexCoord2f acimm_texcoord2f
#define glTexCoord2i acimm_texcoord2i
#define glTexCoord2fv acimm_texcoord2fv
#define glColor3f acimm_color3f
#define glColor3d acimm_color3d
#define glColor4f acimm_color4f
#define glColor3ub acimm_color3ub
#define glColor4ub acimm_color4ub
#define glColor4ubv acimm_color4ubv
#define glColor3fv acimm_color3fv
#define glColor4fv acimm_color4fv
#define glDrawArrays acimm_drawarrays
#define glDrawElements acimm_drawelements
