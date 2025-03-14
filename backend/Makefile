.PHONY: help db-start db-stop db-clear db-backup db-restore db-create \
        migrations migrate superuser run run-dev shell \
        test test-coverage \
        collectstatic setup db-wait env-setup db-settings

# Color configuration
# Set NO_COLOR=1 to disable all colors
INTERACTIVE := $(shell [ -t 0 ] && echo 1 || echo 0)
NO_COLOR ?= 1

ifeq ($(or $(filter 1,$(NO_COLOR)),$(filter 0,$(INTERACTIVE))),1)
    RED := 
    GREEN := 
    YELLOW := 
    NC := 
else
    RED := \033[0;31m
    GREEN := \033[0;32m
    YELLOW := \033[0;33m
    NC := \033[0m
endif

PYTHON = python3
MANAGE = $(PYTHON) manage.py
PIP = $(PYTHON) -m pip

DOCKER_COMPOSE = docker compose
MAX_RETRIES = 10
RETRY_INTERVAL = 5

help:
	@echo "$(GREEN)Django Auction House Development Commands:$(NC)"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@echo "  make db-settings  - Interactive database management menu"
	@echo "  make db-start     - Start PostgreSQL database container"
	@echo "  make db-stop      - Stop PostgreSQL database container"
	@echo "  make db-create    - Create database if it doesn't exist"
	@echo "  make db-clear     - Clear all database data (WARNING: destructive)"
	@echo "  make db-backup    - Backup the database to a file"
	@echo "  make db-restore   - Restore database from backup file"
	@echo "  make db-wait      - Wait for database to be ready"
	@echo ""
	@echo "$(YELLOW)Django:$(NC)"
	@echo "  make migrations  - Create database migrations"
	@echo "  make migrate     - Apply database migrations"
	@echo "  make superuser   - Create a Django superuser"
	@echo "  make run         - Run the Django development server"
	@echo "  make run-dev     - Run server with debug toolbar"
	@echo "  make shell       - Open Django shell"
	@echo "  make collectstatic - Collect static files"
	@echo ""
	@echo "$(YELLOW)Testing & Quality:$(NC)"
	@echo "  make test        - Run tests"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo ""
	@echo "$(YELLOW)Workflow:$(NC)"
	@echo "  make setup       - Initial setup (db, env, migrations, superuser)"
	@echo "  make update      - Update dependencies"
	@echo "  make env-setup   - Initialize environment files"

db-settings:
	@clear
	@echo "$(GREEN)Database Management Settings$(NC)"
	@echo "--------------------------"
	@echo "$(YELLOW)Please select an option:$(NC)"
	@echo "1) Start database"
	@echo "2) Stop database"
	@echo "3) Create database"
	@echo "4) Clear database (WARNING: destructive)"
	@echo "5) Backup database"
	@echo "6) Restore database from backup"
	@echo "7) Wait for database to be ready"
	@echo "8) Return to main menu"
	@echo ""
	@read -p "Enter your choice [1-8]: " choice; \
	case $$choice in \
		1) \
			$(MAKE) db-start; \
			;; \
		2) \
			$(MAKE) db-stop; \
			;; \
		3) \
			$(MAKE) db-create; \
			;; \
		4) \
			$(MAKE) db-clear; \
			;; \
		5) \
			$(MAKE) db-backup; \
			;; \
		6) \
			read -p "Enter backup file path (e.g., backups/db_20230101_120000.sql): " file; \
			$(MAKE) db-restore file=$$file; \
			;; \
		7) \
			$(MAKE) db-wait; \
			;; \
		8) \
			echo "Returning to main menu"; \
			;; \
		*) \
			echo "$(RED)Invalid option selected$(NC)"; \
			;; \
	esac

db-create:
	@echo "$(YELLOW)Checking if database exists...$(NC)"
	@$(DOCKER_COMPOSE) up -d db
	@$(MAKE) db-wait
	@if ! $(DOCKER_COMPOSE) exec -T db psql -U $(shell grep DB_USER .env | cut -d= -f2) -lqt | cut -d \| -f 1 | grep -qw $(shell grep DB_NAME .env | cut -d= -f2); then \
		echo "$(YELLOW)Creating database $(shell grep DB_NAME .env | cut -d= -f2)...$(NC)"; \
		$(DOCKER_COMPOSE) exec -T db psql -U $(shell grep DB_USER .env | cut -d= -f2) -c "CREATE DATABASE $(shell grep DB_NAME .env | cut -d= -f2)"; \
		echo "$(GREEN)Database $(shell grep DB_NAME .env | cut -d= -f2) created successfully.$(NC)"; \
	else \
		echo "$(GREEN)Database $(shell grep DB_NAME .env | cut -d= -f2) already exists.$(NC)"; \
	fi; \
	echo ""; \
	read -p "Would you like to restore from a backup? [y/N] " restore_choice; \
	if [ "$$restore_choice" = "y" ] || [ "$$restore_choice" = "Y" ]; then \
		$(MAKE) db-restore; \
	else \
		echo "$(YELLOW)Skipping backup restoration.$(NC)"; \
	fi

db-start:
	$(DOCKER_COMPOSE) up -d db
	@echo "$(GREEN)Database started on port $(shell grep DB_PORT .env | cut -d= -f2)$(NC)"

db-stop:
	$(DOCKER_COMPOSE) down
	@echo "$(YELLOW)Database stopped$(NC)"

db-clear:
	@echo "$(RED)WARNING: This will delete ALL database data!$(NC)"
	@read -p "Are you sure you want to proceed? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		$(DOCKER_COMPOSE) down; \
		if docker volume ls | grep -q backend_postgres_data; then \
			docker volume rm backend_postgres_data && \
			echo "$(GREEN)Database data cleared. Use 'make db-start' to restart the database.$(NC)"; \
		else \
			echo "$(YELLOW)Volume not found. Nothing to remove.$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)Operation cancelled.$(NC)"; \
	fi

db-backup:
	@mkdir -p backups
	@NOW=$$(date +"%Y%m%d_%H%M%S"); \
	echo "$(GREEN)Creating database backup: backups/db_$$NOW.sql$(NC)"; \
	$(DOCKER_COMPOSE) exec db pg_dump -U django_user auctionhouse > backups/db_$$NOW.sql && \
	echo "$(GREEN)Backup completed: backups/db_$$NOW.sql$(NC)" || \
	echo "$(RED)Backup failed$(NC)"

db-restore:
	@mkdir -p backups
	@if [ -z "$(file)" ]; then \
		if [ -d "backups" ] && [ "$$(ls -A backups 2>/dev/null | grep -E '\.sql$$')" ]; then \
			echo "$(YELLOW)Available backup files:$(NC)"; \
			ls -1 backups | grep -E '\.sql$$' | nl; \
			echo ""; \
			read -p "Enter backup number or full path (or 'q' to quit): " backup_input; \
			if [ "$$backup_input" = "q" ]; then \
				echo "$(YELLOW)Restoration cancelled.$(NC)"; \
				exit 0; \
			elif [[ "$$backup_input" =~ ^[0-9]+$$ ]]; then \
				selected_file=$$(ls -1 backups | grep -E '\.sql$$' | sed -n "$${backup_input}p"); \
				if [ -n "$$selected_file" ]; then \
					export file="backups/$$selected_file"; \
				else \
					echo "$(RED)Invalid backup number. Aborting.$(NC)"; \
					exit 1; \
				fi; \
			else \
				export file="$$backup_input"; \
			fi; \
		else \
			echo "$(YELLOW)No backup files found in backups/ directory.$(NC)"; \
			read -p "Enter full path to backup file (or 'q' to quit): " backup_path; \
			if [ "$$backup_path" = "q" ]; then \
				echo "$(YELLOW)Restoration cancelled.$(NC)"; \
				exit 0; \
			else \
				export file="$$backup_path"; \
			fi; \
		fi; \
	fi; \
	if [ ! -f "$$file" ]; then \
		echo "$(RED)Error: Backup file $$file not found$(NC)"; \
		exit 1; \
	fi; \
	echo "$(RED)WARNING: This will COMPLETELY REPLACE all data in the database!$(NC)"; \
	echo "$(RED)All existing users, data, and configurations will be overwritten.$(NC)"; \
	read -p "Are you absolutely sure you want to proceed? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "$(YELLOW)Restoring from $$file...$(NC)"; \
		cat "$$file" | $(DOCKER_COMPOSE) exec -T db psql -U $(shell grep DB_USER .env | cut -d= -f2) -d $(shell grep DB_NAME .env | cut -d= -f2) && \
		echo "$(GREEN)Database restored successfully. All previous data has been replaced.$(NC)" || \
		echo "$(RED)Restore failed. Please check the error message above.$(NC)"; \
	else \
		echo "$(YELLOW)Database restore cancelled.$(NC)"; \
	fi

db-wait:
	@echo "$(YELLOW)Waiting for database to be ready...$(NC)"
	@for i in $$(seq 1 $(MAX_RETRIES)); do \
		if $(DOCKER_COMPOSE) exec -T db pg_isready -U django_user -d auctionhouse > /dev/null 2>&1; then \
			echo "$(GREEN)Database is ready!$(NC)"; \
			exit 0; \
		fi; \
		echo "$(YELLOW)Attempt $$i/$(MAX_RETRIES): Database not ready yet. Retrying in $(RETRY_INTERVAL) seconds...$(NC)"; \
		sleep $(RETRY_INTERVAL); \
	done; \
	echo "$(RED)Database failed to start after $(MAX_RETRIES) attempts.$(NC)"; \
	exit 1

migrations:
	$(MANAGE) makemigrations
	@echo "$(GREEN)Migrations created.$(NC)"

migrate:
	$(MANAGE) migrate
	@echo "$(GREEN)Migrations applied.$(NC)"

superuser:
	$(MANAGE) createsuperuser

run:
	@echo "$(GREEN)Starting development server...$(NC)"
	$(MANAGE) runserver 0.0.0.0:8000

run-dev:
	@echo "$(GREEN)Starting development server with debug toolbar...$(NC)"
	DEBUG_TOOLBAR=True $(MANAGE) runserver 0.0.0.0:8000

shell:
	$(MANAGE) shell

collectstatic:
	$(MANAGE) collectstatic --noinput

test:
	$(MANAGE) test

test-coverage:
	coverage run --source='.' $(MANAGE) test
	coverage report

env-setup:
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "$(GREEN)Created .env file from .env.example$(NC)"; \
			echo "$(YELLOW)Please update the .env file with your specific settings.$(NC)"; \
		else \
			echo "$(RED)Error: .env.example file not found.$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(YELLOW).env file already exists. Skipping.$(NC)"; \
	fi

setup: db-start env-setup db-create db-wait migrate
	@echo "$(GREEN)Initial setup completed.$(NC)"
	@echo -n "$(YELLOW)Do you want to create a superuser? [y/N] $(NC)"; \
	read answer; \
	if [ "$$answer" = "y" ] || [ "$$answer" = "Y" ]; then \
		$(MAKE) superuser; \
	else \
		echo "$(YELLOW)Skipping superuser creation.$(NC)"; \
	fi

update:
	$(PIP) install -r requirements.txt --upgrade
	@echo "$(GREEN)Dependencies updated.$(NC)"
