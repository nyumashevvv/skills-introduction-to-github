shader_type spatial;
render_mode cull_disabled;

// Procedural facade for building walls.
// COLOR.rgb  wall colour (sRGB), COLOR.a  per-building random seed 0..1
// UV.x  metres along this wall, UV.y  metres above the ground at the building
// UV2.x wall length (m), UV2.y  height of walls (m); UV2.y < 0 marks a parapet-free plain surface

const float FLOOR_H = 3.2;

float hash(float n) { return fract(sin(mod(n, 289.0) * 12.9898 + 0.5) * 43758.5453); }

void fragment() {
	vec3 wall = pow(COLOR.rgb, vec3(2.2));
	float seed = floor(COLOR.a * 255.0 + 0.5) / 255.0;   // quantised so it is exactly constant per building
	float u = UV.x;
	float v = UV.y;
	float len = floor(UV2.x * 10.0 + 0.5) / 10.0;
	float H = floor(UV2.y * 10.0 + 0.5) / 10.0;
	vec3 col = wall;
	float rough = 0.9;
	float metal = 0.0;

	float floors = max(1.0, floor((H + 0.4) / FLOOR_H));
	float fl = floor(v / FLOOR_H);
	float fv = v - fl * FLOOR_H;
	bool tall = H > 8.0;
	bool shop = !tall && H > 5.0 && hash(seed * 7.0) < 0.45;

	// bay layout along the wall
	float bay_w = tall ? 3.6 : (shop ? 4.2 : 3.0);
	float n = max(1.0, floor(len / bay_w));
	float bay = len / n;
	float idx = floor(u / bay);
	float fu = (u - idx * bay) / bay;
	float wall_id = floor(len * 10.0 + seed * 255.0 * 7.0);

	// plinth
	if (v < 0.35) {
		col = wall * 0.55;
	}

	bool usable = len > 1.8 && v < floors * FLOOR_H - 0.2;
	if (usable) {
		float hw = clamp(0.9 / bay, 0.14, 0.32);         // half width of a window, fraction of the bay
		if (tall) hw = clamp(1.3 / bay, 0.2, 0.42);
		float y0 = fl == 0.0 ? 0.9 : 0.85;
		float y1 = tall ? 2.6 : 2.25;
		bool door_bay = fl == 0.0 && idx == floor(hash(wall_id) * n) && hash(wall_id + 3.0) < 0.6;

		if (fl == 0.0 && shop) {
			// shophouse front: roller shutters or open shop
			if (fu > 0.05 && fu < 0.95 && fv < 2.7) {
				bool open = hash(wall_id + idx * 1.3) < 0.45;
				if (open) {
					col = vec3(0.04, 0.035, 0.03) + vec3(0.12, 0.08, 0.03) * smoothstep(2.7, 0.5, fv);
				} else {
					float rib = step(0.5, fract(fv * 9.0));
					col = vec3(0.42, 0.44, 0.46) * (0.85 + 0.15 * rib);
					metal = 0.4;
					rough = 0.5;
				}
			}
			// sign board above the shop
			if (fv > 2.75 && fv < 3.15 && fu > 0.02 && fu < 0.98) {
				float h = hash(wall_id + idx * 5.1);
				col = pow(mix(vec3(0.85, 0.2, 0.15), vec3(0.15, 0.35, 0.75), step(0.5, h)) * (0.7 + 0.3 * hash(h)), vec3(2.2));
			}
		} else if (door_bay) {
			// door with frame and step
			float dw = clamp(0.5 / bay, 0.12, 0.3);
			if (abs(fu - 0.5) < dw + 0.04 / bay && fv < 2.18) {
				col = vec3(0.9);
				if (abs(fu - 0.5) < dw && fv < 2.1) {
					float k = hash(seed * 3.3);
					vec3 door = k < 0.33 ? vec3(0.35, 0.18, 0.08) : (k < 0.66 ? vec3(0.08, 0.25, 0.35) : vec3(0.55, 0.08, 0.06));
					col = pow(door, vec3(2.2));
					// panels
					float px = abs(fu - 0.5) / dw;
					if (px > 0.12 && px < 0.82 && (abs(fv - 0.6) < 0.4 || abs(fv - 1.55) < 0.4)) col *= 0.75;
					if (abs(fu - 0.5 - dw * 0.7) < 0.02 && abs(fv - 1.05) < 0.06) { col = vec3(0.8, 0.65, 0.2); metal = 1.0; rough = 0.3; }
				}
			}
		} else if (abs(fu - 0.5) < hw && fv > y0 && fv < y1) {
			// window: frame, glass, mullion, optional shutters
			float fx = abs(fu - 0.5) / hw;                    // 0 centre .. 1 edge
			float fy = (fv - y0) / (y1 - y0);
			float frame_x = 0.07 / (hw * bay);
			float frame_y = 0.07 / (y1 - y0);
			bool frame = fx > 1.0 - frame_x || fy < frame_y || fy > 1.0 - frame_y || abs(fu - 0.5) < 0.025 / bay;
			float style = hash(seed * 11.0);
			vec3 frame_col = style < 0.5 ? vec3(0.92) : (style < 0.8 ? vec3(0.25, 0.15, 0.08) : vec3(0.18, 0.2, 0.22));
			if (frame) {
				col = pow(frame_col, vec3(2.2));
			} else {
				// glass with a soft sky reflection, sometimes curtains
				float refl = 0.25 + 0.35 * smoothstep(0.0, 1.0, fy) + 0.15 * hash(wall_id + idx + fl * 9.0);
				col = mix(vec3(0.02, 0.04, 0.06), vec3(0.35, 0.5, 0.62), refl * 0.5);
				if (hash(wall_id + idx * 3.0 + fl * 13.0) < 0.3 && fy > 0.55) col = pow(vec3(0.85, 0.8, 0.7), vec3(2.2)) * 0.6;
				rough = 0.08;
				metal = 0.2;
			}
			// sill
			if (fv > y0 - 0.1 && fv < y0) col = wall * 0.7;
		} else if (hash(seed * 5.0) < 0.35 && !tall && abs(fu - 0.5) < hw * 1.55 && abs(fu - 0.5) >= hw && fv > y0 && fv < y1) {
			// wooden shutters next to the window
			vec3 sh = hash(seed * 9.0) < 0.5 ? vec3(0.1, 0.32, 0.25) : vec3(0.42, 0.24, 0.12);
			col = pow(sh, vec3(2.2)) * (0.85 + 0.15 * step(0.5, fract(fv * 6.0)));
		}
		// hotel balconies: railing band below every upper-floor window
		if (tall && fl > 0.0 && fv < 1.0 && fv > 0.0 && abs(fu - 0.5) < hw + 0.05) {
			if (fv > 0.9 || fract(u * 6.0) < 0.15) col = pow(vec3(0.85), vec3(2.2));
		}
	}
	// floor slab line and eave shadow
	if (floors > 1.0 && fl > 0.0 && fv < 0.18 && v < floors * FLOOR_H) col *= 0.78;
	float top_dist = H - v;
	if (top_dist < 0.35 && top_dist > -0.01) col *= 0.6 + 0.4 * (top_dist / 0.35);
	// parapet above the roof line
	if (v > H) col = wall * 0.92;
	ALBEDO = col;
	ROUGHNESS = rough;
	METALLIC = metal;
}
