"""feat: phase 4 complete allocation matrix and reportlab pdf engine

Revision ID: 8fd468c9e0d8
Revises: b182a3f4d5f7
Create Date: 2026-09-03 02:21:55.436145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8fd468c9e0d8'
down_revision: Union[str, Sequence[str], None] = 'b182a3f4d5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
