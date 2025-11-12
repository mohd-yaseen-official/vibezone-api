from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'bc3e17126050'
down_revision = '5f4e61f676f8'
branch_labels = None
depends_on = None

# define enum once for reuse
subscription_status_enum = sa.Enum(
    'created', 'incomplete', 'incomplete_expired', 'trialing', 'active',
    'past_due', 'canceled', 'unpaid',
    name='subscriptionstatus'
)

def upgrade() -> None:
    # Create ENUM type
    subscription_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Alter goals column
    op.alter_column(
        'goals', 'celery_task_ids',
        existing_type=sa.VARCHAR(),
        type_=sa.Text(),
        existing_nullable=True
    )
    
    # Alter stripe_subscriptions.status with USING cast
    op.alter_column(
        'stripe_subscriptions',
        'status',
        existing_type=sa.VARCHAR(length=50),
        type_=subscription_status_enum,
        postgresql_using="status::subscriptionstatus",
        existing_nullable=False
    )
    
    # Create index
    op.create_index(
        op.f('ix_tasks_status'), 'tasks', ['status'], unique=False
    )
    
    # Add column
    op.add_column(
    'users',
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.sql.expression.true())
)




def downgrade() -> None:
    # Revert users table
    op.drop_column('users', 'is_active')
    
    # Drop index
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    
    # Revert stripe_subscriptions.status column
    op.alter_column(
        'stripe_subscriptions', 'status',
        existing_type=subscription_status_enum,
        type_=sa.VARCHAR(length=50),
        existing_nullable=False
    )
    
    # Revert goals column
    op.alter_column(
        'goals', 'celery_task_ids',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(),
        existing_nullable=True
    )
    
    # Drop the enum t
