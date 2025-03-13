# Auction House Backend

This is the backend API for an Auction House platform built with Django.

## Current Progress

The backend currently has the following features implemented:

- **Authentication System**:
  - JWT-based authentication with token refresh and blacklisting
  - User registration and login
  - Password change functionality
  - User profiles with different roles (Admin, Staff, Buyer, Seller)

- **User Management**:
  - User profile viewing and editing
  - Address management (create, read, update, delete)
  - Payment method management
  - Default address and payment method selection

- **Admin Functions**:
  - User management dashboard
  - View and manage all addresses and payment methods

## Setup Instructions

### Prerequisites

- Python 3.x
- Docker and Docker Compose (for PostgreSQL)
- pip
- python-dotenv (for environment variable management)

### Environment Setup

1. Clone the repository (if you haven't already)
   ```bash
   git clone [repository-url]
   cd auctionhouse/backend
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables
   ```bash
  # Create a .env file from the template
   copy .env.example .env

   # Open the file in Notepad to edit
   notepad .env
   ```

### Database Setup

The project uses PostgreSQL running in Docker. You can manage the database using the provided Makefile commands:

```bash
# Start Docker Desktop first, then:

# Start the PostgreSQL container
docker-compose up -d

# Create database
docker exec -it auction_house_postgres psql -U django_user -c "CREATE DATABASE auctionhouse;"

# Backup database
mkdir -p backups
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker exec -it auction_house_postgres pg_dump -U django_user auctionhouse > "backups/auctionhouse_$timestamp.sql"

# Restore from backup
docker exec -i auction_house_postgres psql -U django_user auctionhouse < backups/filename.sql

# Stop the PostgreSQL container
docker-compose down
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
python manage.py makemigrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run the development server
python manage.py runserver              # Normal mode
python manage.py runserver --settings=auctionhouse.settings.dev  # With debug toolbar

```

### Running the Development Server

Start the Django development server:
```bash
python manage.py runserver
```

The API will be available at http://127.0.0.1:8000/

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

## Next Steps / Coming Soon

- Product listings and categories
- Auction functionality with bidding
- Order processing
- Payment integration
- Notifications system
- Search and filter functionality

## Notes

- The project uses Django's built-in authentication system with a custom User model
- JWT tokens are configured to expire after 60 minutes, with refresh tokens valid for 14 days
- Robust validation is implemented for user data including emails and phone numbers