shader_type spatial;

// Lamp lenses, canopy lights and bulbs: glow only after dark (global `night`).
global uniform float night;
uniform vec4 albedo : source_color = vec4(1.0, 0.96, 0.85, 1.0);
uniform vec3 glow : source_color = vec3(1.0, 0.82, 0.55);
uniform float strength = 6.0;

void fragment() {
	ALBEDO = albedo.rgb * COLOR.rgb;
	EMISSION = glow * strength * night;
	ROUGHNESS = 0.3;
}
