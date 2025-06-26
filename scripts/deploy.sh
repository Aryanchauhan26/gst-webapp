#!/bin/bash
# =============================================================================
# GST Intelligence Platform - Deployment Script
# Automated deployment for different environments
# =============================================================================

set -e  # Exit on any error

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="production"
SKIP_TESTS=false
SKIP_BACKUP=false
FORCE_DEPLOY=false
VERBOSE=false

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy GST Intelligence Platform to specified environment.

OPTIONS:
    -e, --environment ENV    Target environment (development, staging, production)
    -t, --skip-tests        Skip running tests before deployment
    -b, --skip-backup       Skip database backup before deployment
    -f, --force             Force deployment even if checks fail
    -v, --verbose           Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0 -e production                 # Deploy to production with all checks
    $0 -e staging --skip-tests       # Deploy to staging without tests
    $0 -e development --force        # Force deploy to development

EOF
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Check if environment file exists
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        warning "No .env file found. Creating from template..."
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        warning "Please configure .env file with your settings"
    fi
    
    success "Prerequisites check passed"
}

run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        warning "Skipping tests as requested"
        return
    fi
    
    log "Running tests..."
    
    cd "$PROJECT_DIR"
    
    # Build test image
    docker build --target testing -t gst-intelligence:test . || error "Failed to build test image"
    
    # Run tests
    docker run --rm \
        -v "$PROJECT_DIR:/app" \
        -e ENVIRONMENT=testing \
        gst-intelligence:test || error "Tests failed"
    
    success "All tests passed"
}

backup_database() {
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        warning "Skipping database backup as requested"
        return
    fi
    
    if [[ "$ENVIRONMENT" == "development" ]]; then
        warning "Skipping backup for development environment"
        return
    fi
    
    log "Creating database backup..."
    
    # Create backup directory
    BACKUP_DIR="$PROJECT_DIR/backups/$(date +'%Y%m%d_%H%M%S')"
    mkdir -p "$BACKUP_DIR"
    
    # Run backup script
    docker-compose exec -T postgres pg_dump -U gstuser gstintelligence > "$BACKUP_DIR/database_backup.sql" || warning "Database backup failed"
    
    # Compress backup
    gzip "$BACKUP_DIR/database_backup.sql" || warning "Failed to compress backup"
    
    success "Database backup created: $BACKUP_DIR"
}

build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_DIR"
    
    # Set build arguments
    BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    VERSION=$(grep "VERSION=" .env | cut -d'=' -f2 | tr -d '"' || echo "2.0.0")
    
    # Build production image
    docker build \
        --target production \
        --build-arg VERSION="$VERSION" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg ENVIRONMENT="$ENVIRONMENT" \
        -t gst-intelligence:latest \
        -t "gst-intelligence:$VERSION" \
        . || error "Failed to build production image"
    
    success "Docker images built successfully"
}

deploy_application() {
    log "Deploying application to $ENVIRONMENT environment..."
    
    cd "$PROJECT_DIR"
    
    # Set environment variables
    export ENVIRONMENT="$ENVIRONMENT"
    export BUILD_TARGET="production"
    
    # Choose the right compose file based on environment
    COMPOSE_FILES="-f docker-compose.yml"
    
    case "$ENVIRONMENT" in
        "production")
            COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.prod.yml"
            ;;
        "staging")
            COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.staging.yml"
            ;;
        "development")
            COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.dev.yml"
            ;;
    esac
    
    # Stop existing services
    log "Stopping existing services..."
    docker-compose $COMPOSE_FILES down || warning "No existing services to stop"
    
    # Start services
    log "Starting services..."
    docker-compose $COMPOSE_FILES up -d || error "Failed to start services"
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    sleep 10
    
    # Check health
    check_deployment_health
    
    success "Application deployed successfully"
}

run_migrations() {
    log "Running database migrations..."
    
    cd "$PROJECT_DIR"
    
    # Run migrations
    docker-compose run --rm app python init_database.py || error "Database migration failed"
    
    success "Database migrations completed"
}

check_deployment_health() {
    log "Checking deployment health..."
    
    # Wait for application to start
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            success "Application is healthy"
            return
        fi
        
        log "Attempt $attempt/$max_attempts: Waiting for application..."
        sleep 5
        ((attempt++))
    done
    
    error "Application health check failed after $max_attempts attempts"
}

cleanup_old_images() {
    log "Cleaning up old Docker images..."
    
    # Remove dangling images
    docker image prune -f || warning "Failed to prune images"
    
    # Remove old versions (keep last 3)
    docker images gst-intelligence --format "table {{.Tag}}\t{{.ID}}" | grep -v "latest" | tail -n +4 | awk '{print $2}' | xargs -r docker rmi || warning "Failed to remove old images"
    
    success "Docker cleanup completed"
}

post_deployment_tasks() {
    log "Running post-deployment tasks..."
    
    # Send deployment notification (if configured)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚀 GST Intelligence Platform deployed to $ENVIRONMENT\"}" \
            "$SLACK_WEBHOOK_URL" || warning "Failed to send Slack notification"
    fi
    
    # Update deployment timestamp
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" > "$PROJECT_DIR/.last_deployment"
    
    success "Post-deployment tasks completed"
}

rollback() {
    log "Rolling back deployment..."
    
    cd "$PROJECT_DIR"
    
    # Stop current services
    docker-compose down
    
    # Restore from backup if available
    LATEST_BACKUP=$(find "$PROJECT_DIR/backups" -name "*.sql.gz" | sort -r | head -1)
    
    if [[ -n "$LATEST_BACKUP" ]]; then
        log "Restoring database from backup: $LATEST_BACKUP"
        zcat "$LATEST_BACKUP" | docker-compose exec -T postgres psql -U gstuser gstintelligence || warning "Database restore failed"
    fi
    
    # Start services with previous version
    docker-compose up -d
    
    success "Rollback completed"
}

# =============================================================================
# MAIN DEPLOYMENT PROCESS
# =============================================================================

main() {
    log "Starting deployment process..."
    log "Environment: $ENVIRONMENT"
    log "Skip tests: $SKIP_TESTS"
    log "Skip backup: $SKIP_BACKUP"
    log "Force deploy: $FORCE_DEPLOY"
    
    # Pre-deployment checks
    check_prerequisites
    
    # Run tests
    run_tests
    
    # Create backup
    backup_database
    
    # Build images
    build_images
    
    # Run migrations
    run_migrations
    
    # Deploy application
    deploy_application
    
    # Cleanup
    cleanup_old_images
    
    # Post-deployment tasks
    post_deployment_tasks
    
    success "Deployment completed successfully! 🎉"
    log "Application is running at: http://localhost:8000"
    log "Check logs with: docker-compose logs -f"
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -b|--skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        -f|--force)
            FORCE_DEPLOY=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            set -x
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --rollback)
            rollback
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Validate environment
case "$ENVIRONMENT" in
    "development"|"staging"|"production")
        ;;
    *)
        error "Invalid environment: $ENVIRONMENT. Must be development, staging, or production"
        ;;
esac

# Create log file
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Run main deployment
main

# =============================================================================
# ADDITIONAL SCRIPTS
# =============================================================================

# Create additional utility scripts
cat > "$SCRIPT_DIR/quick-deploy.sh" << 'EOF'
#!/bin/bash
# Quick deployment script for development
set -e

cd "$(dirname "$0")/.."

echo "🚀 Quick deployment to development..."

# Build and start
docker-compose build app
docker-compose up -d

echo "✅ Development deployment complete!"
echo "Application: http://localhost:8000"
echo "Logs: docker-compose logs -f app"
EOF

cat > "$SCRIPT_DIR/health-check.sh" << 'EOF'
#!/bin/bash
# Health check script

curl -sf http://localhost:8000/health || {
    echo "❌ Health check failed"
    exit 1
}

echo "✅ Application is healthy"
EOF

cat > "$SCRIPT_DIR/backup.sh" << 'EOF'
#!/bin/bash
# Database backup script

BACKUP_DIR="/backups/$(date +'%Y%m%d_%H%M%S')"
mkdir -p "$BACKUP_DIR"

pg_dump -h postgres -U gstuser gstintelligence | gzip > "$BACKUP_DIR/backup.sql.gz"

echo "✅ Backup created: $BACKUP_DIR/backup.sql.gz"
EOF

# Make scripts executable
chmod +x "$SCRIPT_DIR"/*.sh

log "Deployment script setup complete!"
log "Run with: ./scripts/deploy.sh -e production"