shader_type sky;

// Tropical sky: day gradient, sunset glow around the sun, night with stars.
// night 0..1 (0 day, 1 full night), dusk 0..1 (sunrise/sunset strength).

uniform vec3 top_day : source_color = vec3(0.16, 0.42, 0.82);
uniform vec3 horizon_day : source_color = vec3(0.66, 0.80, 0.93);
uniform vec3 top_night : source_color = vec3(0.01, 0.02, 0.06);
uniform vec3 horizon_night : source_color = vec3(0.04, 0.07, 0.14);
uniform vec3 sunset : source_color = vec3(1.0, 0.45, 0.18);
uniform float night = 0.0;
uniform float dusk = 0.0;
uniform vec3 moon_dir = vec3(0.3, 0.6, -0.74);

float hash3(vec3 p) {
	p = fract(p * vec3(443.897, 441.423, 437.195));
	p += dot(p, p.yzx + 19.19);
	return fract((p.x + p.y) * p.z);
}

void sky() {
	vec3 d = normalize(EYEDIR);
	float h = clamp(d.y, 0.0, 1.0);
	vec3 day = mix(horizon_day, top_day, pow(h, 0.55));
	vec3 nite = mix(horizon_night, top_night, pow(h, 0.5));
	vec3 c = mix(day, nite, night);
	if (d.y < 0.0) c = mix(c, c * 0.6, clamp(-d.y * 4.0, 0.0, 1.0));
	vec3 sun = LIGHT0_ENABLED ? LIGHT0_DIRECTION : vec3(0.0, 1.0, 0.0);
	float to_sun = max(dot(d, sun), 0.0);
	// sunset / sunrise glow, strongest at the horizon towards the sun
	// dusk: dim the day sky towards deep blue, warm band low over the horizon
	c = mix(c, vec3(0.12, 0.18, 0.38) * (0.6 + 0.4 * h), dusk * 0.75);
	float band = pow(1.0 - h, 5.0);
	c += sunset * dusk * band * (0.35 + 1.4 * pow(to_sun, 6.0));
	c += vec3(0.55, 0.22, 0.35) * dusk * 0.35 * pow(1.0 - h, 2.5) * (1.0 - to_sun);
	// sun disk
	if (LIGHT0_ENABLED && to_sun > 0.99993) c += LIGHT0_COLOR * LIGHT0_ENERGY * 6.0;
	// stars and moon
	if (night > 0.01 && d.y > 0.0) {
		vec3 p = floor(d * 420.0);
		float s = hash3(p);
		float star = step(0.9975, s) * (0.4 + 0.6 * hash3(p + 7.0));
		c += vec3(star) * night * smoothstep(0.0, 0.25, h);
		float m = dot(d, normalize(moon_dir));
		c += vec3(0.9, 0.92, 1.0) * smoothstep(0.99955, 0.9997, m) * night * 1.5;
		c += vec3(0.08, 0.1, 0.16) * pow(max(m, 0.0), 40.0) * night;
	}
	COLOR = c;
}
