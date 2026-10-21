#version 330
#include common.glsl
uniform mat4 p3d_ModelMatrix;
uniform vec4 u_frame;      // u0, v0, u1, v1 do quadro dentro da folha
uniform vec4 u_sprite;     // viés de profundidade, espelhar(0/1), 0, 0
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec3 v_world;
out vec2 v_uv;
void main() {
    vec4 w = p3d_ModelMatrix * p3d_Vertex;
    v_world = w.xyz;
    vec2 t = p3d_MultiTexCoord0;
    if (u_sprite.y > 0.5) t.x = 1.0 - t.x;
    v_uv = mix(u_frame.xy, u_frame.zw, t);
    // profundidade: o sprite inteiro usa a profundidade dos pés (como um painel em pé)
    vec3 feet = (p3d_ModelMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
    vec4 pos = oblique(w.xyz, 0.0);
    vec4 dpos = oblique(vec3(w.x, feet.y, feet.z), u_sprite.x);
    gl_Position = vec4(pos.xy, dpos.z, 1.0);
}
