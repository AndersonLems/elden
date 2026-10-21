#version 330
#define FRAGMENT
#include common.glsl
uniform sampler2D p3d_Texture0;
in vec3 v_world;
in vec3 v_normal;
in vec2 v_uv;
in vec4 v_color;
out vec4 o_color;
void main() {
    vec4 albedo = texture(p3d_Texture0, v_uv);
    if (albedo.a < 0.5) discard;
    float liquid = v_color.a >= 1.5 ? 1.0 : 0.0;
    float dither = bayer4(gl_FragCoord.xy);
    vec3 n = normalize(v_normal);
    vec3 light = gather_light(v_world, n, 0.15, dither);
    light = band_light(light, dither);
    vec3 vertex_ao = mix(vec3(1.0), v_color.rgb, u_render_q.x);
    vec3 col = albedo.rgb * vertex_ao * light;
    // emissivo: v_color.a ou texels do atlas com alfa < 0.95 (vitrais, runas, brasas)
    float vem = liquid > 0.5 ? v_color.a - 2.0 : v_color.a;
    float emis = max(vem, albedo.a < 0.95 ? 1.0 : 0.0);
    if (liquid > 0.5) {
        // superfície líquida: ondulação de brilho e reflexos pontilhados
        float tt = u_misc.x;
        float w = sin(v_world.x * 2.1 + tt * 1.3) * sin(v_world.z * 1.7 - tt * 1.1) + sin((v_world.x + v_world.z) * 3.3 + tt * 2.0) * 0.5;
        float glint = step(0.92, fract(sin(dot(floor(v_world.xz * 16.0), vec2(12.9898, 78.233)) + floor(tt * 3.0)) * 43758.5453));
        col *= 0.85 + 0.25 * w;
        col += albedo.rgb * (glint * 0.6 + max(0.0, w) * 0.2) * (0.4 + vem);
        emis *= 0.75 + 0.35 * w;
    }
    col += albedo.rgb * emis * 1.6;
    col = apply_fog(col, v_world);
    o_color = vec4(col, 1.0);
}
