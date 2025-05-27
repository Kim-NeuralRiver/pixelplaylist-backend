# PixelPlaylistAI Backend

This is the Django backend for the PixelPlaylistAI project. It handles user authentication, game recommendation generation, playlist saving, and communication with external APIs like IGDB, IsThereAnyDeal, and OpenAI.

## Requirements

- Python 3.10+
- pip
- Virtual environment (recommended)
- A `.env` file with your API keys and secrets

## Setup Instructions

1. **Clone the repo**


   ```bash
   git clone -b 6-set-up-django-authentication-jwt https://github.com/Kim-NeuralRiver/pixelplaylist-backend.git
   cd pixelplaylist-backend

Note: for now, clone the development-branch, or the most recent ticket branch. In the current case, that is: 6-set-up-django-authentication-jwt

2. **Set up venv**
Set up a virtual environment

python -m venv venv
source venv/bin/activate      # On Mac/Linux
venv\Scripts\activate         # On Windows

3. **Install dependencies**

pip install -r requirements.txt

4. **Clone .env example**

Copy example env file as .env

cp env.example .env

And fill with actual variables.

5. **(WIP, OPTIONAL) Apply Database Migrations**
python manage.py migrate

6. **Run dev server**

python manage.py runserver

7. **Visit the API**

    API: http://localhost:8000/api/

    Swagger Docs: http://localhost:8000/swagger/

8. **Check with frontend**

Run dev server at the same time as frontend for compatibility check. 