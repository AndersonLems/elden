#version 330
uniform sampler2D u_ui;
in vec2 v_uv;
out vec4 o_color;
void main() {
    vec4 c = texture(u_ui, v_uv);
    if (c.a <= 0.0) discard;
    o_color = c;
}
