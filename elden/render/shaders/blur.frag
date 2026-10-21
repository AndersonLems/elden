#version 330
uniform sampler2D u_src;
uniform vec4 u_dir;        // passo em uv (x, y)
in vec2 v_uv;
out vec4 o_color;
void main() {
    float w[5] = float[5](0.227, 0.195, 0.122, 0.054, 0.016);
    vec3 c = texture(u_src, v_uv).rgb * w[0];
    for (int i = 1; i < 5; i++) {
        c += texture(u_src, v_uv + u_dir.xy * float(i)).rgb * w[i];
        c += texture(u_src, v_uv - u_dir.xy * float(i)).rgb * w[i];
    }
    o_color = vec4(c, 1.0);
}
