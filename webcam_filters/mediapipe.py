from enum import Enum, unique


@unique
class SelfieSegmentationModel(int, Enum):
    general = 0
    landscape = 1
