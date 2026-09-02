"""feat: phase 2 dynamic syllabus and siloed ghost data sync

Revision ID: 246151f2ec37
Revises: f74e0a47f3b6
Create Date: 2026-09-03 01:51:22.440663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '246151f2ec37'
down_revision: Union[str, Sequence[str], None] = 'f74e0a47f3b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
