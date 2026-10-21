#version 330
// partículas, rastros de lâmina e ondas: cor HDR aditiva, sem iluminação
in vec4 v_color;
in vec2 v_uv;
out vec4 o_color;
void main() {
    if (v_color.a <= 0.003) discard;
    o_color = vec4(v_color.rgb * v_color.a, 1.0);
}
