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
    pip install django djangorestframework psycopg2-binary djangorestframework-simplejwt
    ```
    
    ```
    https://medium.com/@basit26374/how-to-run-postgresql-in-docker-container-with-volume-bound-c141f94e4c5a
    ```
    
5.  **Database Configuration:**

       ```
        django-admin startproject auctionhouse backend/
       ```
       
    -   Update `backend/auctionhouse/settings.py` with your database credentials:

        ```
        DATABASES = {
            'default': {
                  'ENGINE': 'django.db.backends.postgresql',
                  'NAME': 'auction_house',
                  'USER': 'username',
                  'PASSWORD': 'pswd',
                  'HOST': 'localhost',
                  'PORT': '5433',
            }
        }
        ```

7.  **Apply Migrations:**

    ```
    python manage.py makemigrations
    python manage.py migrate
    ```
8.  **Start the Django Development Server:**

    ```
    python manage.py runserver
    ```

    The backend server should now be running on `http://127.0.0.1:5433/`.