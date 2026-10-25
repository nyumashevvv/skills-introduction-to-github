shader_type spatial;
render_mode cull_disabled;
// A digital ad screen: the picture glows, scanlines crawl, now and then the image tears and the panel flickers.
uniform sampler2D tex : source_color, filter_linear_mipmap;
uniform float energy = 2.2;
uniform float seed = 0.0;

void fragment() {
	float t = TIME + seed * 17.0;
	float tear = step(0.96, fract(sin(floor(t * 5.0) * 43.7 + seed) * 4375.5));
	vec2 uv = UV;
	uv.x += tear * 0.04 * sin(uv.y * 60.0 + t * 30.0);
	vec3 c = texture(tex, uv).rgb;
	float scan = 0.82 + 0.18 * sin(uv.y * 500.0 - t * 6.0);
	float flicker = 0.92 + 0.08 * sin(t * 31.0) * sin(t * 7.3);
	ALBEDO = c * 0.05;
	ROUGHNESS = 0.15;
	EMISSION = c * energy * scan * flicker;
}
