#version 330
#include common.glsl
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;
in vec4 p3d_Color;
out vec3 v_world;
out vec3 v_normal;
out vec2 v_uv;
out vec4 v_color;
void main() {
    vec4 w = p3d_ModelMatrix * p3d_Vertex;
    v_world = w.xyz;
    v_normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
    v_uv = p3d_MultiTexCoord0;
    v_color = p3d_Color;
    gl_Position = oblique(w.xyz, 0.0);
}
