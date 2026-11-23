shader_type spatial;
render_mode cull_disabled;

// Leaves, palms and trunks. Sways in the wind (more towards the top),
// per-instance tint from INSTANCE_CUSTOM.rgb, light shining through leaves.

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool use_alpha = true;
uniform vec4 albedo_color : source_color = vec4(1.0);
uniform float sway = 1.0;
uniform float backlight = 0.35;

varying vec3 tint;

void vertex() {
	tint = INSTANCE_CUSTOM.rgb;
	if (tint == vec3(0.0)) tint = vec3(1.0);
	vec3 wp = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float h = max(VERTEX.y, 0.0);
	float ph = wp.x * 0.071 + wp.z * 0.053;
	float w = sin(TIME * 1.1 + ph) * 0.6 + sin(TIME * 2.7 + ph * 1.7 + VERTEX.x) * 0.25;
	VERTEX.x += w * 0.0022 * h * h * sway;
	VERTEX.z += cos(TIME * 0.83 + ph) * 0.0014 * h * h * sway;
}

void fragment() {
	vec4 t = texture(albedo_tex, UV);
	if (use_alpha && t.a < 0.5) discard;
	ALBEDO = t.rgb * albedo_color.rgb * tint;
	ROUGHNESS = 0.85;
	SPECULAR = 0.25;
	BACKLIGHT = vec3(backlight) * t.rgb * 1.6;
}
