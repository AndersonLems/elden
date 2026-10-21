// Uniformes e funções compartilhadas por cenário, sprites e partículas.
// Projeção ortográfica semi-isométrica: azimute 45 graus, elevação 38 graus.

uniform vec4 u_view;        // centro x, centro z, meia-largura (unid.), meia-altura (unid.)
uniform vec4 u_depth;       // z mínimo, 1/alcance, viés, 0

vec4 oblique(vec3 w, float bias) {
    vec3 p = w - vec3(u_view.x, 0.0, u_view.y);
    float sx = (p.x * 0.70710678 - p.z * 0.70710678) / u_view.z;
    float sy = (p.x * 0.435337 - p.z * -0.435337 + p.y * 0.788011) / u_view.w;
    float camera_depth = p.x * 0.557208 + p.z * 0.557208 - p.y * 0.615661;
    float d = ((camera_depth - u_depth.x) - bias) * u_depth.y;
    return vec4(sx, sy, d * 2.0 - 1.0, 1.0);
}

// Painéis de personagens permanecem verticais e voltados à câmera.
vec4 billboard(vec3 w, vec3 feet, float bias) {
    vec4 base = oblique(feet, bias);
    base.x += (w.x - feet.x) / u_view.z;
    base.y += (w.y - feet.y) * 0.788011 / u_view.w;
    return base;
}

#ifdef FRAGMENT

#define MAXL 16
uniform vec3 u_amb_sky;     // ambiente vindo de cima
uniform vec3 u_amb_ground;  // ambiente vindo de baixo / sombras
uniform vec3 u_dir_dir;     // direção PARA a luz direcional (lua, sol, brilho divino)
uniform vec3 u_dir_col;
uniform vec4 u_lpos[MAXL];  // xyz, raio
uniform vec4 u_lcol[MAXL];  // rgb já multiplicado pela intensidade, w = projeta sombra (0/1)
uniform int u_nlights;
uniform sampler2D u_occ;    // ocupação do mapa: r = altura do bloqueio / 8
uniform vec4 u_occ_info;    // origem x, origem z, 1/largura, 1/altura (em células)
uniform vec4 u_fog;         // cor rgb, intensidade da névoa baixa
uniform vec4 u_misc;        // tempo, bandas de luz, força do pontilhado, altura do chão base
uniform vec4 u_shadow_q;    // passos de sombra pontual, passos direcional, 0, 0
uniform vec4 u_render_q;    // intensidade de AO geométrico, bloom do perfil, reservado

float bayer4(vec2 p) {
    ivec2 q = ivec2(mod(p, 4.0));
    int idx = q.x + q.y * 4;
    int m[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
    return (float(m[idx]) + 0.5) / 16.0;
}

float occ_h(vec2 xz) {
    vec2 uv = (xz - u_occ_info.xy) * u_occ_info.zw;
    if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) return 0.0;
    return texture(u_occ, uv).r * 8.0;
}

float point_shadow(vec3 p, vec3 lp, float dither) {
    int steps = int(u_shadow_q.x);
    if (steps <= 0) return 1.0;
    vec3 d = lp - p;
    for (int i = 0; i < 24; i++) {
        if (i >= steps) break;
        float t = (float(i) + dither) / float(steps);
        vec3 q = p + d * t;
        if (occ_h(q.xz) > q.y + 0.02) return 0.0;
    }
    return 1.0;
}

float dir_shadow(vec3 p, float dither) {
    int steps = int(u_shadow_q.y);
    if (steps <= 0) return 1.0;
    vec3 L = normalize(u_dir_dir);
    float reach = 7.0;
    for (int i = 0; i < 24; i++) {
        if (i >= steps) break;
        float t = (float(i) + dither) / float(steps) * reach;
        vec3 q = p + L * t;
        if (occ_h(q.xz) > q.y + 0.02) return 0.0;
    }
    return 1.0;
}

// Luz total que chega em p com normal n. 'wrap' suaviza o lambert (sprites usam mais).
vec3 gather_light(vec3 p, vec3 n, float wrap, float dither) {
    float up = n.y * 0.5 + 0.5;
    vec3 col = mix(u_amb_ground, u_amb_sky, up);
    vec3 L = normalize(u_dir_dir);
    float nd = max(0.0, (dot(n, L) + wrap) / (1.0 + wrap));
    if (nd > 0.0 && dot(u_dir_col, u_dir_col) > 0.0001)
        col += u_dir_col * nd * dir_shadow(p + n * 0.04, dither);
    for (int i = 0; i < MAXL; i++) {
        if (i >= u_nlights) break;
        vec3 d = u_lpos[i].xyz - p;
        float dist = length(d);
        float r = u_lpos[i].w;
        if (dist > r) continue;
        float att = 1.0 - dist / r;
        att *= att;
        float l = max(0.0, (dot(n, d / max(dist, 1e-3)) + wrap) / (1.0 + wrap));
        if (l * att <= 0.002) continue;
        float s = u_lcol[i].w > 0.5 ? point_shadow(p + n * 0.04, u_lpos[i].xyz, dither) : 1.0;
        col += u_lcol[i].rgb * (l * att * s);
    }
    return col;
}

// Quantiza a luz em faixas (visual pixel art) com pontilhado ordenado.
vec3 band_light(vec3 light, float dither) {
    float bands = u_misc.y;
    if (bands < 1.0) return light;
    float lum = max(1e-4, dot(light, vec3(0.299, 0.587, 0.114)));
    float q = floor(lum * bands + (dither - 0.5) * u_misc.z + 0.5) / bands;
    q = max(q, lum * 0.35);
    return mix(light, light * (q / lum), 0.75);
}

vec3 apply_fog(vec3 col, vec3 p) {
    float base = u_misc.w;
    float low = clamp((base + 0.6 - p.y) / 3.0, 0.0, 1.0);
    float mist = low * u_fog.w;
    // abismos escurecem até o preto
    float pit = clamp((base - 0.5 - p.y) / 4.0, 0.0, 1.0);
    col = mix(col, u_fog.rgb, mist);
    return mix(col, vec3(0.0), pit);
}

#endif
