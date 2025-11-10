# Example env file for DigitalOcean App Platform deploys
#
# Usage:
#   cp .env.example.do .env.do
#   scripts/deploy-digitalocean.sh
#   # or specify a custom file
#   ENV_FILE_CANDIDATE=/path/to/your.env scripts/deploy-digitalocean.sh

# Required
DO_APP_NAME=cybergrader
DO_REGION=sfo3

# GitHub repo used by DO App Platform to build the app image
# If omitted, the deploy script tries to derive it from your local git remote.
DO_GITHUB_REPO=your-org/cybergrader
DO_GITHUB_BRANCH=main

# Full connection string from DO Managed Database (Settings -> Connection Details)
# Example:
# postgresql://doadmin:password@db-postgresql-nyc1-12345-do-user-1234567-0.b.db.ondigitalocean.com:25060/defaultdb?sslmode=require
DO_DB_CONNECTION_STRING=postgresql://doadmin:password@db-host:25060/defaultdb?sslmode=require

# Optional: update an existing app instead of creating new
# DO_APP_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# App sizing
DO_INSTANCE_SIZE=basic-xxs
DO_INSTANCE_COUNT=1

# Database schema to use
DATABASE_SCHEMA=public

# Follow logs after deployment (1 or 0)
FOLLOW_LOGS=1

# Authentication / password reset (ForwardEmail)
SECRET_KEY=change-me
FORWARDEMAIL_API_TOKEN=your-forwardemail-api-token
EMAIL_FROM=no-reply@yourdomain.tld
# Use your DO ingress + path to your frontend reset page
RESET_LINK_BASE=https://your-app-name.ondigitalocean.app/reset-password
