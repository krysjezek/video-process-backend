from .perspective_transformations import *
from .blending_effects import *

EFFECT_REGISTRY = {
    "corner_pin": corner_pin_effect,
    "reflections": reflections_effect,
}
