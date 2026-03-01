CREATE USER keycloak WITH PASSWORD 'keycloak';
CREATE DATABASE keycloak OWNER keycloak;

CREATE USER app_user WITH PASSWORD 'app_pass';
CREATE DATABASE app_db OWNER app_user;

