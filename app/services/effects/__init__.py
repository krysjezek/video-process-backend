from .perspective_transformations import *
from .blending_effects import *
from .blur_effect import gauss_blur_effect

EFFECT_REGISTRY = {
    "corner_pin": corner_pin_effect,
    "reflections": reflections_effect,
    "gauss_blur": gauss_blur_effect,
}
