shader_type spatial;
render_mode cull_disabled;

// Road surfaces.
// COLOR.r junction (no markings) · COLOR.g width/50 · COLOR.b material: 0 asphalt, .5 concrete, 1 dirt
// COLOR.a markings: 1 two-lane road, .6 runway
// UV.x metres across the strip · UV.y metres along the road
// UV2.x strip: 0 carriageway, 1 curb face, 2 sidewalk, 3 verge · UV2.y per-road seed

uniform sampler2D noise : filter_linear_mipmap, repeat_enable;

varying vec3 wpos;

float hash(float n) { return fract(sin(mod(n, 289.0) * 12.9898 + 0.3) * 43758.5453); }

vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	// pull the surface slightly towards the camera so it never fights the terrain
	vec3 to_cam = CAMERA_POSITION_WORLD - wpos;
	float d = length(to_cam);
	vec3 shifted = wpos + to_cam / d * clamp(d * 0.0015, 0.0, 2.5);
	VERTEX = (inverse(MODEL_MATRIX) * vec4(shifted, 1.0)).xyz;
}

void fragment() {
	float strip = floor(UV2.x + 0.5);
	float seed = UV2.y;
	float mat = COLOR.b;
	float w = COLOR.g * 50.0;
	float x = UV.x;
	float y = UV.y;
	vec2 p = wpos.xz;
	float n1 = texture(noise, p * 0.9).r;          // fine grain
	float n2 = texture(noise, p * 0.11).r;         // patches
	float n3 = texture(noise, p * 0.023).r;        // large wear
	vec3 col;
	float rough = 0.9;

	if (strip < 0.5) {
		float u = x / max(w, 0.1);                 // 0..1 across
		if (mat < 0.25) {
			// asphalt: grain, repaired patches, polished wheel tracks, dusty edges
			col = vec3(0.075, 0.077, 0.08) * (0.8 + 0.45 * n1);
			if (n2 > 0.62) col = mix(col, vec3(0.045, 0.046, 0.05), 0.7);
			if (n2 < 0.3) col = mix(col, vec3(0.11, 0.105, 0.1), 0.5);
			float tracks = exp(-pow((fract(u * 2.0) - 0.5) * 6.0, 2.0));
			col *= 1.0 - 0.15 * tracks * (1.0 - COLOR.r);
			float edge = min(x, w - x);
			col = mix(lin(vec3(0.55, 0.48, 0.38)), col, smoothstep(0.0, 0.45 + 0.4 * n1, edge));
			rough = 0.85 - 0.15 * tracks;
			// markings
			float mk = COLOR.a * (1.0 - COLOR.r);
			if (mk > 0.8) {
				bool centre = abs(x - w * 0.5) < 0.07 && fract(y / 9.0) < 0.45;
				bool edges = abs(x - 0.35) < 0.06 || abs(x - (w - 0.35)) < 0.06;
				float paint = 0.85 + 0.15 * n1;
				if (centre) col = lin(vec3(0.92, 0.72, 0.12)) * paint;
				if (edges) col = lin(vec3(0.9)) * paint;
			} else if (mk > 0.5) {
				bool centre = abs(x - w * 0.5) < 0.45 && fract(y / 50.0) < 0.6;
				bool edges = abs(x - 1.5) < 0.45 || abs(x - (w - 1.5)) < 0.45;
				if (centre || edges) col = lin(vec3(0.9)) * (0.85 + 0.15 * n1);
			}
		} else if (mat < 0.75) {
			// poured concrete lane: slabs with joints, stains
			col = lin(vec3(0.62, 0.61, 0.58)) * (0.85 + 0.25 * n1);
			col *= 0.85 + 0.2 * n3;
			col *= 1.0 - 0.1 * smoothstep(0.6, 0.75, n2);
			float jy = abs(fract(y / 4.5) - 0.5) * 4.5;
			float jx = abs(x - w * 0.5);
			if (jy > 2.2 || jx < 0.02) col *= 0.45;
			float edge = min(x, w - x);
			col = mix(lin(vec3(0.5, 0.45, 0.36)), col, smoothstep(0.0, 0.3, edge));
		} else {
			// red laterite track: ruts, gravel, grass down the middle
			col = lin(vec3(0.62, 0.38, 0.24)) * (0.75 + 0.4 * n1);
			col = mix(col, lin(vec3(0.5, 0.42, 0.34)), 0.4 * n3);
			float rut = exp(-pow((abs(u - 0.5) - 0.24) * 14.0, 2.0));
			col *= 1.0 - 0.25 * rut;
			float grass = smoothstep(0.12, 0.04, abs(u - 0.5)) * smoothstep(0.35, 0.6, n1 + n2 * 0.5);
			col = mix(col, lin(vec3(0.3, 0.45, 0.18)) * (0.7 + 0.5 * n1), grass);
			float edge = min(x, w - x);
			col = mix(lin(vec3(0.35, 0.45, 0.2)), col, smoothstep(0.0, 0.6 + 0.6 * n2, edge));
			rough = 1.0;
		}
	} else if (strip < 1.5) {
		// curb face: red/white or yellow/white paint on main streets, else plain
		col = lin(vec3(0.7, 0.69, 0.66)) * (0.92 + 0.08 * n2);
		float h = hash(seed * 31.0);
		if (h < 0.55) {
			bool band = fract(y / 1.0) < 0.5;
			vec3 paint = h < 0.35 ? vec3(0.75, 0.12, 0.1) : vec3(0.9, 0.75, 0.1);
			col = band ? lin(paint) : lin(vec3(0.92));
			col *= 0.9 + 0.12 * n2;
		}
	} else if (strip < 2.5) {
		// sidewalk tiles
		vec2 t = vec2(x, y) / 0.4;
		vec2 g = abs(fract(t) - 0.5);
		float joint = step(0.46, max(g.x, g.y));
		float tone = hash(floor(t.x) * 7.0 + floor(t.y) * 13.0 + seed * 50.0);
		col = mix(lin(vec3(0.74, 0.71, 0.66)), lin(vec3(0.78, 0.62, 0.54)), step(0.85, tone));
		col *= 0.93 + 0.07 * tone;
		col *= 1.0 - 0.2 * joint;
		col *= 0.88 + 0.15 * n2;
	} else {
		// gravel verge fading into the ground
		col = lin(vec3(0.64, 0.58, 0.48)) * (0.8 + 0.35 * n1);
		col = mix(col, lin(vec3(0.33, 0.42, 0.2)) * (0.7 + 0.4 * n2), smoothstep(0.3, 0.9, n2) * 0.5);
		rough = 1.0;
	}
	ALBEDO = col;
	ROUGHNESS = rough;
}
