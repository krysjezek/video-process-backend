from .perspective_transformations import *
from .blending_effects import *
from .blur_effect import gauss_blur_effect
from .screen_glow import screen_glow_effect

EFFECT_REGISTRY = {
    "corner_pin": corner_pin_effect,
    "reflections": reflections_effect,
    "gauss_blur": gauss_blur_effect,
    "screen_glow": screen_glow_effect,
}
