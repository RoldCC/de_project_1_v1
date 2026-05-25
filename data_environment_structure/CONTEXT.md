# General context
Here youll build the principal files youll need to run the project (docker files - docker compose.yml, utils.py).

- Always use logging package instead of print to give logs.

## Docker
- Create a docker-compose.yml file to contain all the necessary code to build and use an azurite storage.

## Utilities
Create a utils.py file which will contain functions used in all other python files:
- Create the azurite client.
- All require storage operations (containers creation, file uploads, file pulls, file upload to specific layer).
- main() as usual.

At the end add the created files into the claude.md file directory structure diagram (ONLY MAIN FILES, do not add subfiles).