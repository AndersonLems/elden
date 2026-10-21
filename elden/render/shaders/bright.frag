#version 330
// extrai as partes muito claras (HDR) e reduz a resolução para o bloom
uniform sampler2D u_src;
uniform vec4 u_texel;      // 1/largura, 1/altura da origem, limiar, suavidade
in vec2 v_uv;
out vec4 o_color;
void main() {
    vec3 c = vec3(0.0);
    c += texture(u_src, v_uv + u_texel.xy * vec2(-0.5, -0.5)).rgb;
    c += texture(u_src, v_uv + u_texel.xy * vec2( 0.5, -0.5)).rgb;
    c += texture(u_src, v_uv + u_texel.xy * vec2(-0.5,  0.5)).rgb;
    c += texture(u_src, v_uv + u_texel.xy * vec2( 0.5,  0.5)).rgb;
    c *= 0.25;
    float l = max(c.r, max(c.g, c.b));
    float k = clamp((l - u_texel.z) / max(u_texel.w, 1e-3), 0.0, 1.0);
    o_color = vec4(c * k, 1.0);
}
