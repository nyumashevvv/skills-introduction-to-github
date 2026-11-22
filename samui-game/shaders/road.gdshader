shader_type spatial;

// COLOR.rgb = surface colour, COLOR.a = 1 for main roads with markings
// UV.x across road 0..1, UV.y = metres along road
void fragment() {
	vec3 c = COLOR.rgb;
	if (COLOR.a > 0.5) {
		float x = UV.x;
		bool center = abs(x - 0.5) < 0.018 && fract(UV.y / 9.0) < 0.5;
		bool edge = abs(x - 0.06) < 0.015 || abs(x - 0.94) < 0.015;
		if (center) c = vec3(0.85, 0.75, 0.25);
		if (edge) c = vec3(0.8);
	}
	ALBEDO = pow(c, vec3(2.2));
	ROUGHNESS = 0.85;
}
