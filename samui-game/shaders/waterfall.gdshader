shader_type spatial;
render_mode cull_disabled, blend_mix, depth_draw_opaque;

// Falling water: white streaks streaming down (UV.y = 0 at the top), foam at the foot.
uniform sampler2D noise : filter_linear_mipmap, repeat_enable;

void fragment() {
	vec2 uv = UV;
	float n1 = texture(noise, vec2(uv.x * 3.0, uv.y * 0.8 - TIME * 1.4)).r;
	float n2 = texture(noise, vec2(uv.x * 7.0 + 0.3, uv.y * 1.5 - TIME * 2.2)).r;
	float streak = smoothstep(0.35, 0.75, n1 * 0.6 + n2 * 0.5);
	float edge = smoothstep(0.0, 0.12, uv.x) * smoothstep(1.0, 0.88, uv.x);
	vec3 c = mix(vec3(0.55, 0.7, 0.72), vec3(0.97), streak);
	c = mix(c, vec3(1.0), smoothstep(0.8, 1.0, uv.y));
	ALBEDO = c;
	ALPHA = clamp((0.45 + 0.5 * streak) * edge + smoothstep(0.85, 1.0, uv.y) * 0.4, 0.0, 0.95);
	ROUGHNESS = 0.2;
}
