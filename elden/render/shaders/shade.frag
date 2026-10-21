#version 330
// sombras de contato (elipses escuras sob personagens) e marcas no chão com mistura alfa
in vec4 v_color;
in vec2 v_uv;
out vec4 o_color;
void main() {
    vec2 d = v_uv * 2.0 - 1.0;
    float r = dot(d, d);
    if (r > 1.0) discard;
    float a = v_color.a * (r < 0.55 ? 1.0 : 0.6);
    o_color = vec4(v_color.rgb, a);
}
