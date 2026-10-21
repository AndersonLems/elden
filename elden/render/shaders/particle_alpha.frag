#version 330
// partículas opacas/semitransparentes (poeira, sangue, fumaça, lascas) com pontilhado
in vec4 v_color;
in vec2 v_uv;
out vec4 o_color;
void main() {
    if (v_color.a <= 0.02) discard;
    ivec2 q = ivec2(gl_FragCoord.xy);
    float th = (float(((q.x & 1) << 1) | (q.y & 1)) + 0.5) / 4.0;
    if (v_color.a < th) discard;
    o_color = vec4(v_color.rgb, 1.0);
}
