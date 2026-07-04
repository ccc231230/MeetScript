from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('username', sa.String(128), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(32), default='viewer', nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('preferred_language', sa.String(10), default='zh-CN', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Meetings table
    op.create_table(
        'meetings',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('description', sa.String(2048), nullable=True),
        sa.Column('source_language', sa.String(10), default='zh', nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('file_type', sa.String(32), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), default=0),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(32), default='uploaded', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_meetings_user_time', 'meetings', ['user_id', 'created_at'])
    op.create_index('idx_meetings_status_time', 'meetings', ['status', 'created_at'])

    # Subtitles table (with FTS)
    op.create_table(
        'subtitles',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('meeting_id', sa.UUID(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('speaker_label', sa.String(64), default='SPEAKER_00', nullable=False),
        sa.Column('language', sa.String(10), default='zh', nullable=False),
        sa.Column('start_time_ms', sa.Integer(), nullable=False),
        sa.Column('end_time_ms', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_candidate', sa.Boolean(), default=False, nullable=False),
        sa.Column('confidence', sa.Float(), default=0.0, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index('idx_subtitles_meeting_time', 'subtitles', ['meeting_id', 'start_time_ms'])
    op.create_index('idx_subtitles_meeting_speaker', 'subtitles', ['meeting_id', 'speaker_label'])

    # Full-text search column (PostgreSQL specific)
    op.execute(
        "ALTER TABLE subtitles ADD COLUMN text_search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED"
    )
    op.execute(
        "CREATE INDEX idx_subtitles_text_search ON subtitles USING GIN (text_search_vector)"
    )

    # Meeting FTS
    op.execute(
        "ALTER TABLE meetings ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(description, ''))) STORED"
    )
    op.execute(
        "CREATE INDEX idx_meetings_search ON meetings USING GIN (search_vector)"
    )

    # Meeting Tasks
    op.create_table(
        'meeting_tasks',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('meeting_id', sa.UUID(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_type', sa.String(32), nullable=False),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('priority', sa.Integer(), default=5, nullable=False),
        sa.Column('status', sa.String(32), default='pending', nullable=False),
        sa.Column('progress', sa.Integer(), default=0, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0, nullable=False),
        sa.Column('max_retries', sa.Integer(), default=3, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index('idx_tasks_meeting_type_status', 'meeting_tasks', ['meeting_id', 'task_type', 'status'])
    op.create_index('idx_tasks_status_time', 'meeting_tasks', ['status', 'created_at'])

    # Translations
    op.create_table(
        'translations',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('subtitle_id', sa.UUID(), sa.ForeignKey('subtitles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('meeting_id', sa.UUID(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_language', sa.String(10), nullable=False),
        sa.Column('translated_text', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(128), nullable=False),
        sa.Column('token_count_input', sa.Integer(), default=0),
        sa.Column('token_count_output', sa.Integer(), default=0),
        sa.Column('cost', sa.Float(), default=0.0),
        sa.Column('translation_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index('idx_translations_subtitle_lang', 'translations', ['subtitle_id', 'target_language'])
    op.create_index('idx_translations_hash_lang', 'translations', ['translation_hash', 'target_language'])

    # Model Configs
    op.create_table(
        'model_configs',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('model_type', sa.String(32), nullable=False),
        sa.Column('provider', sa.String(64), nullable=False),
        sa.Column('model_name', sa.String(128), nullable=False),
        sa.Column('api_key_encrypted', sa.String(512), nullable=False),
        sa.Column('endpoint_url', sa.String(512), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_model_type_active', 'model_configs', ['model_type', 'is_active'])

    # Token Usages
    op.create_table(
        'token_usages',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('meeting_id', sa.UUID(), sa.ForeignKey('meetings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('model_config_id', sa.UUID(), sa.ForeignKey('model_configs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('operation_type', sa.String(32), nullable=False),
        sa.Column('tokens_input', sa.Integer(), default=0),
        sa.Column('tokens_output', sa.Integer(), default=0),
        sa.Column('tokens_total', sa.Integer(), default=0),
        sa.Column('cost', sa.Float(), default=0.0),
        sa.Column('request_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index('idx_token_usage_user_time', 'token_usages', ['user_id', 'created_at'])

    # API Keys
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key_name', sa.String(128), nullable=False),
        sa.Column('api_key_hash', sa.String(128), unique=True, nullable=False),
        sa.Column('prefix', sa.String(8), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('rate_limit', sa.Integer(), default=100),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )

    # Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(128), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=True),
        sa.Column('resource_id', sa.String(64), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index('idx_audit_logs_user_action_time', 'audit_logs', ['user_id', 'action', 'created_at'])
    op.create_index('idx_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
    op.drop_table('token_usages')
    op.drop_table('model_configs')
    op.drop_table('translations')
    op.drop_table('meeting_tasks')
    op.drop_table('subtitles')
    op.drop_table('meetings')
    op.drop_table('users')
