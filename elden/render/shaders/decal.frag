#version 330
// marcas no chão: avisos (telegráficos) de área, anéis, feixes e círculos de runas
uniform vec4 u_decal;     // forma (0 círculo, 1 anel, 2 retângulo), raio interno (0..1), progresso, pulso
uniform vec4 u_decal_col; // rgb, alfa
uniform vec4 u_misc;
in vec4 v_color;
in vec2 v_uv;
out vec4 o_color;
void main() {
    vec2 d = v_uv * 2.0 - 1.0;
    float shape = u_decal.x;
    float a = u_decal_col.a;
    float t = u_misc.x;
    if (shape < 0.5) {
        float r = length(d);
        if (r > 1.0) discard;
        float edge = r > 0.86 ? 1.0 : 0.0;
        float fill = r < u_decal.z ? 0.55 : 0.18;
        a *= max(edge, fill);
    } else if (shape < 1.5) {
        float r = length(d);
        if (r > 1.0 || r < u_decal.y) discard;
        a *= 0.8;
    } else {
        float edge = (abs(d.x) > 0.86 || abs(d.y) > 0.94) ? 1.0 : 0.0;
        float fill = (v_uv.y < u_decal.z) ? 0.5 : 0.16;
        a *= max(edge, fill);
    }
    a *= 0.75 + 0.25 * sin(t * u_decal.w * 6.283);
    ivec2 q = ivec2(gl_FragCoord.xy);
    if (a < 0.5 && ((q.x + q.y) & 1) == 0) discard;
    o_color = vec4(u_decal_col.rgb, clamp(a, 0.0, 1.0));
}
