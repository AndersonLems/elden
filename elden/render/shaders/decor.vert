#version 330
#include common.glsl
// sprites estáticos agrupados: a normal carrega a posição dos pés.
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;
out vec3 v_world;
out vec2 v_uv;
void main() {
    v_world = p3d_Vertex.xyz;
    v_uv = p3d_MultiTexCoord0;
    gl_Position = billboard(p3d_Vertex.xyz, p3d_Normal, 0.02);
}
