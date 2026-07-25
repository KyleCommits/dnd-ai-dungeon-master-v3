"""initial schema including campaign_world_state

Revision ID: 001_initial
Revises:
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all ORM tables from metadata (fresh local / wiped DB)."""
    from src.models import Base
    import src.character_models  # noqa: F401
    import src.animal_companion_models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    # Ensure additive columns exist on older partial installs
    op.execute("ALTER TABLE characters ADD COLUMN IF NOT EXISTS spell_slots_used TEXT DEFAULT '{}'")
    op.execute("ALTER TABLE characters ADD COLUMN IF NOT EXISTS conditions_json TEXT DEFAULT '[]'")


def downgrade() -> None:
    from src.models import Base
    import src.character_models  # noqa: F401
    import src.animal_companion_models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
