#!/bin/bash

# Production startup script for Blog Content Generator API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Configuration
APP_NAME="blog-content-generator"
APP_DIR="/app"
LOG_DIR="/var/log/app"
PID_FILE="/var/run/app.pid"
CONFIG_FILE="/app/config/production.py"

# Create necessary directories
log "Creating necessary directories..."
mkdir -p "$LOG_DIR"
mkdir -p "/var/run"
mkdir -p "/tmp/profiling"

# Check if required environment variables are set
log "Checking environment variables..."
required_vars=("SECRET_KEY" "DEEPSEEK_API_KEY" "STABILITY_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        error "Required environment variable $var is not set"
        exit 1
    fi
done

# Set optional environment variables with defaults
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-"8000"}
export WORKERS=${WORKERS:-"4"}

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        error "Port $port is already in use"
        exit 1
    fi
}

# Function to check disk space
check_disk_space() {
    local required_space=1024  # 1GB in MB
    local available_space=$(df -m / | awk 'NR==2 {print $4}')
    
    if [ "$available_space" -lt "$required_space" ]; then
        warn "Low disk space: ${available_space}MB available, ${required_space}MB required"
    fi
}

# Function to check memory
check_memory() {
    local required_memory=512  # 512MB in MB
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    
    if [ "$available_memory" -lt "$required_memory" ]; then
        warn "Low memory: ${available_memory}MB available, ${required_memory}MB required"
    fi
}

# Function to start the application
start_app() {
    log "Starting $APP_NAME..."
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            error "Application is already running with PID $pid"
            exit 1
        else
            warn "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi
    
    # Check port availability
    check_port "$PORT"
    
    # Check system resources
    check_disk_space
    check_memory
    
    # Start the application with uvicorn
    log "Starting uvicorn server on $HOST:$PORT with $WORKERS workers..."
    
    cd "$APP_DIR"
    
    exec uvicorn app.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level "$LOG_LEVEL" \
        --access-log \
        --log-config /app/logging_config.py \
        --timeout-keep-alive 30 \
        --limit-concurrency 100 \
        --limit-max-requests 1000 \
        --backlog 2048 \
        --server-header \
        --date-header
}

# Function to stop the application
stop_app() {
    log "Stopping $APP_NAME..."
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid"
            log "Sent SIGTERM to PID $pid"
            
            # Wait for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt 30 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            if kill -0 "$pid" 2>/dev/null; then
                warn "Force killing process $pid"
                kill -KILL "$pid"
            fi
            
            rm -f "$PID_FILE"
            log "Application stopped"
        else
            warn "Process $pid not found"
            rm -f "$PID_FILE"
        fi
    else
        warn "PID file not found"
    fi
}

# Function to restart the application
restart_app() {
    log "Restarting $APP_NAME..."
    stop_app
    sleep 2
    start_app
}

# Function to check application status
status_app() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Application is running with PID $pid"
            
            # Check if application is responding
            if curl -f -s "http://$HOST:$PORT/health" >/dev/null 2>&1; then
                log "Application is healthy"
            else
                warn "Application is running but not responding to health checks"
            fi
        else
            error "Application is not running (stale PID file)"
            rm -f "$PID_FILE"
        fi
    else
        error "Application is not running"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_DIR/app.log" ]; then
        tail -f "$LOG_DIR/app.log"
    else
        error "Log file not found: $LOG_DIR/app.log"
    fi
}

# Function to run health check
health_check() {
    log "Running health check..."
    
    local health_url="http://$HOST:$PORT/health"
    local response=$(curl -s -w "%{http_code}" "$health_url" -o /tmp/health_response)
    
    if [ "$response" = "200" ]; then
        log "Health check passed"
        cat /tmp/health_response | jq '.' 2>/dev/null || cat /tmp/health_response
    else
        error "Health check failed with status $response"
        cat /tmp/health_response
    fi
    
    rm -f /tmp/health_response
}

# Function to show metrics
show_metrics() {
    log "Fetching metrics..."
    
    local metrics_url="http://$HOST:$PORT/metrics"
    local response=$(curl -s -w "%{http_code}" "$metrics_url" -o /tmp/metrics_response)
    
    if [ "$response" = "200" ]; then
        cat /tmp/metrics_response | jq '.' 2>/dev/null || cat /tmp/metrics_response
    else
        error "Failed to fetch metrics with status $response"
        cat /tmp/metrics_response
    fi
    
    rm -f /tmp/metrics_response
}

# Function to show help
show_help() {
    echo "Usage: $0 {start|stop|restart|status|logs|health|metrics|help}"
    echo ""
    echo "Commands:"
    echo "  start   - Start the application"
    echo "  stop    - Stop the application"
    echo "  restart - Restart the application"
    echo "  status  - Show application status"
    echo "  logs    - Show application logs"
    echo "  health  - Run health check"
    echo "  metrics - Show application metrics"
    echo "  help    - Show this help message"
}

# Main script logic
case "$1" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    status)
        status_app
        ;;
    logs)
        show_logs
        ;;
    health)
        health_check
        ;;
    metrics)
        show_metrics
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
