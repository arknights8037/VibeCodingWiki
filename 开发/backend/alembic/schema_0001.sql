
CREATE TABLE IF NOT EXISTS categories (
	id INTEGER NOT NULL, 
	slug VARCHAR(80) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	parent_id INTEGER, 
	order_index INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(parent_id) REFERENCES categories (id) ON DELETE SET NULL
)

;
CREATE INDEX IF NOT EXISTS ix_categories_order_index ON categories (order_index);
CREATE INDEX IF NOT EXISTS ix_categories_parent_id ON categories (parent_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_categories_slug ON categories (slug);

CREATE TABLE IF NOT EXISTS courses (
	id INTEGER NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	summary TEXT NOT NULL, 
	prerequisites TEXT NOT NULL, 
	difficulty VARCHAR(12) NOT NULL, 
	order_index INTEGER NOT NULL, 
	status VARCHAR(14) NOT NULL, 
	is_standalone BOOLEAN DEFAULT '0' NOT NULL, 
	directory_collapsible BOOLEAN DEFAULT '1' NOT NULL, 
	PRIMARY KEY (id)
)

;
CREATE INDEX IF NOT EXISTS ix_courses_order_index ON courses (order_index);
CREATE UNIQUE INDEX IF NOT EXISTS ix_courses_slug ON courses (slug);

CREATE TABLE IF NOT EXISTS mcp_settings (
	id INTEGER NOT NULL, 
	enabled BOOLEAN DEFAULT '1' NOT NULL, 
	auth_enabled BOOLEAN DEFAULT '0' NOT NULL, 
	auth_token_hash VARCHAR(128), 
	github_client_id VARCHAR(200), 
	github_client_secret VARCHAR(300), 
	gitee_client_id VARCHAR(200), 
	gitee_client_secret VARCHAR(300), 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE IF NOT EXISTS mcp_tool_settings (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT NOT NULL, 
	enabled BOOLEAN DEFAULT '1' NOT NULL, 
	PRIMARY KEY (id)
)

;
CREATE UNIQUE INDEX IF NOT EXISTS ix_mcp_tool_settings_name ON mcp_tool_settings (name);

CREATE TABLE IF NOT EXISTS skill_packages (
	id INTEGER NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	summary TEXT NOT NULL, 
	version VARCHAR(40) NOT NULL, 
	license_name VARCHAR(100), 
	compatibility VARCHAR(500), 
	skill_md TEXT NOT NULL, 
	files_json TEXT NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	status VARCHAR(14) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug, version)
)

;
CREATE INDEX IF NOT EXISTS ix_skill_packages_slug ON skill_packages (slug);
CREATE INDEX IF NOT EXISTS ix_skill_packages_status ON skill_packages (status);

CREATE TABLE IF NOT EXISTS tags (
	id INTEGER NOT NULL, 
	slug VARCHAR(80) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;
CREATE UNIQUE INDEX IF NOT EXISTS ix_tags_slug ON tags (slug);

CREATE TABLE IF NOT EXISTS users (
	id INTEGER NOT NULL, 
	email VARCHAR(320) NOT NULL, 
	display_name VARCHAR(80) NOT NULL, 
	real_name VARCHAR(80), 
	avatar_url VARCHAR(500), 
	mcp_token_hash VARCHAR(128), 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(8) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	github_username VARCHAR(120), 
	gitee_username VARCHAR(120), 
	PRIMARY KEY (id)
)

;
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);

CREATE TABLE IF NOT EXISTS audit_logs (
	id INTEGER NOT NULL, 
	actor_id INTEGER, 
	action VARCHAR(100) NOT NULL, 
	target_type VARCHAR(60) NOT NULL, 
	target_id VARCHAR(100) NOT NULL, 
	detail TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs (actor_id);

CREATE TABLE IF NOT EXISTS lessons (
	id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	objective TEXT NOT NULL, 
	body_markdown TEXT NOT NULL, 
	practice TEXT NOT NULL, 
	completion_criteria TEXT NOT NULL, 
	estimated_minutes INTEGER NOT NULL, 
	order_index INTEGER NOT NULL, 
	status VARCHAR(14) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (course_id, slug), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_lessons_course_id ON lessons (course_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_lessons_slug ON lessons (slug);

CREATE TABLE IF NOT EXISTS project_submissions (
	id INTEGER NOT NULL, 
	owner_id INTEGER NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	summary TEXT NOT NULL, 
	description_markdown TEXT NOT NULL, 
	repository_url VARCHAR(500) NOT NULL, 
	demo_url VARCHAR(500), 
	license_name VARCHAR(80) NOT NULL, 
	tech_stack TEXT NOT NULL, 
	status VARCHAR(14) NOT NULL, 
	is_featured BOOLEAN NOT NULL, 
	review_note TEXT, 
	submitted_at DATETIME, 
	published_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_project_submissions_is_featured ON project_submissions (is_featured);
CREATE INDEX IF NOT EXISTS ix_project_submissions_owner_id ON project_submissions (owner_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_project_submissions_slug ON project_submissions (slug);
CREATE INDEX IF NOT EXISTS ix_project_submissions_status ON project_submissions (status);

CREATE TABLE IF NOT EXISTS refresh_tokens (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	revoked_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;
CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens (token_hash);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);

CREATE TABLE IF NOT EXISTS review_events (
	id INTEGER NOT NULL, 
	entity_type VARCHAR(40) NOT NULL, 
	entity_id INTEGER NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	reviewer_id INTEGER NOT NULL, 
	comment TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reviewer_id) REFERENCES users (id)
)

;
CREATE INDEX IF NOT EXISTS ix_review_events_entity_id ON review_events (entity_id);
CREATE INDEX IF NOT EXISTS ix_review_events_entity_type ON review_events (entity_type);
CREATE INDEX IF NOT EXISTS ix_review_events_reviewer_id ON review_events (reviewer_id);

CREATE TABLE IF NOT EXISTS wiki_articles (
	id INTEGER NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	summary TEXT NOT NULL, 
	body_markdown TEXT NOT NULL, 
	difficulty VARCHAR(12) NOT NULL, 
	category_id INTEGER NOT NULL, 
	order_index INTEGER NOT NULL, 
	status VARCHAR(14) NOT NULL, 
	version INTEGER NOT NULL, 
	updated_at DATETIME NOT NULL, 
	published_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id)
)

;
CREATE INDEX IF NOT EXISTS ix_wiki_articles_category_id ON wiki_articles (category_id);
CREATE INDEX IF NOT EXISTS ix_wiki_articles_difficulty ON wiki_articles (difficulty);
CREATE INDEX IF NOT EXISTS ix_wiki_articles_order_index ON wiki_articles (order_index);
CREATE UNIQUE INDEX IF NOT EXISTS ix_wiki_articles_slug ON wiki_articles (slug);
CREATE INDEX IF NOT EXISTS ix_wiki_articles_status ON wiki_articles (status);
CREATE INDEX IF NOT EXISTS ix_wiki_articles_title ON wiki_articles (title);

CREATE TABLE IF NOT EXISTS article_tags (
	article_id INTEGER NOT NULL, 
	tag_id INTEGER NOT NULL, 
	PRIMARY KEY (article_id, tag_id), 
	FOREIGN KEY(article_id) REFERENCES wiki_articles (id) ON DELETE CASCADE, 
	FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE CASCADE
)

;

CREATE TABLE IF NOT EXISTS lesson_progress (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	lesson_id INTEGER NOT NULL, 
	completed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, lesson_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_lesson_progress_lesson_id ON lesson_progress (lesson_id);
CREATE INDEX IF NOT EXISTS ix_lesson_progress_user_id ON lesson_progress (user_id);
