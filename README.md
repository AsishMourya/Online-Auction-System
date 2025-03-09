# Online-Auction-System
## Backend Setup (Django)

1.  **Navigate to the Backend Directory:**

    ```
    cd backend
    ```

2.  **Create a Virtual Environment:**

    ```
    python -m venv venv
    ```

3.  **Activate the Virtual Environment:**

    -   On Unix or macOS:

        ```
        source venv/bin/activate
        ```

    -   On Windows:

        ```
        .\venv\Scripts\activate
        ```

4.  **Install Dependencies:**

    ```
    pip install django djangorestframework psycopg2-binary
    ```
    
5.  **Database Configuration:**

    -   Update `backend/auctionhouse/settings.py` with your database credentials:

        ```
        DATABASES = {
            'default': {
                  'ENGINE': 'django.db.backends.postgresql',
                  'NAME': 'auction_house',
                  'USER': 'pswd',
                  'PASSWORD': 'pswd',
                  'HOST': 'localhost',
                  'PORT': '5433',
            }
        }
        ```

6.  **Apply Migrations:**

    ```
    python manage.py makemigrations
    python manage.py migrate
    ```
7.  **Start the Django Development Server:**

    ```
    python manage.py runserver
    ```

    The backend server should now be running on `http://127.0.0.1:5433/`.

