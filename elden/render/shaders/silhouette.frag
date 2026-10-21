#version 330
// silhueta do jogador quando atrás de paredes (desenhada só onde o depth falha)
uniform sampler2D p3d_Texture0;
uniform vec4 u_tint;
in vec3 v_world;
in vec2 v_uv;
out vec4 o_color;
void main() {
    vec4 tex = texture(p3d_Texture0, v_uv);
    if (tex.a < 0.02) discard;
    ivec2 q = ivec2(gl_FragCoord.xy);
    if (((q.x + q.y) & 1) == 0) discard;
    o_color = vec4(u_tint.rgb, 1.0);
}
