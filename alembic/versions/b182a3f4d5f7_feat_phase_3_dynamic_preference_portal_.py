"""feat: phase 3 dynamic preference portal with session routing

Revision ID: b182a3f4d5f7
Revises: 246151f2ec37
Create Date: 2026-09-03 02:04:34.213406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b182a3f4d5f7'
down_revision: Union[str, Sequence[str], None] = '246151f2ec37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
