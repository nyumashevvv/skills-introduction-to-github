shader_type canvas_item;

uniform float intensity : hint_range(0.0, 1.0) = 0.0;
uniform vec4 tint : source_color = vec4(0.75, 0.0, 0.0, 1.0);

void fragment() {
	float d = distance(UV, vec2(0.5));
	COLOR = vec4(tint.rgb, smoothstep(0.2, 0.75, d) * intensity);
}
