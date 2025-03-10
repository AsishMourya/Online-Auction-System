# Online-Auction-System
## Backend Setup (Django)

1.  **Navigate to the Backend Directory:**

    ```
    cd backend
    ```

2.  **Create and Activate the Virtual Environment:**

    ```
    python -m venv venv
    .\venv\Scripts\activate
    ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```
    
4.  **Database Configuration:**

       ```
        django-admin startproject auctionhouse backend/
       ```
       
    -   Update `backend/auctionhouse/settings.py` with your database credentials: Current Settings :
        
        ```
        DATABASES = {
            'default': {
                  'ENGINE': 'django.db.backends.postgresql',
                  'NAME': 'auction_house',
                  'USER': 'panda',
                  'PASSWORD': 'panda',
                  'HOST': '0.0.0.0',
                  'PORT': '5433',
            }
        }
        ```

5.  **Running Migrations and creating Super user:**

    ```
    python manage.py makemigrations
    python manage.py migrate
    ```
    
    Create an admin user:
    
    ```
    python manage.py createsuperuser
    ```    
    
7.  **Start the Django Development Server:**

    ```
    python manage.py runserver
    ```

    The API now be running on `http://127.0.0.1:5433/`.

