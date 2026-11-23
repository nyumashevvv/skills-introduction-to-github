shader_type spatial;
render_mode cull_disabled;

// Procedural facades for Samui building styles.
// COLOR.rgb wall colour (sRGB) · COLOR.a = (style * 32 + seed) / 255
//   style: 0 house, 1 shophouse, 2 resort bungalow, 3 hotel, 4 villa, 5 temple, 6 warehouse, 7 Fisherman's Village
// UV.x metres along the wall, UV.y metres above the ground
// UV2.x wall length (m), UV2.y wall height to the eaves (m)

const float FLOOR_H = 3.2;
global uniform float night;

float hash(float n) { return fract(sin(mod(n, 289.0) * 12.9898 + 0.5) * 43758.5453); }
vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }
vec3 GOLD_FIX() { return vec3(0.95, 0.72, 0.22); }

void fragment() {
	vec3 wall = lin(COLOR.rgb);
	float code = floor(COLOR.a * 255.0 + 0.5);
	float style = floor(code / 32.0);
	float seed = (code - style * 32.0) / 32.0;
	float u = UV.x;
	float v = UV.y;
	float len = floor(UV2.x * 10.0 + 0.5) / 10.0;
	float H = floor(UV2.y * 10.0 + 0.5) / 10.0;
	bool minimart = H > 500.0;          // an OSM convenience store is inside this building
	if (minimart) H -= 1000.0;
	vec3 col = wall;
	float rough = 0.9;
	float metal = 0.0;
	vec3 emit = vec3(0.0);       // lit windows, shops and signs after dark

	bool house = style < 0.5, shop = abs(style - 1.0) < 0.5, bung = abs(style - 2.0) < 0.5, hotel = abs(style - 3.0) < 0.5;
	bool villa = abs(style - 4.0) < 0.5, temple = abs(style - 5.0) < 0.5, big = abs(style - 6.0) < 0.5, fisher = abs(style - 7.0) < 0.5;
	bool tall = H > 8.0 || hotel;

	float floor_h = temple ? max(H, 3.0) : (big ? max(H, 3.0) : FLOOR_H);
	float floors = max(1.0, floor((H + 0.4) / floor_h));
	float fl = floor(v / floor_h);
	float fv = v - fl * floor_h;
	bool shopfront = (shop && H > 4.0) || (fisher) || (house && H > 5.0 && hash(seed * 7.0) < 0.3);

	// wall material
	if (bung || fisher) {
		// timber boards: vertical on bungalows, horizontal on old shophouses
		float board = bung ? fract(u / 0.18) : fract(v / 0.22);
		float id = bung ? floor(u / 0.18) : floor(v / 0.22);
		if (wall.r > wall.b * 1.3 || fisher) {
			col *= 0.85 + 0.25 * hash(id + seed * 40.0);
			if (board < 0.08) col *= 0.55;
		}
	} else if (big) {
		col *= 0.9 + 0.1 * step(0.5, fract(u / 0.25));   // corrugated sheet
		metal = 0.25;
		rough = 0.6;
	}
	if (v < 0.35) col = (temple ? lin(vec3(0.75, 0.15, 0.1)) : wall * 0.55);   // plinth

	// bays along the wall
	float bay_w = tall ? 3.6 : (shopfront ? 4.0 : (villa ? 4.5 : 3.0));
	if (temple) bay_w = 3.2;
	if (big) bay_w = 6.0;
	float n = max(1.0, floor(len / bay_w));
	float bay = len / n;
	float idx = floor(u / bay);
	float fu = (u - idx * bay) / bay;
	float wall_id = floor(len * 10.0 + seed * 255.0 * 7.0);

	bool usable = len > 1.8 && v < floors * floor_h - 0.2;
	if (usable) {
		float hw = clamp(0.9 / bay, 0.14, 0.32);
		if (tall) hw = clamp(1.3 / bay, 0.2, 0.42);
		if (villa) hw = 0.42;
		if (temple) hw = clamp(0.45 / bay, 0.08, 0.2);
		float y0 = fl == 0.0 ? 0.9 : 0.85;
		float y1 = tall ? 2.6 : 2.25;
		if (villa) { y0 = 0.15; y1 = 2.9; }
		if (temple) { y0 = 1.4; y1 = min(floor_h - 1.0, 5.5); }
		if (big) { y0 = floor_h - 1.6; y1 = floor_h - 0.6; }
		bool door_bay = fl == 0.0 && idx == floor(hash(wall_id) * n) && hash(wall_id + 3.0) < (big ? 0.9 : 0.6);

		if (fl == 0.0 && shopfront && !door_bay) {
			if (fu > 0.05 && fu < 0.95 && fv < 2.7) {
				bool open = hash(wall_id + idx * 1.3) < (fisher ? 0.7 : 0.45);
				if (open) {
					// shop interior with warm light and shelves
					col = vec3(0.05, 0.04, 0.03) + vec3(0.35, 0.22, 0.08) * smoothstep(2.6, 0.4, fv);
					emit = vec3(1.0, 0.72, 0.38) * 1.6 * night * smoothstep(2.7, 0.6, fv);
					if (abs(fract(fv * 2.2) - 0.5) < 0.04 && fv < 2.2) col += vec3(0.08);
					rough = 0.4;
				} else if (fisher) {
					col = lin(vec3(0.4, 0.26, 0.15)) * (0.85 + 0.15 * step(0.5, fract(u / 0.25)));
				} else {
					float rib = step(0.5, fract(fv * 9.0));
					col = vec3(0.42, 0.44, 0.46) * (0.85 + 0.15 * rib);
					metal = 0.4;
					rough = 0.5;
				}
			}
			if (fv > 2.75 && fv < 3.15 && fu > 0.02 && fu < 0.98 && !fisher) {
				float h = hash(wall_id + idx * 5.1);
				vec3 sign = h < 0.25 ? vec3(0.85, 0.2, 0.15) : (h < 0.5 ? vec3(0.15, 0.35, 0.75) : (h < 0.75 ? vec3(0.95, 0.8, 0.15) : vec3(0.1, 0.55, 0.3)));
				col = lin(sign * (0.75 + 0.25 * hash(h)));
				// pale "lettering" stripes
				if (abs(fv - 2.95) < 0.07 && fract(u * 1.7 + h * 3.0) < 0.55) col = lin(vec3(0.95));
				emit = col * 2.5 * night * step(0.4, hash(h + 2.0));
			}
		} else if (door_bay) {
			float dw = big ? 0.38 : (bung ? clamp(0.9 / bay, 0.2, 0.42) : clamp(0.5 / bay, 0.12, 0.3));
			float dh = big ? min(floor_h - 0.6, 4.0) : (temple ? 3.2 : 2.1);
			if (abs(fu - 0.5) < dw + 0.04 / bay && fv < dh + 0.08) {
				col = temple ? lin(GOLD_FIX()) : vec3(0.9);
				if (abs(fu - 0.5) < dw && fv < dh) {
					float k = hash(seed * 3.3);
					vec3 door = k < 0.33 ? vec3(0.35, 0.18, 0.08) : (k < 0.66 ? vec3(0.08, 0.25, 0.35) : vec3(0.55, 0.08, 0.06));
					if (temple) door = vec3(0.55, 0.06, 0.04);
					col = lin(door);
					if (bung) {
						// sliding glass door
						col = mix(vec3(0.02, 0.04, 0.06), vec3(0.3, 0.42, 0.5), 0.3 + 0.4 * fv / dh);
						if (abs(fu - 0.5) < 0.01) col = lin(vec3(0.3, 0.2, 0.12));
						rough = 0.1;
					} else if (big) {
						col = vec3(0.35, 0.37, 0.4) * (0.85 + 0.15 * step(0.5, fract(fv * 6.0)));
						metal = 0.5;
					} else {
						float px = abs(fu - 0.5) / dw;
						if (px > 0.12 && px < 0.82 && (abs(fv - 0.6) < 0.4 || abs(fv - 1.55) < 0.4)) col *= 0.75;
						if (temple && px < 0.04) col = lin(GOLD_FIX());
					}
				}
			}
		} else if (abs(fu - 0.5) < hw && fv > y0 && fv < y1) {
			float fx = abs(fu - 0.5) / hw;
			float fy = (fv - y0) / (y1 - y0);
			float frame_x = (villa ? 0.04 : 0.07) / (hw * bay);
			float frame_y = 0.07 / (y1 - y0);
			bool frame = fx > 1.0 - frame_x || fy < frame_y || fy > 1.0 - frame_y || abs(fu - 0.5) < 0.025 / bay;
			float style_f = hash(seed * 11.0);
			vec3 frame_col = style_f < 0.5 ? vec3(0.92) : (style_f < 0.8 ? vec3(0.25, 0.15, 0.08) : vec3(0.18, 0.2, 0.22));
			if (villa) frame_col = vec3(0.12);
			if (bung || fisher) frame_col = vec3(0.3, 0.2, 0.12);
			if (temple) frame_col = GOLD_FIX();
			if (temple && fy > 0.8 && fx > 1.0 - (fy - 0.8) * 5.0) {
				col = wall;   // pointed top on temple windows
			} else if (frame) {
				col = lin(frame_col);
				if (temple) { metal = 0.8; rough = 0.3; }
			} else if (temple) {
				col = lin(vec3(0.55, 0.06, 0.04));   // red shutters
			} else {
				float refl = 0.25 + 0.35 * smoothstep(0.0, 1.0, fy) + 0.15 * hash(wall_id + idx + fl * 9.0);
				col = mix(vec3(0.02, 0.04, 0.06), vec3(0.35, 0.5, 0.62), refl * 0.5);
				if (hash(wall_id + idx * 3.0 + fl * 13.0) < 0.3 && fy > 0.55 && !villa) col = lin(vec3(0.85, 0.8, 0.7)) * 0.6;
				rough = 0.08;
				metal = 0.2;
				float lit = hash(wall_id * 0.37 + idx * 7.0 + fl * 3.0 + 1.0);
				if (lit < (hotel || villa ? 0.6 : 0.42)) {
					vec3 lamp = lit < 0.12 ? vec3(0.75, 0.85, 1.0) : vec3(1.0, 0.74, 0.42);
					emit = lamp * (0.8 + 0.6 * fy) * night;
				}
			}
			if (fv > y0 - 0.1 && fv < y0 && !villa) col = wall * 0.7;
		} else if ((hash(seed * 5.0) < 0.35 || fisher) && !tall && !villa && !temple && !big && abs(fu - 0.5) < hw * 1.55 && abs(fu - 0.5) >= hw && fv > y0 && fv < y1) {
			vec3 sh = hash(seed * 9.0) < 0.5 ? vec3(0.1, 0.32, 0.25) : vec3(0.42, 0.24, 0.12);
			col = lin(sh) * (0.85 + 0.15 * step(0.5, fract(fv * 6.0)));
		}
		// balconies on hotels and some shophouses
		if (tall && fl > 0.0 && fv < 1.0 && fv > 0.0 && abs(fu - 0.5) < hw + 0.05) {
			if (fv > 0.9 || fract(u * 6.0) < 0.15) col = lin(vec3(0.85));
		}
		// villa: timber slat panel on part of the wall
		if (villa && abs(fu - 0.5) >= hw + 0.02 && hash(wall_id + idx) < 0.5) {
			col = lin(vec3(0.5, 0.33, 0.2)) * (0.8 + 0.2 * step(0.4, fract(u / 0.12)));
		}
	}
	// temple: red-and-gold band under the eaves
	// 24-hour mini-mart: glass shopfront and a sign band on the ground floor
	if (minimart && len > 4.0 && v < 3.6) {
		if (v < 2.75 && v > 0.15) {
			float m = fract(u / 1.6);
			col = (m < 0.05 || v < 0.25 || v > 2.65) ? lin(vec3(0.93)) : mix(vec3(0.02, 0.05, 0.06), vec3(0.75, 0.72, 0.6), 0.25 + 0.2 * smoothstep(2.6, 0.4, v));
			if (m >= 0.05 && v >= 0.25 && v <= 2.65) emit = vec3(0.92, 0.96, 1.0) * 2.2 * night;
			rough = 0.1;
			metal = 0.1;
		} else if (v >= 2.75) {
			col = lin(vec3(0.12, 0.54, 0.54));
			if (v < 2.88) col = lin(vec3(0.91, 0.46, 0.12));
			if (abs(v - 3.22) < 0.12 && fract(u * 1.3) < 0.6 && abs(u - len * 0.5) < min(3.0, len * 0.35)) col = lin(vec3(0.97));
			rough = 0.4;
			emit = col * 2.5 * night;
		}
	}
	if (temple && H - v < 0.9 && H - v > 0.0) {
		col = lin(fract(u / 0.6) < 0.5 ? vec3(0.7, 0.1, 0.06) : GOLD_FIX());
		metal = 0.5;
	}
	if (floors > 1.0 && fl > 0.0 && fv < 0.18 && v < floors * floor_h && !bung) col *= 0.78;
	float top_dist = H - v;
	if (top_dist < 0.35 && top_dist > -0.01 && !temple) col *= 0.6 + 0.4 * (top_dist / 0.35);
	if (v > H) col = wall * 0.92;
	ALBEDO = col;
	ROUGHNESS = rough;
	METALLIC = metal;
	EMISSION = emit;
}

