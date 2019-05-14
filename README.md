Synopsis:

The project catalog is a web application written in Python using Flask framework for a catalog of items.
Each item in the catalog belongs to a certain category. Public information is read-only and you will not be able to
add/edit/delete items unless you are logged in. This application provides the users 2 options to log in using
their Facebook or Google accounts.
The user should be able to edit/delete the items they have created.

---------------------------------------------------------------------------------------------------------------------
Installation:

To run the project, switch to the project directory and follow the steps below:
1. To create the database and tables, run `python database_setup.py`.
This creates 3 tables in the itemcatalog database
    a. user
    b. category
    c. item
2. To run the application, run `python application.py`.
3. To view the catalog, visit `http://localhost:8000` in browser.

---------------------------------------------------------------------------------------------------------------------
Links:

Visit the following links to browse the application:

1. Login --> `http://localhost:8000/login`
2. View catalog home --> `http://localhost:8000` or `http://localhost:8000/catalog`
3. View items in category --> `http://localhost:8000/catalog/<category-name>/items`
4. View item information --> `http://localhost:8000/catalog/<category-name>/<item-name>`
5. View category items JSON --> `http://localhost:8000/catalog/<category-name>/items/JSON`
6. View all categories JSON --> `http://localhost:8000/catalog/categories/JSON`
7. View item JSON --> `http://localhost:8000/catalog/<item-name>/JSON`
8. View catalog JSON --> `http://localhost:8000/catalog.json`

For logged in users who created the item:
9. Edit item --> `http://localhost:8000/catalog/<item-name>/edit`
10. Delete item --> `http://localhost:8000/catalog/<item-name>/delete`

For logged in Users only:
11. Logout --> `http://localhost:8000/disconnect`
12. Create New Item --> `http://localhost:8000/catalog/item/new`
13. Create New Category --> `http://localhost:8000/catalog/new`

---------------------------------------------------------------------------------------------------------------------
Contributors:

Girish Gombi