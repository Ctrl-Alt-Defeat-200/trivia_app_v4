"""empty message

Revision ID: dcf072edb71f
Revises: a63e74524a0c
Create Date: 2023-10-10 20:32:51.489772

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcf072edb71f'
down_revision = 'a63e74524a0c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
   with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.execute("UPDATE user SET is_active = true")
        batch_op.alter_column('is_active', nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('is_active',
            existing_type=sa.BOOLEAN(),
            nullable=True)

    # ### end Alembic commands ###