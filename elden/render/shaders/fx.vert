#version 330
#include common.glsl
in vec4 p3d_Vertex;
in vec4 p3d_Color;
in vec2 p3d_MultiTexCoord0;
out vec4 v_color;
out vec2 v_uv;
void main() {
    v_color = p3d_Color;
    v_uv = p3d_MultiTexCoord0;
    gl_Position = oblique(p3d_Vertex.xyz, 0.05);
}
