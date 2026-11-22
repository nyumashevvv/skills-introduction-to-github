shader_type spatial;
render_mode cull_disabled;

uniform sampler2D colormap : filter_linear_mipmap, repeat_disable;
uniform sampler2D detail : filter_linear_mipmap, repeat_enable;
uniform float map_half = 12000.0;
uniform float cell = 10.0;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 uv = (wpos.xz + map_half + cell * 0.5) / (map_half * 2.0);
	vec3 c = pow(texture(colormap, uv).rgb, vec3(2.2));
	float d1 = texture(detail, wpos.xz * 0.045).r;
	float d2 = texture(detail, wpos.xz * 0.006).r;
	float dist = length(wpos - CAMERA_POSITION_WORLD);
	float fade = clamp(1.0 - dist / 1500.0, 0.0, 1.0);
	c *= mix(1.0, 0.78 + 0.42 * d1, fade) * (0.9 + 0.2 * d2);
	ALBEDO = c;
	ROUGHNESS = 0.95;
	SPECULAR = 0.2;
}
