"""feat: phase 1 workspace enums and smtp pipeline

Revision ID: f74e0a47f3b6
Revises: 00002efa29ff
Create Date: 2026-09-03 01:35:14.645778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f74e0a47f3b6'
down_revision: Union[str, Sequence[str], None] = '00002efa29ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
