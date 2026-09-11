"""Import every ORM model so that ``Base.metadata`` is complete.

Alembic's ``env.py`` and the test suite import this module; application code imports
models from their own modules.
"""

from nemeth.core.db import Base
from nemeth.core.identifiers import IdentifierCounter
from nemeth.modules.bom.models import BomLine
from nemeth.modules.components.models import Component, ComponentRevision
from nemeth.modules.experiments.models import Experiment, ExperimentPrototype, ExperimentRevision
from nemeth.modules.products.models import Caliber, Product, ProductModel
from nemeth.modules.prototypes.models import BuildEntry, BuildRecord, PartInstance, Prototype

__all__ = [
    "Base",
    "BomLine",
    "BuildEntry",
    "BuildRecord",
    "Caliber",
    "Component",
    "ComponentRevision",
    "Experiment",
    "ExperimentPrototype",
    "ExperimentRevision",
    "IdentifierCounter",
    "PartInstance",
    "Product",
    "ProductModel",
    "Prototype",
]
