import os


DEBUG = True
##############################################################################################
# Database settings
##############################################################################################
DATABASE_NAME = "LinkVault"
DATABASE_USERNAME = "postgres"
DATABASE_PASSWORD = 'postgres'
DATABASE_HOST = "localhost"
DATABASE_POST = "5432"
SQLALCHEMY_DATABASE_URL = f'postgresql+asyncpg://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_POST}/{DATABASE_NAME}'

##############################################################################################
# AUTH SETTINGS
##############################################################################################
SECRET_KEY = "ad4c4ff0dce6478c5c51045da5d800534115a7247b0150ff8063849d04b0a31a"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


##############################################################################################
# FILE SETTINGS
##############################################################################################
BASE_UPLOAD_DIR = 'media'
UPLOAD_URL = '/media'
