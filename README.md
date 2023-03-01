# Setup and Run Application

1. Install Python 3.10.4.
2. Install Redis and start it using `redis-server` use default port of 6379
3. Clone repo to somewhere sensible on machine
   1. `git clone https://github.com/coliin8/book_explorer.git`
4. `cd book_explorer`
5. Setup Virtual Env
   1. `python -m venv .`
  1. Activate venv
    1. Windows: `Scripts\activate.bat`
    2. Linux/Mac: `source bin/activate`
6. Run `pip install -f requirements.txt`
7. Setup Environmental Variables
   1. AWS_ACCESS_KEY_ID=Your_Key_id
   2. AWS_SECRET_ACCESS_KEY=Your_Secret_Token
8. Run `pyt
9. hon manage.py migrate` to run migration and generate database
10. Run `python manage.py runserver`
11. Run `celery --app book_explorer  worker -l info`

# Run Tests

`pytest`

## Creating an admin user

First we’ll need to create a user who can login to the admin site. Run the following command:

`python manage.py createsuperuser`

Enter your desired username and press enter.

`Username: admin`

You will then be prompted for your desired email address:

`Email address: admin@example.com`

The final step is to enter your password. You will be asked to enter your password twice, the second time as a confirmation of the first.

```
Password: **********
Password (again): *********
Superuser created successfully.
```

### Development Server and admin

`python manage.py runserver`

Goto http://127.0.0.1/admin

You can login with admin user credentials
