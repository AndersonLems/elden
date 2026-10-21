#version 330
#define FRAGMENT
#include common.glsl
uniform sampler2D p3d_Texture0;
uniform vec4 u_flash;      // rgb, quantidade (piscar de dano / ruptura)
uniform vec4 u_tint;       // rgb multiplicador, alfa
uniform vec4 u_glow;       // rgb emissivo extra, força do brilho da máscara emissiva
in vec3 v_world;
in vec2 v_uv;
out vec4 o_color;
void main() {
    vec4 tex = texture(p3d_Texture0, v_uv);
    if (tex.a < 0.02) discard;
    float dither = bayer4(gl_FragCoord.xy);
    // alfa entre 0.02 e 0.6 marca pixels emissivos (olhos, magia, brasas) na folha gerada
    float emissive = tex.a < 0.6 ? 1.0 : 0.0;
    vec3 n = normalize(vec3(0.0, 0.45, -1.0));
    vec3 p = vec3(v_world.x, v_world.y, v_world.z - 0.3);
    vec3 light = gather_light(p, n, 0.6, dither);
    light = band_light(light, dither);
    vec3 col = tex.rgb * u_tint.rgb * light;
    col += tex.rgb * emissive * (0.85 + u_glow.w);
    col += u_glow.rgb;
    col = mix(col, u_flash.rgb, u_flash.a);
    col = apply_fog(col, v_world);
    if (u_tint.a < 1.0 && dither > u_tint.a) discard;   // transparência pontilhada (pixel art)
    o_color = vec4(col, 1.0);
}
