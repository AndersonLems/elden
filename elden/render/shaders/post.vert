#version 330
uniform vec4 u_rect;        // escala xy e deslocamento zw em coordenadas de tela (-1..1)
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 v_uv;
void main() {
    v_uv = p3d_MultiTexCoord0;
    gl_Position = vec4(p3d_Vertex.xy * u_rect.xy + u_rect.zw, 0.0, 1.0);
}
