shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled;

uniform vec3 deep : source_color = vec3(0.01, 0.10, 0.20);
uniform vec3 shallow : source_color = vec3(0.04, 0.35, 0.42);
uniform sampler2D waves : filter_linear_mipmap, repeat_enable;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = wpos.xz;
	float t = TIME;
	float a = texture(waves, p * 0.02 + vec2(t * 0.010, t * 0.006)).r;
	float b = texture(waves, p * 0.05 - vec2(t * 0.012, -t * 0.009)).r;
	float c = texture(waves, p * 0.0025 + vec2(t * 0.002, 0.0)).r;
	vec3 n = normalize(vec3((a - 0.5) * 0.35 + (b - 0.5) * 0.25, 1.0, (b - 0.5) * 0.35 - (a - 0.5) * 0.2));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALBEDO = mix(shallow, deep, 0.4 + 0.3 * c);
	ALPHA = clamp(0.22 + fres * 0.55, 0.0, 0.85);
	ROUGHNESS = 0.08;
	METALLIC = 0.0;
	SPECULAR = 0.6;
}
