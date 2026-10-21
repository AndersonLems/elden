#version 330
// Junta cena (pixels nítidos) + bloom, aplica tonemapping, gradação de cor e efeitos de tela.
uniform sampler2D u_scene;
uniform sampler2D u_bloom1;
uniform sampler2D u_bloom2;
uniform vec4 u_grade_lift;    // rgb, exposição
uniform vec4 u_grade_gain;    // rgb, saturação
uniform vec4 u_fx;            // vinheta, granulação, aberração, tempo
uniform vec4 u_fx2;           // fade (0..1), dessaturação, força do bloom, pulso vermelho de dano
uniform vec4 u_fx3;           // brilho branco (flash), escurecer, 0, 0
uniform vec4 u_scene_uv;      // deslocamento subpixel (uv), escala uv
in vec2 v_uv;
out vec4 o_color;

vec3 aces(vec3 x) {
    return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void main() {
    vec2 uv = u_scene_uv.xy + v_uv * u_scene_uv.zw;
    vec3 col;
    if (u_fx.z > 0.0) {
        vec2 off = (v_uv - 0.5) * u_fx.z * 0.01;
        col = vec3(texture(u_scene, uv + off).r, texture(u_scene, uv).g, texture(u_scene, uv - off).b);
    } else {
        col = texture(u_scene, uv).rgb;
    }
    // Duas escalas, com energia contida para não apagar os pixels do núcleo emissivo.
    vec3 bloom = texture(u_bloom1, uv).rgb * 0.38 + texture(u_bloom2, uv).rgb * 0.48;
    col += bloom * u_fx2.z;
    col *= u_grade_lift.w;
    col = aces(col);
    // gradação: lift nas sombras, ganho nas luzes, saturação
    col = col * u_grade_gain.rgb + u_grade_lift.rgb * (1.0 - col);
    float l = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(l), col, u_grade_gain.w * (1.0 - u_fx2.y));
    // pulso de dano nas bordas
    vec2 c = v_uv - 0.5;
    float edge = dot(c, c);
    col = mix(col, vec3(0.55, 0.0, 0.02), clamp(u_fx2.w * edge * 3.0, 0.0, 0.8));
    // vinheta
    col *= 1.0 - u_fx.x * smoothstep(0.12, 0.62, edge * 1.6);
    // granulação
    col += (hash(v_uv * 800.0 + u_fx.w) - 0.5) * u_fx.y;
    col = mix(col, vec3(1.0), u_fx3.x);
    col *= 1.0 - u_fx3.y;
    col *= 1.0 - u_fx2.x;
    o_color = vec4(pow(max(col, 0.0), vec3(1.0)), 1.0);
}
