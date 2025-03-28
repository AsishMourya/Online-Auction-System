# Online Auction System

A comprehensive auction platform with Django backend and React frontend.

## Current Progress

The system currently has the following features implemented:

- **Authentication System**:
  - JWT-based authentication with token refresh and blacklisting
  - User registration and login
  - Password change functionality
  - User profiles with different roles (Admin, Staff, User)

- **User Management**:
  - User profile viewing and editing (personal information, avatar)
  - Address management (create, read, update, delete)
  - Payment method management
  - Default address and payment method selection
  - Account deletion functionality
  - Profile picture/avatar uploading

- **Wallet & Transactions**:
  - User wallet creation and management
  - Transaction history tracking
  - Fund deposits and withdrawals

- **Admin Functions**:
  - User management dashboard
  - View and manage all users, addresses and payment methods
  - Activate/deactivate user accounts
  - Change user roles (admin, staff, user)
  - Create new users with specific roles
  - Add funds to user wallets
  - View user transaction history

- **Notifications System**:
  - Notification preferences for users
  - In-app notifications

- **Frontend Interface**:
  - User profile management
  - Profile editing
  - Password changing
  - Responsive design

## Setup Instructions

### Prerequisites

- Python 3.x
- Docker and Docker Compose (for PostgreSQL)
- Node.js and npm (for frontend)
- pip
- python-dotenv (for environment variable management)

### Environment Setup

1. Clone the repository
   ```bash
   git clone [repository-url]
   ```

2. Backend setup
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Frontend setup
   ```bash
   cd frontend
   npm install
   ```

4. Set up environment variables
   ```bash
   # For backend
   cd backend
   # Initialize the environment setup (creates .env from .env.example if needed)
   make env-setup
   
   # Modify the .env file with your settings
   nano .env
   ```

### Database Setup

The project uses PostgreSQL running in Docker. You can manage the database using the provided Makefile commands:

```bash
# Start the PostgreSQL container
make db-start

# Wait for the database to be ready
make db-wait

# Create database and optionally restore from a backup
make db-create
# This will create the database if needed and offer to restore from a backup

# Stop the PostgreSQL container
make db-stop

# Create a database backup
make db-backup
# This will create a timestamped SQL dump in the backups/ directory

# Restore from a backup file
make db-restore
# This will show available backups and guide you through the restoration process
# You can also specify a file directly: make db-restore file=backups/db_filename.sql
# WARNING: This will completely replace all data in the database

# Interactive database management menu
make db-settings
# Provides a menu-driven interface for all database operations

# Clear database (WARNING: destructive)
make db-clear
```

The Docker container uses configuration from your .env file:
- Database: Value from DB_NAME in .env (default: auctionhouse)
- User: Value from DB_USER in .env (default: django_user)
- Password: Value from DB_PASSWORD in .env (default: panda)
- Port: Value from DB_PORT in .env (default: 5433 mapped from container's 5432)

### Project Setup and Management

Use the provided Makefile commands to manage the project:

```bash
# Run database migrations
make migrations    # Create migration files
make migrate       # Apply migrations to database

# Create a superuser
make superuser

# Run the development server
make run           # Normal mode
make run-dev       # With debug toolbar

# Testing and code quality
make test          # Run tests
make test-coverage # Run tests with coverage report
make lint          # Check code style with flake8
make format        # Format code using black

# Quick initial setup (database, environment, migrations)
make setup

# See all available commands
make help
```

### Running the Development Server

Start the Django development server:
```bash
# Backend
cd backend
make run
```

Start the React development server:
```bash
# Frontend
cd frontend
npm start
```

The API will be available at http://127.0.0.1:8000/
The frontend will be available at http://localhost:3000/

## Environment Variables

The project uses environment variables for configuration. These are stored in a `.env` file. A template file `.env.example` is provided.

Key environment variables:
- `DEBUG`: Set to "True" or "False" to control debug mode
- `SECRET_KEY`: Django secret key
- `DB_*`: Database connection settings
- `EMAIL_*`: Email service configuration
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `STATIC_ROOT`/`MEDIA_ROOT`: Paths for static and media files
- `TIME_ZONE`: Application timezone

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: http://127.0.0.1:8000/swagger/
- ReDoc: http://127.0.0.1:8000/redoc/
- Postman

## Next Steps / Coming Soon

- Auction functionality with bidding
- Item listings and categories
- Search and filter functionality
- Order processing and tracking
- Payment gateway integration
- Enhanced notification system

## Notes

- The project uses Django's built-in authentication system with a custom User model
- JWT tokens are configured to expire after 60 minutes, with refresh tokens valid for 14 days
- Robust validation is implemented for user data including emails and phone numbers
- User accounts have wallet functionality for handling transactions
- Admin users can manage other users including activating/deactivating accounts and changing roles
