#version 330
#include common.glsl
// sprites estáticos agrupados num único mesh: a normal carrega a posição dos pés (profundidade)
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;
out vec3 v_world;
out vec2 v_uv;
void main() {
    v_world = p3d_Vertex.xyz;
    v_uv = p3d_MultiTexCoord0;
    vec4 pos = oblique(p3d_Vertex.xyz, 0.0);
    vec4 dpos = oblique(vec3(p3d_Vertex.x, p3d_Normal.y, p3d_Normal.z), 0.02);
    gl_Position = vec4(pos.xy, dpos.z, 1.0);
}
