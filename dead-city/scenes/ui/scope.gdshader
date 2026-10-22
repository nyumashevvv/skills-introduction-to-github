shader_type canvas_item;
// Black outside a round eyepiece, with a soft dark rim.

uniform float radius = 0.42;

void fragment() {
	vec2 size = 1.0 / SCREEN_PIXEL_SIZE;
	vec2 p = (UV - 0.5) * vec2(size.x / size.y, 1.0);
	float d = length(p);
	float a = smoothstep(radius - 0.01, radius + 0.004, d);
	float rim = smoothstep(radius - 0.12, radius, d) * 0.6;
	COLOR = vec4(0.0, 0.0, 0.0, max(a, rim));
}
