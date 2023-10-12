# craftdb
create a local database for my crafting
source .venv/bin/activate

 pip install -r Requirements.txt

## Libraries
* Flask: Web app library
* python-dotenv: For setting flask variables
* psycopg2-binary: Allows us to connect to the hosted database
* Materialize: https://materializecss.com/getting-started.html

## Files
* .env environment specific variables. not public do not share
* .flaskenv: flask variables
* app.py: The flask application. app is the default name, but it could be something else. Set the file name in .flaskenv

## Variables
### Flask Env
* FLASK_APP: Application file name. default: app
* FLASK_DEBUG: Flag to turn on debug mode. default: False
### Env
* DATABASE_URL: Url of the database hosting. Currently from ElephantSQL

## Templates
* Base
    * create - pass data tuple
        * field - column name
        * type 
            * 1 == text
            * 2 == date
            * 3 == expandable field
            * 4 == date
        * title = pretty column name to be displayed


## Plan
### List Pages
* Projects Page - **/projects**
    * list out projects
    * button to enter 1 project -> *Create Project*
    * roll up supplies usage costs, join to projects page
* Multi Pack Tools - **/multipacks**
    * list out multipacks
    * button to enter 1 multipack -> *Create Multipack*
    * link to add multiple supplies -> *Create Supply from Multipack*
* Supplies Page
    * list out supplies
    * button to enter 1 supply -> *Create Supply*
* Supplies Usage
### Create Pages
* Create Project - **/create-project**
    * Enter Data
        * Project Name
        * Completion Date
        * Type
    * Disable Form & Show Alert
    * Future: Navigate to the single project page & propagate alert there
* Create Multipack - **/create-multipack**
    * Enter Data
        * Name
        * Purchase Date
        * Brand
        * Store
        * Volume
        * Cost
    * Disable Form & Show Alert
    * Future: Navigate to the multi supply page & propagate data
        * multipack id
        * cost per unit -> cost
        * variable number of names
        * store
        * brand
        * purchase date
* Create Supply - **/create-supply**
    * Enter Data
        * Name
        * Purchase Date
        * Brand
        * Store
        * Volume
        * Cost
        * Estimate Flag
        * Used Up Flag - don't need on create page
        * Mutipack ID (optional) - don't need on create page
    * Disable Form & Show Alert
### Single Pages
* Single Project Page
    * edit details
    * see supplies usage
    * button to add supplies usage
* Single Supply Page
    * edit details
    * see projects where its used

create/edit
    project
        edit - include supply usage
        new
    multipack
        edit
        new
    supply
        edit
        new


https://www.digitalocean.com/community/tutorials/how-to-make-a-web-application-using-flask-in-python-3
@app.route('/<int:id>/delete', methods=('POST',))
@app.route('/<int:id>/edit', methods=('GET', 'POST'))

<-- return data should be in the format-->
data = {}
{id: 1
    data:{
        field: value,
        field2: value
    }

$(this).find("td").eq(7).find("input").prop('checked')

return_data['usages'] = $("tbody tr").map($(this).find("td").eq(7).find("input").data('initial-value') + " " + $(this).find("td").eq(7).find("input").prop('checked'))
            