-- Research Copilot Database Initialization

-- Create database if it doesn't exist
-- Note: This is handled by docker-compose environment variables

-- Create extensions

CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create research_papers table
CREATE TABLE IF NOT EXISTS research_papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    abstract TEXT,
    authors TEXT[],
    publication_date DATE,
    doi VARCHAR(255) UNIQUE,
    arxiv_id VARCHAR(255) UNIQUE,
    pdf_url VARCHAR(500),
    full_text TEXT,
    categories TEXT[],
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

-- Create search_queries table
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'text',
    results_count INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user_sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    domain VARCHAR(255) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    max_users INTEGER DEFAULT 100,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    settings JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user_roles association table
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Create role_permissions association table
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    permissions TEXT[] DEFAULT '{}',
    rate_limit INTEGER DEFAULT 1000,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID REFERENCES users(id),
    username VARCHAR(100),
    user_email VARCHAR(255),
    organization_id UUID REFERENCES organizations(id),
    ip_address INET,
    user_agent TEXT,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    method VARCHAR(10),
    endpoint VARCHAR(500),
    status_code INTEGER,
    request_data JSON,
    response_data JSON,
    metadata JSON,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    compliance_level VARCHAR(20) DEFAULT 'standard',
    retention_days INTEGER DEFAULT 365,
    correlation_id UUID,
    session_id UUID
);

-- Create refresh_tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_reason VARCHAR(255),
    device_info VARCHAR(500),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_research_papers_title ON research_papers USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_research_papers_abstract ON research_papers USING GIN (abstract gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_research_papers_authors ON research_papers USING GIN (authors);
CREATE INDEX IF NOT EXISTS idx_research_papers_categories ON research_papers USING GIN (categories);
CREATE INDEX IF NOT EXISTS idx_research_papers_tags ON research_papers USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_research_papers_created_at ON research_papers (created_at);
CREATE INDEX IF NOT EXISTS idx_search_queries_user_id ON search_queries (user_id);
CREATE INDEX IF NOT EXISTS idx_search_queries_created_at ON search_queries (created_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions (session_token);
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations (name);
CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations (domain);
CREATE INDEX IF NOT EXISTS idx_permissions_resource_action ON permissions (resource, action);
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles (name);
CREATE INDEX IF NOT EXISTS idx_roles_organization_id ON roles (organization_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_organization_id ON api_keys (organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_organization_id ON audit_logs (organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs (resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_correlation_id ON audit_logs (correlation_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens (expires_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_research_papers_updated_at BEFORE UPDATE ON research_papers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permissions_updated_at BEFORE UPDATE ON permissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default permissions
INSERT INTO permissions (name, description, resource, action) VALUES
('papers.read', 'Read research papers', 'papers', 'read'),
('papers.write', 'Create and modify research papers', 'papers', 'write'),
('papers.delete', 'Delete research papers', 'papers', 'delete'),
('papers.admin', 'Full administration of research papers', 'papers', 'admin'),
('search.read', 'Perform searches', 'search', 'read'),
('search.admin', 'Administer search functionality', 'search', 'admin'),
('users.read', 'View user information', 'users', 'read'),
('users.write', 'Create and modify users', 'users', 'write'),
('users.delete', 'Delete users', 'users', 'delete'),
('users.admin', 'Full user administration', 'users', 'admin'),
('organizations.read', 'View organizations', 'organizations', 'read'),
('organizations.write', 'Create and modify organizations', 'organizations', 'write'),
('organizations.admin', 'Full organization administration', 'organizations', 'admin'),
('analytics.read', 'View analytics and reports', 'analytics', 'read'),
('analytics.admin', 'Full analytics administration', 'analytics', 'admin'),
('admin.system', 'System administration access', 'admin', 'system')
ON CONFLICT (name) DO NOTHING;

-- Insert default roles
INSERT INTO roles (name, description, is_default, is_system) VALUES
('user', 'Basic user role with read access', TRUE, TRUE),
('researcher', 'Researcher role with paper and search access', FALSE, TRUE),
('admin', 'Administrator role with elevated permissions', FALSE, TRUE),
('superuser', 'Superuser with full system access', FALSE, TRUE)
ON CONFLICT (name) DO NOTHING;

-- Assign permissions to roles
-- User role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'user' AND p.name IN ('papers.read', 'search.read')
ON CONFLICT DO NOTHING;

-- Researcher role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'researcher' AND p.name IN ('papers.read', 'papers.write', 'search.read', 'search.admin')
ON CONFLICT DO NOTHING;

-- Admin role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'admin' AND p.name IN ('papers.read', 'papers.write', 'papers.delete', 'papers.admin', 'search.read', 'search.admin', 'users.read', 'users.write', 'analytics.read', 'analytics.admin')
ON CONFLICT DO NOTHING;

-- Superuser role permissions (all permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'superuser'
ON CONFLICT DO NOTHING;

-- Insert default organization
INSERT INTO organizations (name, description, domain, subscription_tier) VALUES
('Default Organization', 'Default organization for single-tenant setup', NULL, 'enterprise')
ON CONFLICT (name) DO NOTHING;

-- Insert default admin user (password: admin123)
-- Note: In production, use proper password hashing
INSERT INTO users (email, username, hashed_password, full_name, is_superuser, organization_id)
SELECT
    'admin@researchcopilot.com',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6fM9q7F8K2', -- bcrypt hash for 'admin123'
    'System Administrator',
    TRUE,
    o.id
FROM organizations o WHERE o.name = 'Default Organization'
ON CONFLICT (email) DO NOTHING;

-- Assign superuser role to admin user
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username = 'admin' AND r.name = 'superuser'
ON CONFLICT DO NOTHING;